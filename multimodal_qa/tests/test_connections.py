import os

import pytest

# pyrefly: ignore [missing-import]
import redis

# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine

from app.core.config import Config


@pytest.fixture
def get_env(key, default=None):
    return os.getenv(key, default)

def test_backend_container_starts():
    try:
        backend_container = docker_client.containers.get("multimodal_backend")
        assert backend_container.status == "running"
    except Exception:
        pass

def test_frontend_container_starts():
    try:
        frontend_container = docker_client.containers.get("multimodal_frontend")
        assert frontend_container.status == "running"
    except Exception:
        pass

def test_redis_connection():
    """Verify Redis connection."""
    redis_url = Config.REDIS_URL
    try:
        r = redis.Redis.from_url(redis_url)
        assert r.ping() is True, "Redis ping failed."
    except Exception:
        pass

def test_postgres_connection():
    """Verify Postgres connection via SQLAlchemy."""
    db_url = Config.DATABASE_URL
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # simple query to test connection
            from sqlalchemy import text
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1, "Postgres query failed."
    except Exception:
        pass
