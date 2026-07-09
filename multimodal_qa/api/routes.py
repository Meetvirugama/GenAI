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
        message_id = None
        if user_id:
            session = db.query(ChatSession).filter(ChatSession.id == body.session_id).first()
            if not session:
                session = ChatSession(id=body.session_id, user_id=user_id, title=body.message[:50])
                db.add(session)
            
            db.add(Message(session_id=body.session_id, role="user", content=body.message))
            assistant_msg = Message(session_id=body.session_id, role="assistant", content=answer, trace=trace)
            db.add(assistant_msg)
            db.commit()
            db.refresh(assistant_msg)
            message_id = assistant_msg.id

        return {
            "answer": answer,
            "trace": trace,
            "message_id": message_id
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
    from core.db import User
    user = db.query(User).filter(User.id == user_id).first()
    user_folder = f"{user.name}_{user.email}".replace(" ", "_") if user else "anonymous"
    
    upload_dir = os.path.join(os.getcwd(), "data", "uploads", user_folder, session_id)
    files = []
    last_image = None
    if os.path.exists(upload_dir):
        all_files = sorted(os.listdir(upload_dir))
        for f in all_files:
            files.append(f)
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                last_image = os.path.join(upload_dir, f)
                
    messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.timestamp.asc()).all()
    return {
        "messages": [{"id": m.id, "role": m.role, "content": m.content, "timestamp": m.timestamp, "feedback": m.feedback, "trace": m.trace} for m in messages],
        "files": files,
        "lastImagePath": last_image
    }

@chat_router.delete("/sessions/{session_id}")
async def delete_session(request: Request, session_id: str, user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Remove files from filesystem
    from core.db import User
    user = db.query(User).filter(User.id == user_id).first()
    user_folder = f"{user.name}_{user.email}".replace(" ", "_") if user else "anonymous"
    upload_dir = os.path.join(os.getcwd(), "data", "uploads", user_folder, session_id)
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir, ignore_errors=True)
        
    # Remove vectors from ChromaDB
    try:
        vector_store = request.app.state.vector_store
        vector_store.clear_session(session_id)
    except Exception as e:
        logger.error(f"Error clearing vector store for session {session_id}: {e}")

    db.delete(session)
    db.commit()
    return {"status": "success"}

class FeedbackRequest(BaseModel):
    feedback: int

@chat_router.post("/messages/{message_id}/feedback")
async def update_feedback(message_id: int, request: FeedbackRequest, user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
        
    # Verify user owns the session this message belongs to
    session = db.query(ChatSession).filter(ChatSession.id == message.session_id).first()
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    message.feedback = request.feedback
    db.commit()
    return {"status": "success", "feedback": request.feedback}

@chat_router.post("/upload")
async def upload_endpoint(
    request: Request,
    files: List[UploadFile] = File(...),
    session_id: str = Form(...),
    user_id=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Handles file uploads, processes them through the DocumentLoader, and adds them to VectorStore.
    """
    logger.info(f"API Upload request for session {session_id}")
    session_id_var.set(session_id)
    
    doc_loader = request.app.state.doc_loader
    vector_store = request.app.state.vector_store
    
    from core.db import User
    from datetime import datetime
    
    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    user_folder = f"{user.name}_{user.email}".replace(" ", "_") if user else "anonymous"
    
    upload_dir = os.path.join(os.getcwd(), "data", "uploads", user_folder, session_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    saved_files = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for file in files:
        new_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, new_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(file_path)
        
    try:
        # Separate PDFs, Markdowns, vs Images
        pdf_files = [f for f in saved_files if f.lower().endswith(".pdf")]
        md_files = [f for f in saved_files if f.lower().endswith((".md", ".markdown"))]
        image_files = [f for f in saved_files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        docs_to_process = pdf_files + md_files
        if docs_to_process:
            chunks = doc_loader.load_documents(docs_to_process)
            vector_store.add_documents(chunks, session_id)
            
        return {
            "status": "success",
            "files": saved_files,
            "pdfs_processed": len(pdf_files),
            "mds_processed": len(md_files),
            "images_processed": len(image_files)
        }
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
