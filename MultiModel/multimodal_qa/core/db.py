import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from core.config import Config
from core.logger import get_logger

logger = get_logger(__name__)

if not hasattr(Config, 'DATABASE_URL') or not Config.DATABASE_URL:
    Config.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/history.db")

engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")


class ChatSession(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)  # ← #6 Session Expiry

    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    trace = Column(Text, nullable=True)
    feedback = Column(Integer, nullable=True)
    confidence = Column(String, nullable=True)  # ← #9 Confidence Scoring ("high"/"medium"/"low")
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


class AuditLog(Base):
    """#4 Audit Logging — tracks every user action for security & compliance."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)        # "chat", "upload", "delete", "blocked"
    session_id = Column(String, nullable=True)
    input_preview = Column(String, nullable=True)  # first 120 chars of input
    ip_address = Column(String, nullable=True)
    status = Column(String, nullable=False)         # "success" / "blocked" / "error"
    detail = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


def init_db():
    try:
        if Config.DATABASE_URL.startswith("sqlite"):
            os.makedirs(os.path.dirname(Config.DATABASE_URL.split("///")[-1]), exist_ok=True)
        Base.metadata.create_all(bind=engine)

        # Safe column migrations for existing DBs
        for sql in [
            "ALTER TABLE messages ADD COLUMN feedback INTEGER",
            "ALTER TABLE messages ADD COLUMN trace TEXT",
            "ALTER TABLE messages ADD COLUMN confidence TEXT",
            "ALTER TABLE sessions ADD COLUMN last_active TIMESTAMP",
        ]:
            try:
                with engine.begin() as conn:
                    conn.execute(text(sql))
            except Exception:
                pass  # Column already exists

        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
