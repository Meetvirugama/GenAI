from contextvars import ContextVar

# Session ID for user tracking in a multi-user environment.
session_id_var: ContextVar[str] = ContextVar("session_id", default="default")

# Image path for the active session's image upload.
from typing import Optional
image_path_var: ContextVar[Optional[str]] = ContextVar("image_path", default=None)
