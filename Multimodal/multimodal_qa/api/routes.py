from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
import uuid
import json

from core.logger import get_logger
from core.context import session_id_var, image_path_var
from api.dependencies import get_current_user, get_db
from sqlalchemy.orm import Session
from core.db import ChatSession, Message

logger = get_logger(__name__)
chat_router = APIRouter(prefix="/api", tags=["Chat"])

class ChatRequest(BaseModel):
    message: str
    session_id: str
    history: Optional[List[dict]] = None
    image_path: Optional[str] = None

@chat_router.post("/chat")
async def chat_endpoint(request: Request, body: ChatRequest, user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Receives a chat message, passes it to the agent, and streams the response back.
    """
    logger.info(f"API Chat request for session {body.session_id}")
    
    agent = request.app.state.agent

    # Set context variables
    session_id_var.set(body.session_id)
    if body.image_path:
        image_path_var.set(body.image_path)
    else:
        image_path_var.set(None)

    # Format history
    history = []
    if body.history:
        for msg in body.history:
            history.append((msg.get("user", ""), msg.get("assistant", "")))

    try:
        # Currently, agent.run returns (answer, trace).
        # To truly stream, we would use agent.graph.astream_events(), but for now we return JSON
        # containing the final answer and trace.
        answer, trace = agent.run(body.message, history)
        
        # Save to DB if user is logged in
        if user_id:
            session = db.query(ChatSession).filter(ChatSession.id == body.session_id).first()
            if not session:
                session = ChatSession(id=body.session_id, user_id=user_id, title=body.message[:50])
                db.add(session)
            
            db.add(Message(session_id=body.session_id, role="user", content=body.message))
            db.add(Message(session_id=body.session_id, role="assistant", content=answer))
            db.commit()

        return {
            "answer": answer,
            "trace": trace
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@chat_router.get("/sessions")
async def get_sessions(user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc()).all()
    return [{"id": s.id, "title": s.title, "created_at": s.created_at} for s in sessions]

@chat_router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.timestamp.asc()).all()
    return [{"id": m.id, "role": m.role, "content": m.content, "timestamp": m.timestamp} for m in messages]

@chat_router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"status": "success"}

@chat_router.post("/upload")
async def upload_endpoint(
    request: Request,
    files: List[UploadFile] = File(...),
    session_id: str = Form(...)
):
    """
    Handles file uploads, processes them through the DocumentLoader, and adds them to VectorStore.
    """
    logger.info(f"API Upload request for session {session_id}")
    session_id_var.set(session_id)
    
    doc_loader = request.app.state.doc_loader
    vector_store = request.app.state.vector_store
    
    upload_dir = os.path.join(os.getcwd(), "data", "uploads", session_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    saved_files = []
    for file in files:
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(file_path)
        
    try:
        # Separate PDFs vs Images
        pdf_files = [f for f in saved_files if f.lower().endswith(".pdf")]
        image_files = [f for f in saved_files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if pdf_files:
            chunks = doc_loader.load_pdfs(pdf_files)
            vector_store.add_documents(chunks, session_id)
            
        return {
            "status": "success",
            "files": saved_files,
            "pdfs_processed": len(pdf_files),
            "images_processed": len(image_files)
        }
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
