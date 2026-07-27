from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    session_id: str
    image_path: str | None = None
    # 'history' is no longer expected from client, sourced directly from Redis

class FeedbackRequest(BaseModel):
    feedback: int
