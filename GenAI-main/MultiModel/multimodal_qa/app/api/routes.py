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
  #6  Session Expiry (via Redis TTL)
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
# pyrefly: ignore [missing-import]
from celery.result import AsyncResult

from app.core.logger import get_logger
from app.core.context import session_id_var, image_path_var
from app.api.dependencies import get_current_user, get_db
from app.core.database import AuditLog
from app.core.memory import redis_memory
from app.rag.tasks import process_document_task
from app.core.security import (
    limiter,
    is_prompt_injection,
    sanitize_output,
    validate_upload_file,
    calculate_confidence,
    is_valid_session_id,
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
    image_path: Optional[str] = None
    # 'history' is no longer expected from client, sourced directly from Redis


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

    if not is_valid_session_id(body.session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

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

    # Fetch history directly from Redis
    history = redis_memory.get_history_pairs(body.session_id)

    try:
        answer, trace = agent.run(body.message, history)

        # #5 Output Content Filter
        answer = sanitize_output(answer)

        # #9 Confidence Scoring
        confidence = calculate_confidence(answer, trace)

        message_id = None
        if user_id:
            # Save User Message to Redis
            redis_memory.save_message(
                session_id=body.session_id, 
                user_id=user_id, 
                role="user", 
                content=body.message,
                title=body.message[:50]
            )
            
            # Save Assistant Message to Redis
            message_id = redis_memory.save_message(
                session_id=body.session_id,
                user_id=user_id,
                role="assistant",
                content=answer,
                trace=trace,
                confidence=confidence["level"]
            )

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
    
    if not is_valid_session_id(body.session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

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
    
    # Fetch history directly from Redis
    history = redis_memory.get_history_pairs(body.session_id)

    full_answer_parts = []

    async def generate():
        try:
            async for token in agent.astream(body.message, history):
                full_answer_parts.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"
                await asyncio.sleep(0)  # yield control to event loop

            # After streaming completes: save to DB and send final metadata
            full_answer = sanitize_output("".join(full_answer_parts))
            # In streaming mode the tool-call trace is not captured separately.
            # Derive a synthetic trace from the answer itself: document analysis
            # responses always include source citations when RAG was used.
            _synthetic_trace = (
                "search_documents search_documents"
                if "(source:" in full_answer.lower() or "<source>" in full_answer.lower()
                else ("search_web" if "url:" in full_answer.lower() else "")
            )
            confidence = calculate_confidence(full_answer, _synthetic_trace)

            message_id = None
            if user_id:
                redis_memory.save_message(
                    session_id=body.session_id, 
                    user_id=user_id, 
                    role="user", 
                    content=body.message,
                    title=body.message[:50]
                )
                message_id = redis_memory.save_message(
                    session_id=body.session_id,
                    user_id=user_id,
                    role="assistant",
                    content=full_answer,
                    confidence=confidence["level"]
                )

            _audit(db, user_id=user_id, action="chat_stream", session_id=body.session_id,
                   input_preview=body.message, ip=ip, status="success")

            yield f"data: {json.dumps({'done': True, 'message_id': message_id, 'confidence': confidence})}\n\n"
            yield "data: [DONE]\n\n"

        except asyncio.CancelledError:
            logger.info(f"Stream cancelled by client mid-generation | session={body.session_id}")
            if full_answer_parts:
                partial_answer = sanitize_output("".join(full_answer_parts))
                if user_id:
                    # Save what we have so far
                    redis_memory.save_message(
                        session_id=body.session_id, 
                        user_id=user_id, 
                        role="user", 
                        content=body.message,
                        title=body.message[:50]
                    )
                    redis_memory.save_message(
                        session_id=body.session_id,
                        user_id=user_id,
                        role="assistant",
                        content=partial_answer,
                        confidence="low"
                    )
            raise
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── /api/search ────────────────────────────────────────────────────────────────
@chat_router.get("/search")
async def search_messages(q: str, user_id=Depends(get_current_user)):
    """
    Full-text search across all messages for the current user.
    Returns matching messages grouped by session, using Redis in-memory search.
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query too short")

    results = redis_memory.search_messages(user_id, q)
    return {"results": results}


# ── /api/sessions ──────────────────────────────────────────────────────────────
@chat_router.get("/sessions")
async def get_sessions(user_id=Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    sessions = redis_memory.get_user_sessions(user_id)
    return [{"id": s["id"], "title": s.get("title", "New Chat"), "created_at": s.get("created_at")} for s in sessions]


# ── /api/sessions/{id}/messages ───────────────────────────────────────────────
@chat_router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    if not is_valid_session_id(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")
        
    messages = redis_memory.get_session_history(session_id)
    # If session doesn't exist or expired in Redis
    if not messages:
        return {"messages": [], "files": [], "lastImagePath": None}

    from app.core.database import User
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

    return {
        "messages": messages,
        "files": files,
        "lastImagePath": last_image
    }


# ── /api/sessions/{id} DELETE ─────────────────────────────────────────────────
@chat_router.delete("/sessions/{session_id}")
async def delete_session(request: Request, session_id: str, user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    if not is_valid_session_id(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

    redis_memory.delete_session(session_id, user_id)

    from app.core.database import User
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

    return {"status": "success"}


# ── /api/messages/{id}/feedback ───────────────────────────────────────────────
@chat_router.post("/messages/{message_id}/feedback")
async def update_feedback(message_id: str, request: FeedbackRequest, user_id=Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
        
    redis_memory.update_feedback(message_id, request.feedback)
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
    
    if not is_valid_session_id(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")
        
    session_id_var.set(session_id)



    from app.core.database import User
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
        docx_files = [f for f in saved_files if f.lower().endswith((".docx", ".doc"))]
        pptx_files = [f for f in saved_files if f.lower().endswith((".pptx", ".ppt"))]
        html_files = [f for f in saved_files if f.lower().endswith((".html", ".htm"))]
        image_files = [f for f in saved_files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        doc_files = pdf_files + md_files + docx_files + pptx_files + html_files
        if doc_files:
            # Dispatch background job for all parseable document types
            task = process_document_task.delay(doc_files, session_id)
            task_id = task.id
        else:
            task_id = None

        # #4 Audit log
        _audit(db, user_id=user_id, action="upload", session_id=session_id,
               input_preview=", ".join(saved_filenames), ip=ip, status="success")

        return {
            "status": "processing" if task_id else "success",
            "task_id": task_id,
            "files": saved_filenames,
            "docs_queued": len(doc_files),
            "images_processed": len(image_files)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        _audit(db, user_id=user_id, action="upload", session_id=session_id,
               ip=ip, status="error", detail=str(e)[:200])
        raise HTTPException(status_code=500, detail=str(e))

# ── /api/tasks/{task_id} ───────────────────────────────────────────────────────
@chat_router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, user_id=Depends(get_current_user)):
    """Polling endpoint for clients to check background indexing status."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
        
    task_result = AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
    }
    
    if task_result.status == "SUCCESS":
        response["result"] = task_result.result
    elif task_result.status == "FAILURE":
        response["error"] = str(task_result.result)
    elif task_result.status in ["PARSING", "EMBEDDING"]:
        response["meta"] = task_result.info

    return response
