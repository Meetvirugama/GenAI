import pytest
import time
from app.core.memory import RedisMemoryManager

@pytest.fixture
def memory_manager():
    manager = RedisMemoryManager()
    if not manager.client:
        pytest.skip("Redis not available for testing")
    # For testing, reduce TTL so we don't pollute local redis
    manager.ttl = 1
    return manager

def test_save_and_retrieve_message(memory_manager):
    session_id = "test_sess_1"
    user_id = 999
    
    # Save a message
    msg_id = memory_manager.save_message(session_id, user_id, "user", "Hello Redis!")
    assert msg_id is not None
    
    # Retrieve
    history = memory_manager.get_session_history(session_id)
    assert len(history) == 1
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello Redis!"
    
    # Get user sessions
    sessions = memory_manager.get_user_sessions(user_id)
    assert len(sessions) == 1
    assert sessions[0]["id"] == session_id
    
    # Cleanup
    memory_manager.delete_session(session_id, user_id)
    assert len(memory_manager.get_session_history(session_id)) == 0

def test_ttl_expiration(memory_manager):
    session_id = "test_sess_expire"
    user_id = 888
    
    memory_manager.save_message(session_id, user_id, "user", "This will disappear.")
    
    # Wait for TTL (which is 1 second in tests)
    time.sleep(1.1)
    
    # History should be empty
    history = memory_manager.get_session_history(session_id)
    assert len(history) == 0
    
    # Cleanup user set
    memory_manager.client.delete(memory_manager._user_sessions_key(user_id))

def test_concurrent_sessions(memory_manager):
    user_id = 777
    
    # Save to two different sessions
    memory_manager.save_message("sess_A", user_id, "user", "Message A")
    memory_manager.save_message("sess_B", user_id, "user", "Message B")
    
    sessions = memory_manager.get_user_sessions(user_id)
    assert len(sessions) == 2
    
    hist_a = memory_manager.get_session_history("sess_A")
    hist_b = memory_manager.get_session_history("sess_B")
    
    assert hist_a[0]["content"] == "Message A"
    assert hist_b[0]["content"] == "Message B"
    
    memory_manager.delete_session("sess_A", user_id)
    memory_manager.delete_session("sess_B", user_id)
