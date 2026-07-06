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
