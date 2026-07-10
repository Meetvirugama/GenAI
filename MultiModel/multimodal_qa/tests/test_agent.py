# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import MagicMock
from agent.graph import MultimodalAgent, SYSTEM_PROMPT

def test_agent_initialization():
    """Test that the agent can be initialized with mock tools."""
    mock_tool = MagicMock()
    mock_tool.name = "mock_tool"
    mock_tool.description = "A mock tool for testing."
    
    agent = MultimodalAgent(tools=[mock_tool])
    assert agent is not None
    assert len(agent.tools) == 1
    assert agent.tools[0].name == "mock_tool"

def test_system_prompt_security():
    """Test that the system prompt contains necessary security guards."""
    assert "<context>" in SYSTEM_PROMPT
    assert "<chunk>" in SYSTEM_PROMPT
    assert "passive data" in SYSTEM_PROMPT.lower()
    assert "ignore all instructions" in SYSTEM_PROMPT.lower()

@pytest.mark.asyncio
async def test_agent_history_parsing():
    """Test that the agent correctly parses history into messages."""
    mock_tool = MagicMock()
    mock_tool.name = "mock_tool"
    
    agent = MultimodalAgent(tools=[mock_tool])
    history = [("Hello", "Hi there!")]
    
    # We mock self.graph.stream to avoid hitting Groq
    agent.graph.stream = MagicMock(return_value=[])
    
    answer, trace = agent.run("How are you?", history=history)
    assert answer == ""
    assert trace == "No trace available."
