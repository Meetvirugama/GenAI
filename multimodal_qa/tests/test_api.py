from unittest.mock import MagicMock, patch

from app.api.endpoints.chat import chat_router
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_db

app = FastAPI()
app.include_router(chat_router)

# Mock dependencies
async def override_get_current_user():
    return "1"

def override_get_db():
    mock_db = MagicMock()
    yield mock_db

app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_db] = override_get_db

# Mock app state dependencies
app.state.agent = MagicMock()
app.state.doc_loader = MagicMock()
app.state.vector_store = MagicMock()

client = TestClient(app)

@patch("app.api.endpoints.chat.redis_memory")
def test_chat_endpoint_success(mock_redis):
    # Mock redis memory return
    mock_redis.get_history_pairs.return_value = []
    
    # Mock agent return
    app.state.agent.run.return_value = ("Hello there!", "No trace")
    
    response = client.post(
        "/api/chat", 
        json={"message": "hello", "session_id": "test_session"}
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "Hello there!"
    assert response.json()["trace"] == "No trace"

def test_search_endpoint():
    with patch("app.api.endpoints.chat.redis_memory") as mock_redis:
        mock_redis.search_messages.return_value = [{"msg": "hello"}]
        response = client.get("/api/search?q=hello")
        assert response.status_code == 200
        assert "results" in response.json()

def test_sessions_endpoint():
    with patch("app.api.endpoints.chat.redis_memory") as mock_redis:
        mock_redis.get_user_sessions.return_value = [{"id": "s1", "title": "Session 1", "created_at": "2023-01-01"}]
        response = client.get("/api/sessions")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["id"] == "s1"
