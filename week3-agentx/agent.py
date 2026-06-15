import os, datetime, uuid
from dotenv import load_dotenv

# pyrefly: ignore [missing-import]
from langchain_groq import ChatGroq
# pyrefly: ignore [missing-import]
from langchain_core.tools import tool
# pyrefly: ignore [missing-import]
from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
# pyrefly: ignore [missing-import]
from langchain_community.utilities import WikipediaAPIWrapper
# pyrefly: ignore [missing-import]
from langgraph.prebuilt import create_react_agent
# pyrefly: ignore [missing-import]
from langgraph.checkpoint.memory import MemorySaver
# pyrefly: ignore [missing-import]
from langgraph.errors import GraphRecursionError

load_dotenv()

# ── MODEL ──
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY", ""),
)

# ── TOOLS ──
@tool
def get_current_date() -> str:
    """Returns today's date. Use before searching when the query
    involves 'latest', 'current', 'today', or 'this year'."""
    return datetime.date.today().isoformat()

search = DuckDuckGoSearchRun(
    description=(
        "Search the web for real-time information. Use for current news, "
        "recent events, live data, or anything published after 2024. "
        "Do NOT use for background knowledge, history, or definitions."
    )
)

wiki = WikipediaQueryRun(
    api_wrapper=WikipediaAPIWrapper(top_k_results=2),
    description=(
        "Look up encyclopaedic information. Use for historical facts, "
        "scientific concepts, notable people, and background context. "
        "Do NOT use for current events or real-time information."
    )
)

tools = [search, wiki, get_current_date]

# ── SYSTEM PROMPT ──
TODAY = datetime.date.today().isoformat()
SYSTEM_PROMPT = f"""You are AgentX, a research assistant with access to web search and Wikipedia.
Today's date is {TODAY}.

When answering:
1. Always state which tool provided each piece of information.
2. Structure your final answer as: Introduction → Key Facts → Recent Developments → Conclusion.
3. If a question asks about something after 2024, use DuckDuckGo, not Wikipedia.
4. If you don't find good information after 2 searches, say so honestly — don't guess.
"""

# ── AGENT ──
memory = MemorySaver()
agent = create_react_agent(
    model=llm,
    tools=tools,
    checkpointer=memory,
    prompt=SYSTEM_PROMPT,
)


# ── INFERENCE WITH TRACE CAPTURE ──
def run_agent_with_trace(user_input: str, session_id: str) -> tuple[str, str]:
    """Returns (final_answer, formatted_trace_string)."""
    trace_log = []
    final_answer = ""
    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": 10,
    }

    try:
        for event in agent.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
            stream_mode="values",
        ):
            last = event["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                for tc in last.tool_calls:
                    trace_log.append(
                        f"→ Tool: {tc['name']}\n   Input: {tc['args']}"
                    )
            elif last.type == "ai" and not last.tool_calls:
                final_answer = last.content

    except GraphRecursionError:
        final_answer = (
            "⚠️ I couldn't finish within the step limit. "
            "Try rephrasing or narrowing your question."
        )
    except Exception as e:
        final_answer = f"An error occurred: {e}"

    trace_str = "\n\n".join(trace_log) if trace_log else "No tools were called."
    return final_answer, trace_str
