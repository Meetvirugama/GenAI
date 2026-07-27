import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from app.core.config import Config
from app.core.logger import get_logger

logger = get_logger(__name__)

if not hasattr(Config, 'DATABASE_URL') or not Config.DATABASE_URL:
    Config.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/history.db")

if Config.DATABASE_URL.startswith("sqlite"):
    # SQLite doesn't support advanced pooling in the same way, but needs thread checks disabled
    # For :memory: databases, it uses SingletonThreadPool which rejects max_overflow, pool_size, etc.
    engine = create_engine(
        Config.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        Config.DATABASE_URL,
        pool_size=20,          # Allow up to 20 concurrent connections
        max_overflow=30,       # Allow up to 30 extra connections if pool is exhausted
        pool_timeout=30,       # Wait up to 30 seconds for a connection
        pool_pre_ping=True,    # Verify connection is alive before using
        pool_recycle=1800      # Recycle connections after 30 minutes
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)





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
            db_path = Config.DATABASE_URL.split("///")[-1]
            db_dir = os.path.dirname(db_path)
            if db_dir:  # Guard against empty string (e.g., in-memory SQLite)
                os.makedirs(db_dir, exist_ok=True)
        Base.metadata.create_all(bind=engine)

        # Safe migrations can be run here if needed for User/AuditLog

        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")


# get_db() is defined in app/api/dependencies.py and injected via FastAPI Depends().
# This module does not re-export it to avoid duplicate definitions.
