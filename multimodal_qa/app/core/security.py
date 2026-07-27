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
from datetime import datetime, timezone

import filetype
from fastapi import HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.logger import get_logger

logger = get_logger(__name__)

# ── #1 Rate Limiter ────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/hour"])

# ── #6 Session Expiry ──────────────────────────────────────────────────────────
SESSION_MAX_AGE_DAYS = 7


def check_session_expiry(last_active: datetime) -> bool:
    """Returns True if the session has expired (older than SESSION_MAX_AGE_DAYS)."""
    if last_active is None:
        return False
    return (datetime.now(timezone.utc) - last_active).days > SESSION_MAX_AGE_DAYS


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
# Only block patterns that are dangerous when rendered in a browser (XSS vectors).
# Python code patterns like eval(), exec(), os.system() etc. are legitimate topics
# for a coding assistant and must NOT be blocked — blocking them wipes valid answers.
_BLOCKED_OUTPUT_PATTERNS = [
    "<script",
    "javascript:",
]


def sanitize_output(answer: str) -> str:
    """Sanitizes the AI output by stripping browser-executable injection vectors.

    Only HTML/JS injection patterns are blocked. Python API names (eval, exec,
    subprocess, etc.) are intentionally NOT in this list — they are safe in text
    responses and are common topics for a coding assistant.
    """
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
    "text/plain",        # .md / .txt files
    "text/html",         # .html / .htm files
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    # DOCX / PPTX are ZIP-based; filetype.guess() returns "application/zip" for them.
    # We add the real MIME types here so they are accepted when a more capable
    # detection library is used in the future.  The primary guard is the extension check.
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    "application/zip",   # generic ZIP (covers .docx / .pptx from filetype.guess)
}

# Extensions that use ZIP as their container format.  filetype.guess() returns
# "application/zip" for these, which would incorrectly fail the MIME check above.
# We skip the MIME check for these extensions and rely solely on the extension guard.
_ZIP_BACKED_EXTENSIONS = {".docx", ".doc", ".pptx", ".ppt"}

# Extension whitelist — primary validation gate
ALLOWED_EXTENSIONS = {
    ".pdf", ".md", ".markdown", ".txt",
    ".docx", ".doc",
    ".pptx", ".ppt",
    ".html", ".htm",
    ".png", ".jpg", ".jpeg", ".webp",
}


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

    # MIME check via magic bytes (only reliable for binary formats).
    # Skip for ZIP-backed office formats (.docx, .pptx) because filetype.guess()
    # returns "application/zip" for them, which would incorrectly block valid files.
    kind = filetype.guess(contents)
    if kind is not None and ext not in _ZIP_BACKED_EXTENSIONS:
        detected_mime = kind.mime
        if detected_mime not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File '{filename}' has a disallowed MIME type: {detected_mime}."
            )

    # Path traversal guard (using strict regex)
    if not is_valid_session_id(filename.rsplit(".", 1)[0]):
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename."
            )
            
    # Malware Scan (Mock implementation checking for EICAR signature)
    scan_for_malware(contents)


def scan_for_malware(contents: bytes) -> None:
    """
    Scans the file contents for known malware signatures.
    If a signature is found, raises an HTTPException.
    """
    # EICAR standard test signature (often used for testing antivirus engines)
    eicar_signature = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    if eicar_signature in contents:
        logger.warning("Malware scan failed: EICAR signature detected.")
        raise HTTPException(
            status_code=403,
            detail="File rejected: Malware signature detected."
        )

def is_valid_session_id(session_id: str) -> bool:
    """
    Validates a session ID to prevent Path Traversal or Injection attacks.
    Only allows alphanumeric characters, dashes, and underscores.
    """
    if not session_id or len(session_id) > 64:
        return False
    # Strict regex: alphanumeric, dash, underscore only
    return bool(re.match(r"^[a-zA-Z0-9_-]+$", session_id))


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
