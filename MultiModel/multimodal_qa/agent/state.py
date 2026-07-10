from typing import TypedDict, Annotated
# pyrefly: ignore [missing-import]
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Represents the state of the ReAct agent graph.

    Attributes:
        messages: The full conversation message history (auto-appended by LangGraph).
    """
    messages: Annotated[list, add_messages]
