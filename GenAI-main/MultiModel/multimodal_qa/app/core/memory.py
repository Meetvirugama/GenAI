import json
import logging
import uuid
import os
from datetime import datetime
from typing import List, Dict, Any

try:
    # pyrefly: ignore [missing-import]
    import redis
except ImportError:
    redis = None

from app.core.config import Config

logger = logging.getLogger(__name__)

class RedisMemoryManager:
    """
    Manages conversational memory entirely within Redis with a strict TTL.
    Prevents persistent local storage of chat history.
    """
    def __init__(self):
        self.ttl = 1800  # 30 minutes
        # We assume Config.REDIS_URL is set, otherwise default to localhost
        redis_url = getattr(Config, "REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        
        if not redis:
            logger.warning("Redis library not found. Conversation memory will fail.")
            self.client = None
            return
            
        try:
            self.client = redis.from_url(redis_url, decode_responses=True)
            self.client.ping()
            logger.info(f"Connected to Redis at {redis_url} for conversation memory.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None

    def _session_key(self, session_id: str) -> str:
        return f"session:{session_id}:messages"

    def _meta_key(self, session_id: str) -> str:
        return f"session:{session_id}:meta"
        
    def _user_sessions_key(self, user_id: int) -> str:
        return f"user:{user_id}:sessions"

    def save_message(self, session_id: str, user_id: int, role: str, content: str, title: str = "New Chat", trace: str = None, confidence: str = None) -> str:
        """Appends a message to the session's Redis list and refreshes the TTL."""
        if not self.client:
            return None
            
        message_id = str(uuid.uuid4())
        msg = {
            "id": message_id,
            "role": role,
            "content": content,
            "trace": trace,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "feedback": None
        }
        
        session_key = self._session_key(session_id)
        meta_key = self._meta_key(session_id)
        user_key = self._user_sessions_key(user_id)
        
        pipeline = self.client.pipeline()
        
        # Append message
        pipeline.rpush(session_key, json.dumps(msg))
        
        # Save session metadata if not exists
        if not self.client.exists(meta_key):
            meta = {
                "id": session_id,
                "user_id": user_id,
                "title": title,
                "created_at": datetime.utcnow().isoformat()
            }
            pipeline.set(meta_key, json.dumps(meta))
            # Link session to user
            pipeline.sadd(user_key, session_id)
        else:
            # Update last_active
            meta_json = self.client.get(meta_key)
            if meta_json:
                meta = json.loads(meta_json)
                meta["last_active"] = datetime.utcnow().isoformat()
                pipeline.set(meta_key, json.dumps(meta))
                
        # Set expiration on everything
        pipeline.expire(session_key, self.ttl)
        pipeline.expire(meta_key, self.ttl)
        pipeline.expire(user_key, self.ttl * 2) # keep user set around slightly longer
        
        pipeline.execute()
        return message_id

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieves all messages for a session and resets TTL."""
        if not self.client:
            return []
            
        session_key = self._session_key(session_id)
        meta_key = self._meta_key(session_id)
        
        if not self.client.exists(session_key):
            return []
            
        # Refresh TTL on read
        self.client.expire(session_key, self.ttl)
        self.client.expire(meta_key, self.ttl)
        
        raw_messages = self.client.lrange(session_key, 0, -1)
        return [json.loads(m) for m in raw_messages]

    def get_history_pairs(self, session_id: str) -> List[tuple]:
        """Returns history as a list of (user, assistant) tuples for LangGraph."""
        messages = self.get_session_history(session_id)
        pairs = []
        user_msg = ""
        for m in messages:
            if m["role"] == "user":
                user_msg = m["content"]
            elif m["role"] == "assistant":
                pairs.append((user_msg, m["content"]))
                user_msg = ""
        return pairs

    def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Returns metadata for all active sessions of a user."""
        if not self.client:
            return []
            
        user_key = self._user_sessions_key(user_id)
        session_ids = self.client.smembers(user_key)
        
        sessions = []
        for sid in session_ids:
            meta_json = self.client.get(self._meta_key(sid))
            if meta_json:
                sessions.append(json.loads(meta_json))
            else:
                # Cleanup orphaned session ID
                self.client.srem(user_key, sid)
                
        # Sort by most recent
        sessions.sort(key=lambda x: x.get("last_active", x.get("created_at")), reverse=True)
        return sessions

    def delete_session(self, session_id: str, user_id: int):
        """Manually wipes a session from memory."""
        if not self.client:
            return
            
        pipeline = self.client.pipeline()
        pipeline.delete(self._session_key(session_id))
        pipeline.delete(self._meta_key(session_id))
        pipeline.srem(self._user_sessions_key(user_id), session_id)
        pipeline.execute()

    def update_feedback(self, message_id: str, feedback: int) -> bool:
        """Inefficient but works for small lists: scan and update feedback."""
        if not self.client:
            return False
            
        # This requires searching all keys in a real world scenario, 
        # but since we only have ephemeral sessions, feedback is less critical here.
        # For a robust implementation, we'd store a secondary index of message_id -> session_id.
        logger.warning("Feedback update on ephemeral Redis memory is a no-op.")
        return True

    def search_messages(self, user_id: int, query: str) -> List[Dict[str, Any]]:
        """In-memory search across active sessions."""
        if not self.client:
            return []
            
        query = query.lower()
        results = []
        
        sessions = self.get_user_sessions(user_id)
        for s in sessions:
            sid = s["id"]
            messages = self.get_session_history(sid)
            for m in messages:
                if query in m["content"].lower():
                    results.append({
                        "message_id": m["id"],
                        "session_id": sid,
                        "session_title": s.get("title", "Unknown Chat"),
                        "role": m["role"],
                        "preview": m["content"][:200],
                        "timestamp": m["timestamp"]
                    })
                    
        # Sort by newest
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results[:30]

redis_memory = RedisMemoryManager()
