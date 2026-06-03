"""Video dubbing pipeline: download -> extract audio -> transcribe -> translate -> TTS -> mux."""
import os
import asyncio
import json
import logging
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.llm.openai import OpenAISpeechToText, OpenAITextToSpeech

logger = logging.getLogger("dubbing")

MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", "/app/backend/media"))
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

MAX_DURATION_SEC = 30 * 60  # 30 minutes


def _key() -> str:
    return os.environ["EMERGENT_LLM_KEY"]


def project_dir(project_id: str) -> Path:
    p = MEDIA_ROOT / project_id
    p.mkdir(parents=True, exist_ok=True)
    return p


async def _run(cmd: list[str]) -> tuple[int, str, str]:
    """Run subprocess asynchronously."""
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode or 0, stdout.decode(errors="ignore"), stderr.decode(errors="ignore")


async def get_video_duration(path: Path) -> float:
    code, out, err = await _run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ])
    if code != 0:
        raise RuntimeError(f"ffprobe failed: {err}")
    return float(out.strip())


async def download_youtube(url: str, dest_dir: Path, cookies_path: str | None = None) -> Path:
    """Download YouTube video as mp4 (max 720p) using yt-dlp Python API.

    Cloud IPs are often bot-flagged by YouTube; we try multiple player clients.
    If `cookies_path` is provided (Netscape format), it is used to authenticate.
    """
    import yt_dlp

    out_template = str(dest_dir / "source.%(ext)s")

    last_err: Exception | None = None
    # Try multiple extractor clients to dodge YouTube bot blocks
    client_strategies = [
        ["tv_embedded"],
        ["android"],
        ["ios"],
        ["mweb"],
        ["web"],
    ]
    for clients in client_strategies:
        opts = {
            "format": "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/b",
            "merge_output_format": "mp4",
            "outtmpl": out_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": clients}},
            "retries": 2,
        }
        if cookies_path and Path(cookies_path).exists():
            opts["cookiefile"] = cookies_path
        try:
            def _download():
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
            await asyncio.to_thread(_download)
            break  # success
        except Exception as e:
            last_err = e
            # clean partial files and try next strategy
            for f in list(dest_dir.iterdir()):
                if f.name.startswith("source."):
                    f.unlink(missing_ok=True)
            continue
    else:
        err_str = str(last_err)
        if "bot" in err_str.lower() or "403" in err_str or "Sign in" in err_str:
            raise RuntimeError(
                "YouTube ha bloccato il download da questo server (anti-bot). "
                "Carica i tuoi cookies YouTube o usa l'upload diretto del file MP4."
            )
        raise RuntimeError(f"Download YouTube fallito: {err_str[-300:]}")

    # find the resulting file
    for f in dest_dir.iterdir():
        if f.name.startswith("source.") and f.suffix in {".mp4", ".mkv", ".webm"}:
            if f.suffix != ".mp4":
                # convert to mp4
                mp4 = dest_dir / "source.mp4"
                await _run(["ffmpeg", "-y", "-i", str(f), "-c", "copy", str(mp4)])
                f.unlink(missing_ok=True)
                return mp4
            return f
    raise RuntimeError("Video YouTube non scaricabile (potrebbe essere bloccato).")


async def extract_audio(video_path: Path, out_path: Path) -> Path:
    """Extract mono 16kHz mp3 audio for Whisper."""
    code, _, err = await _run([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k",
        str(out_path),
    ])
    if code != 0:
        raise RuntimeError(f"audio extract failed: {err[-500:]}")
    return out_path


async def transcribe_audio(audio_path: Path) -> dict:
    """Whisper verbose_json with segment timestamps."""
    stt = OpenAISpeechToText(api_key=_key())
    with open(audio_path, "rb") as f:
        response = await stt.transcribe(
            file=f,
            model="whisper-1",
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )
    segments = []
    raw_segs = getattr(response, "segments", None) or []
    for s in raw_segs:
        # litellm may return dict or object
        if isinstance(s, dict):
            start = s.get("start", 0.0)
            end = s.get("end", 0.0)
            text = s.get("text", "")
        else:
            start = getattr(s, "start", 0.0)
            end = getattr(s, "end", 0.0)
            text = getattr(s, "text", "")
        segments.append({
            "start": float(start),
            "end": float(end),
            "text": (text or "").strip(),
        })
    return {
        "text": response.text,
        "language": getattr(response, "language", "unknown"),
        "segments": segments,
    }


async def translate_segments_to_italian(
    segments: list[dict],
    progress_cb=None,  # async callable(done:int, total:int)
) -> list[dict]:
    """Translate all segment texts to Italian preserving order.

    Multiple chunks are translated in parallel (bounded by semaphore) to speed up
    processing for long videos.
    """
    if not segments:
        return []

    # chunk segments to keep prompts reasonable
    chunk_size = 40
    total = len(segments)
    chunks: list[tuple[int, list[dict]]] = []
    for i in range(0, total, chunk_size):
        chunks.append((i, segments[i:i + chunk_size]))

    # results indexed by chunk start offset
    results: dict[int, list[str]] = {}
    completed_segments = 0
    sem = asyncio.Semaphore(4)  # up to 4 concurrent GPT calls

    from emergentintegrations.llm.chat import TextDelta, StreamDone

    async def translate_chunk(offset: int, chunk: list[dict]) -> tuple[int, list[str]]:
        async with sem:
            # Fresh LlmChat per chunk (avoids history bloat & enables parallelism safely)
            chat = LlmChat(
                api_key=_key(),
                session_id=f"translate-{uuid.uuid4()}",
                system_message=(
                    "Sei un traduttore professionista. Traduci ogni segmento di testo in italiano "
                    "naturale e fluente, mantenendo la stessa lunghezza approssimativa e lo stile del parlato. "
                    "Rispondi SOLO con un JSON array di stringhe, una per ogni segmento di input, "
                    "nello stesso ordine. Esempio output: [\"ciao\", \"come stai\"]"
                ),
            ).with_model("openai", "gpt-4o-mini")
            payload = json.dumps([s["text"] for s in chunk], ensure_ascii=False)
            msg = UserMessage(text=f"Traduci questo array JSON in italiano:\n{payload}")
            full = ""
            async for ev in chat.stream_message(msg):
                if isinstance(ev, TextDelta):
                    full += ev.content
                elif isinstance(ev, StreamDone):
                    break
            cleaned = full.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                if cleaned.lower().startswith("json"):
                    cleaned = cleaned[4:]
                cleaned = cleaned.strip()
            try:
                arr = json.loads(cleaned)
            except Exception:
                arr = [line.strip("-• ").strip() for line in cleaned.splitlines() if line.strip()]
            while len(arr) < len(chunk):
                arr.append("")
            return offset, arr[: len(chunk)]

    progress_lock = asyncio.Lock()

    async def run_one(offset: int, chunk: list[dict]):
        nonlocal completed_segments
        off, arr = await translate_chunk(offset, chunk)
        results[off] = arr
        async with progress_lock:
            completed_segments += len(arr)
            done = completed_segments
        if progress_cb:
            try:
                await progress_cb(done, total)
            except Exception:
                pass

    await asyncio.gather(*(run_one(off, ch) for off, ch in chunks))

    # Stitch results back in order
    out: list[str] = []
    for off, _ in chunks:
        out.extend(results.get(off, []))

    return [
        {**seg, "text_it": (out[i] if i < len(out) else "")}
        for i, seg in enumerate(segments)
    ]


async def synth_segment_audio(text: str, voice: str, out_path: Path) -> Path:
    """Generate TTS for one segment."""
    tts = OpenAITextToSpeech(api_key=_key())
    # OpenAI TTS limit 4096 chars
    text = text[:4000] if text else "..."
    audio_bytes = await tts.generate_speech(
        text=text, model="tts-1", voice=voice, response_format="mp3"
    )
    out_path.write_bytes(audio_bytes)
    return out_path


async def build_italian_audio_track(
    segments: list[dict], total_duration: float, work_dir: Path, voice: str,
    progress_cb=None,  # async callable(done:int, total:int)
) -> Path:
    """Synthesize each segment in parallel and place each at its start time on a silent track."""
    from pydub import AudioSegment

    final = AudioSegment.silent(duration=int(total_duration * 1000) + 500)
    total = len(segments)

    sem = asyncio.Semaphore(8)  # up to 8 concurrent TTS calls
    completed = 0
    progress_lock = asyncio.Lock()

    async def emit_progress():
        nonlocal completed
        async with progress_lock:
            completed += 1
            done = completed
        if progress_cb:
            try:
                await progress_cb(done, total)
            except Exception:
                pass

    async def synth_one(idx: int, seg: dict) -> tuple[int, Path | None]:
        text_it = seg.get("text_it", "").strip()
        if not text_it:
            await emit_progress()
            return idx, None
        seg_path = work_dir / f"seg_{idx:04d}.mp3"
        async with sem:
            try:
                await synth_segment_audio(text_it, voice, seg_path)
            except Exception as e:
                logger.error(f"TTS failed for segment {idx}: {e}")
                await emit_progress()
                return idx, None
        await emit_progress()
        return idx, seg_path

    results = await asyncio.gather(*(synth_one(i, s) for i, s in enumerate(segments)))

    # Overlay sequentially (pydub is not thread-safe; cheap anyway)
    for idx, seg_path in results:
        if seg_path is None or not seg_path.exists():
            continue
        try:
            piece = AudioSegment.from_file(seg_path, format="mp3")
        except Exception as e:
            logger.error(f"Cannot load segment {idx}: {e}")
            continue
        seg = segments[idx]
        seg_duration_ms = int((seg["end"] - seg["start"]) * 1000)
        # If generated piece is longer than segment slot, speed it up using pydub frame_rate trick
        if seg_duration_ms > 0 and len(piece) > seg_duration_ms * 1.15:
            ratio = len(piece) / seg_duration_ms
            ratio = min(ratio, 1.6)  # cap speedup
            new_fr = int(piece.frame_rate * ratio)
            piece = piece._spawn(piece.raw_data, overrides={"frame_rate": new_fr}).set_frame_rate(44100)

        start_ms = int(seg["start"] * 1000)
        final = final.overlay(piece, position=start_ms)

    out_path = work_dir / "italian_audio.mp3"
    final.export(out_path, format="mp3", bitrate="128k")
    return out_path


async def mux_video(video_path: Path, audio_path: Path, out_path: Path) -> Path:
    """Replace video's audio with the Italian audio track."""
    code, _, err = await _run([
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(out_path),
    ])
    if code != 0:
        # fallback: re-encode video
        code2, _, err2 = await _run([
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "veryfast",
            "-c:a", "aac",
            "-shortest",
            str(out_path),
        ])
        if code2 != 0:
            raise RuntimeError(f"mux failed: {err2[-500:]}")
    return out_path


# ----- Main pipeline -----

STAGES = [
    "queued", "downloading", "extracting", "transcribing",
    "translating", "synthesizing", "muxing", "done", "error"
]


async def update_project(db, project_id: str, **fields):
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.projects.update_one({"id": project_id}, {"$set": fields})


async def run_dubbing_pipeline(db, project_id: str):
    proj = await db.projects.find_one({"id": project_id})
    if not proj:
        return
    pdir = project_dir(project_id)
    voice = proj.get("voice", "alloy")
    try:
        # 1. Get the source video
        source_path = pdir / "source.mp4"
        if proj.get("source_type") == "youtube":
            await update_project(db, project_id, status="downloading", progress=5)
            source_path = await download_youtube(
                proj["youtube_url"], pdir, cookies_path=proj.get("cookies_path")
            )
        else:
            # already uploaded as source.<ext>
            existing = proj.get("uploaded_path")
            if existing:
                source_path = Path(existing)
            if not source_path.exists():
                raise RuntimeError("Video sorgente non trovato")

        duration = await get_video_duration(source_path)
        if duration > MAX_DURATION_SEC:
            raise RuntimeError(f"Video troppo lungo ({int(duration)}s). Max 30 minuti.")
        await update_project(db, project_id, duration=duration, progress=15)

        # 2. Extract audio
        await update_project(db, project_id, status="extracting", progress=20)
        audio_path = pdir / "audio.mp3"
        await extract_audio(source_path, audio_path)

        # 3. Transcribe
        await update_project(db, project_id, status="transcribing", progress=35)
        transcript = await transcribe_audio(audio_path)
        await update_project(
            db, project_id,
            transcript_text=transcript["text"],
            transcript_language=transcript["language"],
            segments=transcript["segments"],
            progress=55,
        )

        if not transcript["segments"]:
            raise RuntimeError("Nessun parlato rilevato nel video.")

        # 4. Translate (with per-chunk progress 60→75)
        await update_project(
            db, project_id, status="translating", progress=60,
            step_detail=f"Traduzione 0 / {len(transcript['segments'])} segmenti",
        )

        async def _translate_cb(done: int, total: int):
            pct = 60 + int((done / max(total, 1)) * 15)
            await update_project(
                db, project_id,
                progress=min(pct, 75),
                step_detail=f"Traduzione {done} / {total} segmenti",
            )

        translated = await translate_segments_to_italian(transcript["segments"], progress_cb=_translate_cb)
        await update_project(
            db, project_id,
            segments=translated,
            italian_text=" ".join(s.get("text_it", "") for s in translated).strip(),
            progress=75,
            step_detail=f"Traduzione completata: {len(translated)} segmenti",
        )

        # 5. TTS + assemble (with per-segment progress 80→92)
        await update_project(
            db, project_id, status="synthesizing", progress=80,
            step_detail=f"Sintesi vocale 0 / {len(translated)} segmenti",
        )

        async def _synth_cb(done: int, total: int):
            pct = 80 + int((done / max(total, 1)) * 12)
            await update_project(
                db, project_id,
                progress=min(pct, 92),
                step_detail=f"Sintesi vocale {done} / {total} segmenti",
            )

        italian_audio_path = await build_italian_audio_track(
            translated, duration, pdir, voice, progress_cb=_synth_cb
        )

        # 6. Mux
        await update_project(
            db, project_id, status="muxing", progress=92,
            step_detail="Composizione del video finale",
        )
        out_video = pdir / "dubbed.mp4"
        await mux_video(source_path, italian_audio_path, out_video)

        await update_project(
            db, project_id,
            status="done",
            progress=100,
            step_detail=None,
            dubbed_video_path=str(out_video),
            source_video_path=str(source_path),
        )
    except Exception as e:
        logger.exception("Pipeline error")
        await update_project(db, project_id, status="error", error=str(e)[:500], step_detail=None)
