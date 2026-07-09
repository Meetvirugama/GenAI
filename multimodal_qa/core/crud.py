from typing import List, Tuple
from core.db import SessionLocal, ChatSession, Message
from core.logger import get_logger

logger = get_logger(__name__)

def save_message(sid: str, role: str, content: str, user_id: int = None) -> None:
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.id == sid).first()
        if not session and user_id:
            session = ChatSession(id=sid, user_id=user_id)
            db.add(session)
            db.commit()
            db.refresh(session)
        
        if session:
            msg = Message(session_id=sid, role=role, content=content)
            db.add(msg)
            db.commit()
    except Exception as e:
        logger.error(f"Failed to save message: {e}")
    finally:
        db.close()

def fetch_user_sessions(user_id: int) -> List[List[str]]:
    db = SessionLocal()
    try:
        sessions = db.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc()).all()
        return [s.id for s in sessions]
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        return []
    finally:
        db.close()

def load_session_history(session_id: str) -> List[Tuple[str, str]]:
    db = SessionLocal()
    try:
        messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.timestamp.asc()).all()
        history = []
        user_msg = None
        for msg in messages:
            if msg.role == "user":
                user_msg = msg.content
            elif msg.role == "assistant":
                history.append((user_msg or "", msg.content))
                user_msg = None
        if user_msg:
            history.append((user_msg, ""))
        return history
    except Exception as e:
        logger.error(f"Error loading session history: {e}")
        return []
    finally:
        db.close()

def delete_session(session_id: str) -> bool:
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            db.delete(session)
            db.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return False
    finally:
        db.close()
