from __future__ import annotations
import uuid
from contextvars import ContextVar
from typing import Optional

# Context variables for the current request cycle
session_id_var: ContextVar[str] = ContextVar("session_id", default="")
image_path_var: ContextVar[Optional[str]] = ContextVar("image_path", default=None)
