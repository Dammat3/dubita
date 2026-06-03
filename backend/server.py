"""Main FastAPI server for Dubita - Italian video dubbing app."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
import uuid
import shutil
from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    FastAPI, APIRouter, UploadFile, File, Form, BackgroundTasks,
    Depends, HTTPException
)
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from auth import build_auth_router, seed_admin
from dubbing import (
    run_dubbing_pipeline, project_dir, MEDIA_ROOT, MAX_DURATION_SEC
)
from celery_app import run_dubbing as celery_run_dubbing

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("server")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Dubita - Italian Video Dubbing")

# CORS
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
allow_origins = [frontend_url, "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth
auth_router, get_current_user = build_auth_router(db)
app.include_router(auth_router)

api = APIRouter(prefix="/api")


@api.get("/")
async def root():
    return {"app": "Dubita", "status": "ok"}


@api.get("/voices")
async def list_voices():
    return {
        "voices": [
            {"id": "alloy", "label": "Alloy (Neutra)"},
            {"id": "nova", "label": "Nova (Energica)"},
            {"id": "shimmer", "label": "Shimmer (Brillante)"},
            {"id": "onyx", "label": "Onyx (Profonda)"},
            {"id": "echo", "label": "Echo (Calma)"},
            {"id": "fable", "label": "Fable (Narrativa)"},
            {"id": "coral", "label": "Coral (Calda)"},
            {"id": "sage", "label": "Sage (Misurata)"},
            {"id": "ash", "label": "Ash (Chiara)"},
        ]
    }


class CreateYoutubeIn(BaseModel):
    youtube_url: str
    voice: str = "alloy"
    title: Optional[str] = None


def _new_project_doc(user_id: str, voice: str, source_type: str, title: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "source_type": source_type,
        "voice": voice,
        "status": "queued",
        "progress": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@api.post("/projects/youtube")
async def create_youtube_project(
    payload: CreateYoutubeIn,
    user: dict = Depends(get_current_user),
):
    if not payload.youtube_url.startswith(("http://", "https://")):
        raise HTTPException(400, "URL YouTube non valido")
    title = payload.title or "Video YouTube"
    doc = _new_project_doc(user["id"], payload.voice, "youtube", title)
    doc["youtube_url"] = payload.youtube_url
    # attach user's cookies file if they uploaded one
    cookies_path = MEDIA_ROOT / "_cookies" / f"{user['id']}.txt"
    if cookies_path.exists():
        doc["cookies_path"] = str(cookies_path)
    await db.projects.insert_one(doc)
    project_dir(doc["id"])  # ensure folder
    celery_run_dubbing.delay(doc["id"])
    doc.pop("_id", None)
    return doc


@api.post("/projects/upload")
async def upload_project(
    file: UploadFile = File(...),
    voice: str = Form("alloy"),
    title: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(400, "Nessun file fornito")
    ext = Path(file.filename).suffix.lower()
    if ext not in {".mp4", ".mov", ".mkv", ".webm", ".m4v"}:
        raise HTTPException(400, "Formato non supportato. Usa mp4, mov, mkv, webm.")
    doc = _new_project_doc(user["id"], voice, "upload", title or file.filename)
    pdir = project_dir(doc["id"])
    dest = pdir / f"source{ext}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    # Always work with mp4
    if ext != ".mp4":
        import subprocess
        new_dest = pdir / "source.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(dest), "-c", "copy", str(new_dest)],
            capture_output=True
        )
        if new_dest.exists():
            dest.unlink(missing_ok=True)
            dest = new_dest
    doc["uploaded_path"] = str(dest)
    await db.projects.insert_one(doc)
    celery_run_dubbing.delay(doc["id"])
    doc.pop("_id", None)
    return doc


@api.get("/projects")
async def list_projects(user: dict = Depends(get_current_user)):
    items = await db.projects.find({"user_id": user["id"]}).sort("created_at", -1).to_list(200)
    for p in items:
        p.pop("_id", None)
        p.pop("segments", None)  # lightweight
    return items


@api.get("/projects/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    p = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not p:
        raise HTTPException(404, "Progetto non trovato")
    p.pop("_id", None)
    return p


@api.delete("/projects/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    p = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not p:
        raise HTTPException(404, "Progetto non trovato")
    await db.projects.delete_one({"id": project_id})
    pdir = MEDIA_ROOT / project_id
    if pdir.exists():
        shutil.rmtree(pdir, ignore_errors=True)
    return {"ok": True}


@api.get("/projects/{project_id}/video/source")
async def get_source_video(project_id: str, user: dict = Depends(get_current_user)):
    p = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not p:
        raise HTTPException(404, "Progetto non trovato")
    path = p.get("source_video_path") or p.get("uploaded_path") or str(MEDIA_ROOT / project_id / "source.mp4")
    if not Path(path).exists():
        raise HTTPException(404, "File non disponibile")
    return FileResponse(path, media_type="video/mp4")


@api.get("/projects/{project_id}/video/dubbed")
async def get_dubbed_video(project_id: str, user: dict = Depends(get_current_user)):
    p = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not p:
        raise HTTPException(404, "Progetto non trovato")
    path = p.get("dubbed_video_path")
    if not path or not Path(path).exists():
        raise HTTPException(404, "Video doppiato non disponibile")
    return FileResponse(path, media_type="video/mp4", filename=f"{p.get('title', 'dubbed')}.mp4")


# ---------- YouTube cookies management ----------

def _cookies_path_for(user_id: str) -> Path:
    d = MEDIA_ROOT / "_cookies"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{user_id}.txt"


@api.get("/me/cookies")
async def get_cookies_status(user: dict = Depends(get_current_user)):
    cp = _cookies_path_for(user["id"])
    return {
        "has_cookies": cp.exists(),
        "size": cp.stat().st_size if cp.exists() else 0,
        "uploaded_at": (
            datetime.fromtimestamp(cp.stat().st_mtime, tz=timezone.utc).isoformat()
            if cp.exists() else None
        ),
    }


@api.post("/me/cookies")
async def upload_cookies(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    raw = await file.read()
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(400, "File cookies troppo grande (max 2MB)")
    text = raw.decode("utf-8", errors="ignore")
    # accept Netscape-format cookies (must mention netscape header or have tab-separated lines)
    looks_ok = (
        "# Netscape HTTP Cookie File" in text
        or "# HTTP Cookie File" in text
        or any("\t" in line and not line.lstrip().startswith("#") for line in text.splitlines())
    )
    if not looks_ok:
        raise HTTPException(400, "Formato non valido. Esporta i cookies in formato Netscape (cookies.txt).")
    cp = _cookies_path_for(user["id"])
    cp.write_bytes(raw)
    return {"ok": True, "size": len(raw)}


@api.delete("/me/cookies")
async def delete_cookies(user: dict = Depends(get_current_user)):
    cp = _cookies_path_for(user["id"])
    if cp.exists():
        cp.unlink()
    return {"ok": True}


app.include_router(api)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.projects.create_index("user_id")
    await db.projects.create_index("id", unique=True)
    await seed_admin(db)

    # Resume any in-flight projects (interrupted by restart)
    try:
        cursor = db.projects.find({"status": {"$nin": ["done", "error"]}})
        async for p in cursor:
            logger.info(f"Resuming interrupted project {p['id']} (was: {p['status']})")
            await db.projects.update_one(
                {"id": p["id"]},
                {"$set": {"status": "queued", "progress": 0, "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
            celery_run_dubbing.delay(p["id"])
    except Exception as e:
        logger.warning(f"Resume scan failed: {e}")

    logger.info("Dubita backend ready")


@app.on_event("shutdown")
async def shutdown():
    client.close()
