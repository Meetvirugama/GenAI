from typing import Generator, Tuple, List
# pyrefly: ignore [missing-import]
from langchain_groq import ChatGroq
# pyrefly: ignore [missing-import]
from langgraph.prebuilt import create_react_agent
from core.config import Config
from core.logger import get_logger
from tools.search import search_web
from tools.vision import describe_image
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = get_logger(__name__)

from agent.prompts import (
    BASE_SYSTEM_PROMPT,
    PLANNER_ROUTER_PROMPT,
    DOCUMENT_ANALYSIS_PROMPT,
    DEEP_PDF_UNDERSTANDING_PROMPT,
    IMAGE_ANALYSIS_PROMPT,
    CHART_TABLE_PROMPT,
    CODE_ANALYSIS_PROMPT,
    RESEARCH_PROMPT,
    QA_FORMATTING_PROMPT
)

def build_dynamic_prompt(state: dict) -> str:
    from core.context import image_path_var
    
    parts = [BASE_SYSTEM_PROMPT]
    
    has_image = bool(image_path_var.get())
    
    messages = state.get("messages", [])
    latest_msg = ""
    if messages and hasattr(messages[-1], "content"):
        latest_msg = messages[-1].content.lower()
        
    if has_image:
        parts.append(IMAGE_ANALYSIS_PROMPT)
        parts.append(CHART_TABLE_PROMPT)
        
    if any(keyword in latest_msg for keyword in ["compare", "research", "difference"]):
        parts.append(RESEARCH_PROMPT)
        
    if any(keyword in latest_msg for keyword in ["code", "error", "bug", "fix"]):
        parts.append(CODE_ANALYSIS_PROMPT)
        
    if any(keyword in latest_msg for keyword in ["document", "pdf", "summarize", "report"]):
        parts.append(DOCUMENT_ANALYSIS_PROMPT)
    parts.append("Answer the user's question directly. Use tools if needed to search for information. If you don't know the answer, say so.")
    return "\n\n".join(parts)


class MultimodalAgent:
    """
    LangGraph ReAct Agent with three tools:
    - search_documents (PDF RAG)
    - describe_image (Groq Vision)
    - search_web (DuckDuckGo)
    """

    def __init__(self, tools: List):
        primary_llm = ChatGroq(
            api_key=Config.GROQ_API_KEYS[0],
            model=Config.LLM_MODEL,
            temperature=0.2,
        )
        
        fallbacks = []
        # Add the remaining keys with the primary model
        for key in Config.GROQ_API_KEYS[1:]:
            fallbacks.append(ChatGroq(api_key=key, model=Config.LLM_MODEL, temperature=0.2))
            
        # Add all keys with the fallback model
        for key in Config.GROQ_API_KEYS:
            fallbacks.append(ChatGroq(api_key=key, model="llama-3.1-8b-instant", temperature=0.2))

        
        self.llm = primary_llm.with_fallbacks(fallbacks)
        self.tools = tools
        # The agent uses the graph logic to respond to the prompt.
        self.graph = create_react_agent(
            model=self.llm,
            tools=self.tools,
        )
        logger.info("MultimodalAgent initialized.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    def run(self, user_message: str, history: List[Tuple[str, str]] = None) -> Tuple[str, str]:
        """
        Runs the agent on a user message and returns the final answer + reasoning trace.

        Args:
            user_message: The user's question.
            history: Optional list of previous (user, ai) message tuples.

        Returns:
            Tuple of (final_answer: str, reasoning_trace: str)
        """
        logger.info(f"Agent run | Input: {user_message}")
        
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        
        # Build dynamic prompt manually
        parts = [BASE_SYSTEM_PROMPT]
        from core.context import image_path_var
        has_image = bool(image_path_var.get())
        if has_image:
            parts.append(IMAGE_ANALYSIS_PROMPT)
            parts.append(CHART_TABLE_PROMPT)
        if any(keyword in user_message.lower() for keyword in ["compare", "research", "difference"]):
            parts.append(RESEARCH_PROMPT)
        if any(keyword in user_message.lower() for keyword in ["code", "error", "bug", "fix"]):
            parts.append(CODE_ANALYSIS_PROMPT)
        if any(keyword in user_message.lower() for keyword in ["document", "pdf", "summarize", "report"]):
            parts.append(DOCUMENT_ANALYSIS_PROMPT)
        parts.append("Answer the user's question directly. Use tools if needed to search for information. If you don't know the answer, say so.")
        system_prompt_str = "\n\n".join(parts)
        
        messages = [SystemMessage(content=system_prompt_str)]
        
        if history:
            for h_user, h_ai in history:
                messages.append(HumanMessage(content=h_user))
                messages.append(AIMessage(content=h_ai))
        
        messages.append(HumanMessage(content=user_message))
        
        inputs = {"messages": messages}
        
        trace_lines = []
        final_answer = ""

        for step in self.graph.stream(inputs, config={"recursion_limit": 25}, stream_mode="values"):
            messages = step.get("messages", [])
            if not messages:
                continue
            last_msg = messages[-1]
            
            # Collect tool calls and observations
            msg_type = type(last_msg).__name__
            
            if msg_type == "AIMessage":
                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    for tc in last_msg.tool_calls:
                        trace_lines.append(f"🧠 **Thought** → Calling tool: `{tc['name']}`")
                        trace_lines.append(f"   **Input:** `{tc['args']}`")
                else:
                    # This is the final answer
                    final_answer = last_msg.content
                    trace_lines.append(f"✅ **Final Answer Generated**")

            elif msg_type == "ToolMessage":
                tool_name = getattr(last_msg, "name", "tool")
                content = last_msg.content
                preview = content[:300] + "..." if len(content) > 300 else content
                trace_lines.append(f"🔍 **Observation from `{tool_name}`:**\n```\n{preview}\n```")

        reasoning_trace = "\n\n".join(trace_lines) if trace_lines else "No trace available."
        return final_answer, reasoning_trace


