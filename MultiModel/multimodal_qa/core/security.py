"""
core/security.py
================
Central security module for NexusIQ.

Features implemented:
  #1  Rate Limiting  — via slowapi
  #3  Prompt Injection Filter
  #5  Output Content Filter
  #6  Session Expiry check
  #2  File type + size validation helpers
"""
import re
import filetype
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.logger import get_logger

logger = get_logger(__name__)

# ── #1 Rate Limiter ────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/hour"])

# ── #6 Session Expiry ──────────────────────────────────────────────────────────
SESSION_MAX_AGE_DAYS = 7


def check_session_expiry(last_active: datetime) -> bool:
    """Returns True if the session has expired (older than SESSION_MAX_AGE_DAYS)."""
    if last_active is None:
        return False
    return (datetime.utcnow() - last_active).days > SESSION_MAX_AGE_DAYS


# ── #3 Prompt Injection Filter ─────────────────────────────────────────────────
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions",
    r"forget\s+(everything|your\s+instructions|all\s+instructions)",
    r"\byou\s+are\s+now\b",
    r"\bact\s+as\s+(a|an)\b",
    r"\bpretend\s+(you\s+are|to\s+be)\b",
    r"\bdo\s+anything\s+now\b",
    r"\bdan\s+mode\b",
    r"reveal\s+(your\s+)?(system\s+prompt|instructions|prompt)",
    r"disregard\s+(all\s+)?(previous|prior|above)",
    r"new\s+instructions:",
    r"override\s+(previous\s+)?instructions",
    r"jailbreak",
]
_INJECTION_RE = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def is_prompt_injection(message: str) -> bool:
    """Returns True if the message appears to be a prompt injection attempt."""
    for pattern in _INJECTION_RE:
        if pattern.search(message):
            logger.warning(f"Prompt injection detected: '{message[:80]}'")
            return True
    return False


# ── #5 Output Content Filter ───────────────────────────────────────────────────
_BLOCKED_OUTPUT_PATTERNS = [
    "<script",
    "javascript:",
    "eval(",
    "os.system(",
    "subprocess.run(",
    "__import__(",
    "exec(",
]


def sanitize_output(answer: str) -> str:
    """Sanitizes the AI output, replacing dangerous patterns."""
    answer_lower = answer.lower()
    for pattern in _BLOCKED_OUTPUT_PATTERNS:
        if pattern.lower() in answer_lower:
            logger.warning(f"Output content filter triggered for pattern: {pattern}")
            return (
                "⚠️ The AI generated a response that was flagged by the content filter. "
                "Please rephrase your question."
            )
    return answer


# ── #2 File Validation ─────────────────────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB per file

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",        # .md files
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
}

# Extension whitelist as a fallback (for text/markdown which filetype may not detect)
ALLOWED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt", ".png", ".jpg", ".jpeg", ".webp"}


def validate_upload_file(filename: str, contents: bytes) -> None:
    """
    Validates an uploaded file's MIME type and size.
    Raises HTTPException if validation fails.
    """
    # Size check
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File '{filename}' exceeds the 25MB size limit."
        )

    # Extension check (primary check — filetype struggles with text files)
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' is not allowed. Supported: PDF, MD, PNG, JPG."
        )

    # MIME check via magic bytes (only reliable for binary formats)
    kind = filetype.guess(contents)
    if kind is not None:  # filetype returns None for text files — that's ok
        detected_mime = kind.mime
        if detected_mime not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File '{filename}' has a disallowed MIME type: {detected_mime}."
            )

    # Path traversal guard
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename."
        )


# ── #9 Confidence Scoring ──────────────────────────────────────────────────────
def calculate_confidence(answer: str, trace: str) -> dict:
    """
    Calculates a confidence level for an AI answer based on tool usage in the trace.

    Returns:
        dict with 'level' ("high"/"medium"/"low") and 'label' (human-readable string).
    """
    if not trace:
        return {"level": "low", "label": "General Knowledge"}

    trace_lower = trace.lower()

    # Count document citations
    doc_citations = trace_lower.count("search_documents")
    web_citations = trace_lower.count("search_web")

    # Also check if sources are cited in the answer
    answer_has_source = bool(re.search(r"\(source:", answer, re.IGNORECASE))

    if doc_citations >= 2 or (doc_citations >= 1 and answer_has_source):
        return {"level": "high", "label": "Well Sourced"}
    elif doc_citations >= 1 or web_citations >= 1:
        return {"level": "medium", "label": "Partially Sourced"}
    else:
        return {"level": "low", "label": "General Knowledge"}
