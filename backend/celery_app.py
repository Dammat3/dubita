"""Celery app + dubbing task with lazy Motor connection (fork-safe)."""
import os
import sys
import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# Ensure /app/backend is on sys.path so worker can import sibling modules
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from celery import Celery
from motor.motor_asyncio import AsyncIOMotorClient

REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

celery = Celery(
    "dubita",
    broker=REDIS_URL,
    backend=REDIS_URL,
)
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,         # if worker dies, redeliver task
    task_reject_on_worker_lost=True,
    worker_max_tasks_per_child=20,
    task_default_queue="dubbing",
    broker_connection_retry_on_startup=True,
)

logger = logging.getLogger("celery_app")


def _build_db():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


@celery.task(bind=True, name="dubita.run_dubbing", max_retries=0)
def run_dubbing(self, project_id: str):
    """Run the dubbing pipeline for a project. Synchronous wrapper around async code."""
    from dubbing import run_dubbing_pipeline  # local import to avoid app-load circulars

    async def _go():
        db = _build_db()
        try:
            await run_dubbing_pipeline(db, project_id)
        finally:
            db.client.close()

    asyncio.run(_go())
    return {"project_id": project_id, "status": "completed"}


@celery.task(name="dubita.resume_inflight")
def resume_inflight():
    """Re-queue any projects whose pipeline was interrupted (status not done/error)."""
    async def _go():
        db = _build_db()
        try:
            terminal = {"done", "error"}
            cursor = db.projects.find({"status": {"$nin": list(terminal)}})
            ids: list[str] = []
            async for p in cursor:
                ids.append(p["id"])
            for pid in ids:
                logger.info(f"Resuming interrupted project {pid}")
                run_dubbing.delay(pid)
            return ids
        finally:
            db.client.close()

    return asyncio.run(_go())
