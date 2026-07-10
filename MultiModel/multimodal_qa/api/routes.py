"""
api/routes.py
=============
All API endpoints for NexusIQ.

Security features wired in:
  #1  Rate Limiting (slowapi)
  #2  File MIME Validation + Size Limit
  #3  Prompt Injection Filter
  #4  Audit Logging
  #5  Output Content Filter
  #6  Session Expiry
  #9  Confidence Scoring (returned with chat response)
  #13 Streaming SSE endpoint (/api/chat/stream)
"""
import json
import os
import shutil
import asyncio

from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from core.logger import get_logger
from core.context import session_id_var, image_path_var
from api.dependencies import get_current_user, get_db
from core.db import ChatSession, Message, AuditLog
from core.security import (
    limiter,
    is_prompt_injection,
    sanitize_output,
    validate_upload_file,
    calculate_confidence,
    check_session_expiry,
)

logger = get_logger(__name__)
chat_router = APIRouter(prefix="/api", tags=["Chat"])

MAX_MESSAGE_LENGTH = 4000  # chars — prevents context overflow


# ── Helper: write audit log ────────────────────────────────────────────────────
def _audit(db: Session, *, user_id, action: str, session_id: str = None,
           input_preview: str = None, ip: str = None, status: str, detail: str = None):
    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            session_id=session_id,
            input_preview=(input_preview or "")[:120],
            ip_address=ip,
            status=status,
            detail=detail,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.warning(f"Audit log write failed: {e}")


# ── Models ─────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: str
    history: Optional[List[dict]] = None
    image_path: Optional[str] = None


class FeedbackRequest(BaseModel):
    feedback: int


# ── /api/chat ──────────────────────────────────────────────────────────────────
@chat_router.post("/chat")
@limiter.limit("30/minute")  # #1 Rate Limiting
async def chat_endpoint(
    request: Request,
    body: ChatRequest,
    user_id=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else "unknown"
    logger.info(f"Chat request | session={body.session_id} | user={user_id}")

    # #3 Prompt Injection Filter
    if is_prompt_injection(body.message):
        _audit(db, user_id=user_id, action="chat", session_id=body.session_id,
               input_preview=body.message, ip=ip, status="blocked", detail="prompt_injection")
        return {
            "answer": "⚠️ Your message was flagged by our security filter. Please rephrase.",
            "trace": None,
            "message_id": None,
            "confidence": {"level": "low", "label": "Blocked"}
        }

    # Message length guard
    if len(body.message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail=f"Message too long (max {MAX_MESSAGE_LENGTH} characters).")

    agent = request.app.state.agent

    session_id_var.set(body.session_id)
    image_path_var.set(body.image_path or None)

    history = [(m.get("user", ""), m.get("assistant", "")) for m in (body.history or [])]

    try:
        answer, trace = agent.run(body.message, history)

        # #5 Output Content Filter
        answer = sanitize_output(answer)

        # #9 Confidence Scoring
        confidence = calculate_confidence(answer, trace)

        message_id = None
        if user_id:
            session = db.query(ChatSession).filter(ChatSession.id == body.session_id).first()
            if not session:
                session = ChatSession(id=body.session_id, user_id=user_id, title=body.message[:50])
                db.add(session)

            # #6 Update last_active
            session.last_active = datetime.utcnow()

            db.add(Message(session_id=body.session_id, role="user", content=body.message))
            assistant_msg = Message(
                session_id=body.session_id, role="assistant",
                content=answer, trace=trace,
                confidence=confidence["level"]
            )
            db.add(assistant_msg)
            db.commit()
            db.refresh(assistant_msg)
            message_id = assistant_msg.id

        # #4 Audit log
        _audit(db, user_id=user_id, action="chat", session_id=body.session_id,
               input_preview=body.message, ip=ip, status="success")

        return {"answer": answer, "trace": trace, "message_id": message_id, "confidence": confidence}

    except Exception as e:
        logger.error(f"Chat error: {e}")
        _audit(db, user_id=user_id, action="chat", session_id=body.session_id,
               input_preview=body.message, ip=ip, status="error", detail=str(e)[:200])
        raise HTTPException(status_code=500, detail=str(e))


# ── #13 /api/chat/stream (SSE) ─────────────────────────────────────────────────
@chat_router.post("/chat/stream")
@limiter.limit("30/minute")
async def chat_stream_endpoint(
    request: Request,
    body: ChatRequest,
    user_id=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Streams the AI response token-by-token using Server-Sent Events (SSE)."""
    ip = request.client.host if request.client else "unknown"

    if is_prompt_injection(body.message):
        _audit(db, user_id=user_id, action="chat_stream", session_id=body.session_id,
               input_preview=body.message, ip=ip, status="blocked")

        async def blocked():
            yield f"data: {json.dumps({'token': '⚠️ Message blocked by security filter.'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(blocked(), media_type="text/event-stream")

    if len(body.message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail="Message too long.")

    agent = request.app.state.agent
    session_id_var.set(body.session_id)
    image_path_var.set(body.image_path or None)
    history = [(m.get("user", ""), m.get("assistant", "")) for m in (body.history or [])]

    full_answer_parts = []

    async def generate():
        try:
            async for token in agent.astream(body.message, history):
                full_answer_parts.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"
                await asyncio.sleep(0)  # yield control to event loop

            # After streaming completes: save to DB and send final metadata
            full_answer = sanitize_output("".join(full_answer_parts))
            confidence = calculate_confidence(full_answer, "")

            message_id = None
            if user_id:
                session = db.query(ChatSession).filter(ChatSession.id == body.session_id).first()
                if not session:
                    session = ChatSession(id=body.session_id, user_id=user_id, title=body.message[:50])
                    db.add(session)
                session.last_active = datetime.utcnow()
                db.add(Message(session_id=body.session_id, role="user", content=body.message))
                assistant_msg = Message(
                    session_id=body.session_id, role="assistant",
                    content=full_answer, confidence=confidence["level"]
                )
                db.add(assistant_msg)
                db.commit()
                db.refresh(assistant_msg)
                message_id = assistant_msg.id

            _audit(db, user_id=user_id, action="chat_stream", session_id=body.session_id,
                   input_preview=body.message, ip=ip, status="success")

            yield f"data: {json.dumps({'done': True, 'message_id': message_id, 'confidence': confidence})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── /api/search ────────────────────────────────────────────────────────────────
@chat_router.get("/search")
async def search_messages(q: str, user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Full-text search across all messages for the current user.
    Returns matching messages grouped by session.
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query too short")

    q_lower = f"%{q.strip().lower()}%"

    # Get user's session IDs
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user_id).all()
    session_map = {s.id: s.title for s in sessions}
    session_ids = list(session_map.keys())

    if not session_ids:
        return {"results": []}

    # Search messages (case-insensitive via LIKE — works on both SQLite and Postgres)
    from sqlalchemy import func
    matches = (
        db.query(Message)
        .filter(
            Message.session_id.in_(session_ids),
            func.lower(Message.content).like(q_lower)
        )
        .order_by(Message.timestamp.desc())
        .limit(30)
        .all()
    )

    results = [
        {
            "message_id": m.id,
            "session_id": m.session_id,
            "session_title": session_map.get(m.session_id, "Unknown Chat"),
            "role": m.role,
            "preview": m.content[:200],
            "timestamp": str(m.timestamp),
        }
        for m in matches
    ]
    return {"results": results}


# ── /api/sessions ──────────────────────────────────────────────────────────────
@chat_router.get("/sessions")
async def get_sessions(user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc()).all()
    return [{"id": s.id, "title": s.title, "created_at": s.created_at} for s in sessions]


# ── /api/sessions/{id}/messages ───────────────────────────────────────────────
@chat_router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # #6 Session expiry check
    if check_session_expiry(session.last_active):
        raise HTTPException(status_code=401, detail="Session expired. Please start a new chat.")

    from core.db import User
    user = db.query(User).filter(User.id == user_id).first()
    user_folder = f"{user.name}_{user.email}".replace(" ", "_") if user else "anonymous"

    upload_dir = os.path.join(os.getcwd(), "data", "uploads", user_folder, session_id)
    files = []
    last_image = None
    if os.path.exists(upload_dir):
        for f in sorted(os.listdir(upload_dir)):
            files.append(f)
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                last_image = os.path.join(upload_dir, f)

    messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.timestamp.asc()).all()
    return {
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content,
             "timestamp": str(m.timestamp), "feedback": m.feedback,
             "trace": m.trace, "confidence": m.confidence}
            for m in messages
        ],
        "files": files,
        "lastImagePath": last_image
    }


# ── /api/sessions/{id} DELETE ─────────────────────────────────────────────────
@chat_router.delete("/sessions/{session_id}")
async def delete_session(request: Request, session_id: str, user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from core.db import User
    user = db.query(User).filter(User.id == user_id).first()
    user_folder = f"{user.name}_{user.email}".replace(" ", "_") if user else "anonymous"
    upload_dir = os.path.join(os.getcwd(), "data", "uploads", user_folder, session_id)
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir, ignore_errors=True)

    try:
        vector_store = request.app.state.vector_store
        vector_store.clear_session(session_id)
    except Exception as e:
        logger.error(f"Vector store clear error: {e}")

    db.delete(session)
    db.commit()
    return {"status": "success"}


# ── /api/messages/{id}/feedback ───────────────────────────────────────────────
@chat_router.post("/messages/{message_id}/feedback")
async def update_feedback(message_id: int, request: FeedbackRequest, user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    session = db.query(ChatSession).filter(ChatSession.id == message.session_id).first()
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    message.feedback = request.feedback
    db.commit()
    return {"status": "success", "feedback": request.feedback}


# ── /api/upload ────────────────────────────────────────────────────────────────
@chat_router.post("/upload")
@limiter.limit("10/hour")  # #1 Rate Limiting (stricter for uploads)
async def upload_endpoint(
    request: Request,
    files: List[UploadFile] = File(...),
    session_id: str = Form(...),
    user_id=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else "unknown"
    logger.info(f"Upload request | session={session_id}")
    session_id_var.set(session_id)

    doc_loader = request.app.state.doc_loader
    vector_store = request.app.state.vector_store

    from core.db import User
    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    user_folder = f"{user.name}_{user.email}".replace(" ", "_") if user else "anonymous"

    upload_dir = os.path.join(os.getcwd(), "data", "uploads", user_folder, session_id)
    os.makedirs(upload_dir, exist_ok=True)

    saved_files = []
    saved_filenames = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for file in files:
        # #2 File Validation — read full content for validation
        contents = await file.read()
        validate_upload_file(file.filename, contents)  # raises HTTPException if invalid

        new_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, new_filename)
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        saved_files.append(file_path)
        saved_filenames.append(new_filename)

    try:
        pdf_files = [f for f in saved_files if f.lower().endswith(".pdf")]
        md_files = [f for f in saved_files if f.lower().endswith((".md", ".markdown"))]
        image_files = [f for f in saved_files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        if pdf_files + md_files:
            chunks = doc_loader.load_documents(pdf_files + md_files)
            vector_store.add_documents(chunks, session_id)

        # #4 Audit log
        _audit(db, user_id=user_id, action="upload", session_id=session_id,
               input_preview=", ".join(saved_filenames), ip=ip, status="success")

        return {
            "status": "success",
            "files": saved_filenames,
            "pdfs_processed": len(pdf_files),
            "mds_processed": len(md_files),
            "images_processed": len(image_files)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        _audit(db, user_id=user_id, action="upload", session_id=session_id,
               ip=ip, status="error", detail=str(e)[:200])
        raise HTTPException(status_code=500, detail=str(e))
