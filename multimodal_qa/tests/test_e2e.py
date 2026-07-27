from unittest.mock import MagicMock, patch

from app.api.endpoints.chat import chat_router
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_db

app = FastAPI()
app.include_router(chat_router)

async def override_get_current_user():
    return "1"

def override_get_db():
    yield MagicMock()

app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_db] = override_get_db

app.state.agent = MagicMock()
app.state.doc_loader = MagicMock()
app.state.vector_store = MagicMock()

client = TestClient(app)

@patch("app.api.endpoints.chat.redis_memory")
def test_e2e_user_journey(mock_redis):
    # 1. User is authenticated (overridden dependency)
    # 2. Start a chat session
    mock_redis.get_history_pairs.return_value = []
    app.state.agent.run.return_value = ("E2E Success", "Trace")
    
    response = client.post(
        "/api/chat", 
        json={"message": "What is the meaning of life?", "session_id": "e2e_session"}
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "E2E Success"
    
    # 3. Retrieve sessions
    mock_redis.get_user_sessions.return_value = [{"id": "e2e_session", "title": "New Chat"}]
    response = client.get("/api/sessions")
    assert response.status_code == 200
    assert len(response.json()) == 1
    
    # 4. Search
    mock_redis.search_messages.return_value = [{"msg": "What is the meaning of life?"}]
    response = client.get("/api/search?q=life")
    assert response.status_code == 200
    
    # 5. Delete session
    # mock vector store clear_session
    response = client.delete("/api/sessions/e2e_session")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    app.state.vector_store.clear_session.assert_called_once_with("e2e_session")
