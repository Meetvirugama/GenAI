"""
conftest.py
===========
Shared pytest fixtures for the multimodal_qa test suite.
"""
import os
from unittest.mock import MagicMock

import fakeredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Set all env vars BEFORE any imports so Config reads them correctly
# ---------------------------------------------------------------------------
os.environ.setdefault("GROQ_API_KEY", "fake-groq-key")
os.environ.setdefault("GEMINI_API_KEY", "fake-gemini-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")


# ---------------------------------------------------------------------------
# Fake Redis fixture (no real Redis needed)
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_redis_client():
    """Return a fakeredis client that behaves exactly like redis.Redis."""
    server = fakeredis.FakeServer()
    client = fakeredis.FakeRedis(server=server, decode_responses=True)
    return client


@pytest.fixture
def redis_manager(fake_redis_client):
    """Return a RedisMemoryManager with a fake Redis backend."""
    from app.core.memory import RedisMemoryManager
    rm = RedisMemoryManager.__new__(RedisMemoryManager)
    rm.ttl = 1800
    rm.client = fake_redis_client
    return rm


# ---------------------------------------------------------------------------
# FastAPI test client fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def api_client():
    """Return a TestClient with all dependencies mocked."""
    from app.api.endpoints.chat import chat_router

    from app.api.dependencies import get_current_user, get_db

    app = FastAPI()
    app.include_router(chat_router)

    async def override_user():
        return 1  # Mock user_id = 1

    def override_db():
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = MagicMock(
            id=1, name="Test User", email="test@example.com"
        )
        yield db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    # Mock app.state
    mock_agent = MagicMock()
    mock_agent.run.return_value = ("Test answer", "Trace info")
    app.state.agent = mock_agent
    app.state.doc_loader = MagicMock()
    app.state.vector_store = MagicMock()

    return TestClient(app)


# ---------------------------------------------------------------------------
# Mock agent fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_agent():
    """Return a MagicMock that simulates MultimodalAgent."""
    agent = MagicMock()
    agent.run.return_value = ("Hello! How can I help?", "Reasoning trace here")

    async def fake_astream(message, history=None):
        for token in ["Hello", " world", "!"]:
            yield token

    agent.astream = fake_astream
    return agent
