# Dubita - Italian AI Video Dubbing

## Problem Statement (Original, in Italian)
> possiamo creare un sito che funziona come heygen? mi serve solo il doppiaggio audio in lingua italiana. il sito deve prendere il video e doppiarlo in italiano. è possibile fare una cosa del genere gratuita?

## Architecture
- Backend: FastAPI + MongoDB + ffmpeg + yt-dlp + pydub
- Frontend: React 19 + Tailwind + Phosphor Icons + Outfit/Manrope fonts
- Auth: JWT (httpOnly cookie + Bearer fallback)
- AI Pipeline (all via Emergent Universal LLM Key):
  - OpenAI Whisper (whisper-1) — transcription with segment timestamps
  - OpenAI GPT (gpt-4o-mini) — segment-by-segment translation EN→IT
  - OpenAI TTS (tts-1) — per-segment Italian voice synthesis
  - ffmpeg — audio extract + mux Italian audio back into the source video
- Storage: local disk at /app/backend/media/<project_id>/

## User Personas
- **Content creator / educator** wanting to localize videos to Italian quickly
- **Marketer** dubbing product demos / interviews
- **Casual user** wanting to share a YouTube clip in Italian

## Implemented (2026-02-03)
- JWT login/register with cinematic UI
- Dashboard with both file upload AND YouTube URL ingestion
- Voice picker (9 OpenAI voices)
- Per-segment translation + TTS positioned at original timestamps
- Live status polling (8 stages)
- Side-by-side video player (original vs Italian)
- Bilingual transcript table (original + Italian)
- Download dubbed MP4
- Project deletion (cleans media folder)
- Cinematic dark theme: Obsidian #0A0B0E + Amber #FFB000, Outfit + Manrope fonts
- Max video duration 30 min enforced server-side

## Implemented (2026-02-03, Iteration 2)
- **Celery worker queue** with Redis broker — pipeline runs as `dubita.run_dubbing` task
- **Resume on restart** — interrupted projects (status != done/error) are auto re-queued on backend startup
- **Per-user YouTube cookies.txt** — POST/GET/DELETE `/api/me/cookies`, Netscape-format validation, used by `yt-dlp` `cookiefile` opt to bypass anti-bot
- **CookiesPanel UI** in dashboard with Italian instructions for "Get cookies.txt LOCALLY" browser extension
- Supervisor configs added at `/etc/supervisor/conf.d/dubita_workers.conf` for `redis` + `celery` programs

## Known Limitations / Backlog
- **YouTube downloads blocked by anti-bot from cloud IP** — UI displays clear Italian error; users should upload MP4 directly. Possible fix: user-supplied cookies file or PO token.
- No lip-sync (audio-only dubbing, as requested by user)
- No worker queue — pipeline runs in FastAPI BackgroundTasks; restart kills in-flight jobs
- No login brute-force lockout

## P1 Next
- Add `--cookies` file path support for YouTube (let user upload cookies.txt)
- Optional speed-match: trim/pad each TTS segment more precisely
- Per-segment audio preview before final mux
- Add a "share link" / public preview page

## P2 Next
- Subtitle (SRT/VTT) export
- Multi-language target (other than just Italian)
- Voice cloning (ElevenLabs) opt-in
