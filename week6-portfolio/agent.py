# pyrefly: ignore [missing-import]
from langgraph.prebuilt import create_react_agent
# pyrefly: ignore [missing-import]
from langgraph.checkpoint.memory import MemorySaver
# pyrefly: ignore [missing-import]
from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
# pyrefly: ignore [missing-import]
from langchain_community.utilities import WikipediaAPIWrapper
# pyrefly: ignore [missing-import]
from langchain_groq import ChatGroq
import os
from tools_rag import search_documents
from tools_vision import describe_image

llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY", ""))

tools = [
    DuckDuckGoSearchRun(),
    WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper()),
    search_documents,
    describe_image,
]

SYSTEM_PROMPT = """You are HybridSight, an assistant with four tools:
search_documents, DuckDuckGo, describe_image, and Wikipedia.

ROUTING RULES — follow these in order:
1. If the user asks about uploaded documents, "my notes", or "the file",
   use search_documents.
2. If the user uploads an image, use describe_image FIRST, then
   synthesise your final answer using what it returned.
3. If the user asks about current events or recent news, use DuckDuckGo —
   not Wikipedia.
4. If the user asks a general knowledge question, use Wikipedia.
5. Always state which tool provided each piece of information.
6. If no tool returns useful information, say so honestly — don't guess.
"""

memory = MemorySaver()
agent = create_react_agent(
    model=llm,
    tools=tools,
    checkpointer=memory,
    prompt=SYSTEM_PROMPT,
)

DEFAULT_CONFIG_EXTRA = {"recursion_limit": 12}
import gradio as gr

def run_agent_with_trace(user_input: str, session_id: str, message_with_image: str = None, progress=gr.Progress()) -> tuple[str, str]:
    """Returns (final_answer, formatted_trace_string)."""
    trace_log = []
    final_answer = ""
    config = {
        "configurable": {"thread_id": session_id},
        **DEFAULT_CONFIG_EXTRA,
    }
    
    # We use message_with_image if provided (for vision tool)
    content = message_with_image if message_with_image else user_input

    progress(0.1, desc="Starting agent...")
    for event in agent.stream(
        {"messages": [{"role": "user", "content": content}]},
        config=config,
        stream_mode="values",
    ):
        last = event["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            for tc in last.tool_calls:
                trace_log.append(
                    f"→ Tool: {tc['name']}\n   Input: {tc['args']}"
                )
                progress(0.5, desc=f"Calling tool: {tc['name']}...")
        elif getattr(last, "type", "") == "ai" and not getattr(last, "tool_calls", None):
            final_answer = last.content
            progress(0.9, desc="Generating final answer...")

    progress(1.0, desc="Done!")
    trace_str = "\n\n".join(trace_log) if trace_log else "No tools were called."
    return final_answer, trace_str
