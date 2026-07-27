import pytest
from app.core.database import User, AuditLog
from app.core.logger import get_logger
from app.core.context import session_id_var, image_path_var

def test_db_models():
    user = User(email="test@test.com", name="Test User")
    assert user.email == "test@test.com"
    assert user.name == "Test User"
    
    log = AuditLog(user_id=1, action="test_action", status="success")
    assert log.action == "test_action"
    assert log.status == "success"

def test_logger():
    logger = get_logger("test_logger")
    assert logger.name == "test_logger"

def test_context_vars():
    # Test setting and getting context variables
    token_1 = session_id_var.set("session_123")
    assert session_id_var.get() == "session_123"
    
    token_2 = image_path_var.set("/tmp/img.png")
    assert image_path_var.get() == "/tmp/img.png"
    
    session_id_var.reset(token_1)
    image_path_var.reset(token_2)
