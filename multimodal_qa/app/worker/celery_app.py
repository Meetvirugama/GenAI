import os

# pyrefly: ignore [missing-import]
from celery import Celery

from app.core.config import Config

# Ensure Redis URL is available, default to a standard local path
redis_url = getattr(Config, "REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))

celery_app = Celery(
    "multimodal_qa",
    broker=redis_url,
    backend=redis_url,
    include=["app.rag.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600, # 1 hour max for extremely large PDFs
)
