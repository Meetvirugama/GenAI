from typing import Tuple, List, AsyncIterator
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


# ── #5 Dynamic Temperature ─────────────────────────────────────────────────────
def get_temperature(user_message: str) -> float:
    """Returns the optimal LLM temperature based on query type."""
    msg = user_message.lower()
    if any(k in msg for k in ["write", "create", "story", "poem", "design", "generate", "draft"]):
        return 0.7   # Creative — allow more variety
    if any(k in msg for k in ["code", "fix", "debug", "implement", "function", "syntax", "error", "bug"]):
        return 0.05  # Code — be very precise
    if any(k in msg for k in ["yes", "no", "is it", "does", "can i", "will", "should i"]):
        return 0.0   # Factual yes/no — deterministic
    return 0.2       # Default — balanced

from agent.prompts import (
    BASE_SYSTEM_PROMPT,
    PLANNER_ROUTER_PROMPT,
    DOCUMENT_ANALYSIS_PROMPT,
    IMAGE_ANALYSIS_PROMPT,
    CHART_TABLE_PROMPT,
    CODE_ANALYSIS_PROMPT,
    RESEARCH_PROMPT,
    QA_FORMATTING_PROMPT
)

# ── #10 Memory Summarization threshold ─────────────────────────────────────────
MEMORY_SUMMARY_THRESHOLD = 10  # Summarize when history exceeds this many pairs


class MultimodalAgent:
    """
    LangGraph ReAct Agent with three tools:
    - search_documents (PDF RAG + Hybrid BM25)
    - describe_image (Groq Vision)
    - search_web (DuckDuckGo)

    Security & Quality features:
    - #10 Conversation memory summarization
    - #11 Query rewriting before RAG search
    - #13 Async streaming via astream_events
    """

    def __init__(self, tools: List):
        # #5 Dynamic temperature — start with default, overridden per-request in run()
        primary_llm = ChatGroq(
            api_key=Config.GROQ_API_KEYS[0],
            model=Config.LLM_MODEL,
            temperature=0.2,
        )

        fallbacks = []
        for key in Config.GROQ_API_KEYS[1:]:
            fallbacks.append(ChatGroq(api_key=key, model=Config.LLM_MODEL, temperature=0.2))
        for key in Config.GROQ_API_KEYS:
            fallbacks.append(ChatGroq(api_key=key, model="llama-3.1-8b-instant", temperature=0.2))

        self.llm = primary_llm.with_fallbacks(fallbacks)
        self.tools = tools
        # Store config for dynamic temperature rebuilding
        self._primary_key = Config.GROQ_API_KEYS[0]
        self._model = Config.LLM_MODEL
        self.graph = create_react_agent(
            model=self.llm,
            tools=self.tools,
        )
        logger.info("MultimodalAgent initialized.")

    def _get_llm_for_query(self, user_message: str) -> ChatGroq:
        """#5 Returns an LLM instance with temperature tuned to the query type."""
        temp = get_temperature(user_message)
        llm = ChatGroq(api_key=self._primary_key, model=self._model, temperature=temp)
        fallbacks = []
        for key in Config.GROQ_API_KEYS[1:]:
            fallbacks.append(ChatGroq(api_key=key, model=self._model, temperature=temp))
        for key in Config.GROQ_API_KEYS:
            fallbacks.append(ChatGroq(api_key=key, model="llama-3.1-8b-instant", temperature=temp))
        return llm.with_fallbacks(fallbacks)

    def _self_reflect(self, question: str, answer: str) -> str:
        """
        #1 Self-Reflection Loop — runs a critic LLM pass on the generated answer.
        If the answer is vague/incomplete, the critic explains why and we return
        the improved critique as a notice. Returns the original answer if it passes.
        """
        if len(answer) < 30:  # Too short — skip reflection
            return answer
        try:
            critic_prompt = f"""You are a strict AI quality reviewer. Evaluate this AI response for:
1. Accuracy (no hallucinations)
2. Completeness (does it fully answer the question?)
3. Format (is it well-structured with headers/bullets if needed?)

Question: {question}

Response:
{answer[:1500]}

Reply with either:
- PASS (if the response is accurate, complete, and well-formatted)
- REVISE: [specific 1-sentence reason]

Your verdict (PASS or REVISE only):"""
            verdict = self.llm.invoke(critic_prompt).content.strip()
            if verdict.upper().startswith("REVISE"):
                reason = verdict.replace("REVISE:", "").replace("REVISE", "").strip()
                logger.info(f"Self-reflection triggered revision: {reason}")
                # Append the critique hint to guide the user
                return answer + f"\n\n---\n> ⚠️ *Auto-review note: {reason}*"
            logger.info("Self-reflection: PASS")
        except Exception as e:
            logger.warning(f"Self-reflection failed: {e}")
        return answer

    def _build_system_prompt(self, user_message: str, has_image: bool) -> str:
        """Builds an adaptive system prompt based on the question type."""
        parts = [BASE_SYSTEM_PROMPT, PLANNER_ROUTER_PROMPT]
        msg_lower = user_message.lower()

        if has_image:
            parts.append(IMAGE_ANALYSIS_PROMPT)
            parts.append(CHART_TABLE_PROMPT)

        if any(k in msg_lower for k in ["compare", "vs", "versus", "difference", "better", "research", "pros and cons"]):
            parts.append(RESEARCH_PROMPT)

        if any(k in msg_lower for k in ["code", "write a", "implement", "function", "error", "bug", "fix", "script", "program", "syntax"]):
            parts.append(CODE_ANALYSIS_PROMPT)

        if any(k in msg_lower for k in ["document", "pdf", "file", "uploaded", "summarize", "report", "analyze", "what does", "according to"]):
            parts.append(DOCUMENT_ANALYSIS_PROMPT)

        parts.append(QA_FORMATTING_PROMPT)
        return "\n\n".join(parts)

    def _rewrite_query(self, user_message: str, history_pairs: List[Tuple[str, str]]) -> str:
        """
        #11 Query Rewriting — rewrites vague/contextual queries to be search-optimized.
        E.g., "what about that second one?" → "What is the second problem statement in the document?"
        """
        # Only rewrite if there's history and query seems contextual
        if not history_pairs:
            return user_message

        contextual_indicators = ["that", "this", "it", "those", "them", "he", "she", "they",
                                  "what about", "tell me more", "explain more", "elaborate"]
        msg_lower = user_message.lower().strip()
        needs_rewrite = any(msg_lower.startswith(w) or f" {w} " in msg_lower for w in contextual_indicators)

        if not needs_rewrite and len(user_message.split()) > 8:
            return user_message  # Long, specific query — no rewrite needed

        try:
            recent = history_pairs[-3:]
            history_str = "\n".join([f"User: {u}\nAI: {a[:150]}..." for u, a in recent])
            rewrite_prompt = f"""Given this conversation history and the new user question, rewrite the question to be a clear, standalone search query.
Remove vague references like "it", "that", "the second one" — replace with the actual subject from context.
Return ONLY the rewritten query, no explanation.

History:
{history_str}

Question: {user_message}
Rewritten:"""
            response = self.llm.invoke(rewrite_prompt)
            rewritten = response.content.strip().strip('"').strip("'")
            if rewritten and rewritten != user_message:
                logger.info(f"Query rewritten: '{user_message}' → '{rewritten}'")
            return rewritten or user_message
        except Exception as e:
            logger.warning(f"Query rewrite failed: {e}")
            return user_message

    def _compress_history(self, history_pairs: List[Tuple[str, str]], messages_list: list) -> list:
        """
        #10 Memory Summarization — if history is too long, summarize old turns.
        Keeps the last MEMORY_SUMMARY_THRESHOLD pairs intact, summarizes the rest.
        """
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        if len(history_pairs) <= MEMORY_SUMMARY_THRESHOLD:
            return messages_list  # Short enough, return as-is

        # Split into old (to summarize) and recent (to keep)
        old_pairs = history_pairs[:-MEMORY_SUMMARY_THRESHOLD]
        recent_pairs = history_pairs[-MEMORY_SUMMARY_THRESHOLD:]

        try:
            old_text = "\n".join([f"User: {u}\nAI: {a}" for u, a in old_pairs])
            summary_prompt = f"Summarize this conversation in 3-5 sentences, capturing key facts, questions answered, and any uploaded documents discussed:\n\n{old_text}"
            summary_response = self.llm.invoke(summary_prompt)
            summary = summary_response.content.strip()

            # Rebuild messages: [system] + [summary] + [recent pairs] + [current]
            new_messages = []
            # Find system message
            for m in messages_list:
                if type(m).__name__ == "SystemMessage":
                    new_messages.append(m)
                    break

            new_messages.append(SystemMessage(content=f"[Conversation Summary — earlier turns]: {summary}"))

            for u, a in recent_pairs:
                new_messages.append(HumanMessage(content=u))
                new_messages.append(AIMessage(content=a))

            # Add the current user message (last in messages_list)
            new_messages.append(messages_list[-1])
            logger.info(f"Memory summarized: {len(old_pairs)} old pairs → 1 summary block")
            return new_messages
        except Exception as e:
            logger.warning(f"Memory summarization failed: {e}")
            return messages_list

    def _build_messages(self, user_message: str, history: List[Tuple[str, str]], system_prompt: str) -> list:
        """Builds the full message list with system prompt, history, and current query."""
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        messages = [SystemMessage(content=system_prompt)]

        if history:
            for h_user, h_ai in history:
                messages.append(HumanMessage(content=h_user))
                messages.append(AIMessage(content=h_ai))

        messages.append(HumanMessage(content=user_message))
        return messages

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    def run(self, user_message: str, history: List[Tuple[str, str]] = None) -> Tuple[str, str]:
        """
        Synchronous run — returns (final_answer, reasoning_trace).
        Applies #11 query rewriting and #10 memory summarization.
        """
        history = history or []
        logger.info(f"Agent run | Input: {user_message[:80]}")

        from core.context import image_path_var
        has_image = bool(image_path_var.get())
        system_prompt = self._build_system_prompt(user_message, has_image)

        # #11 Query rewriting
        search_query = self._rewrite_query(user_message, history)

        messages = self._build_messages(search_query if search_query != user_message else user_message,
                                        history, system_prompt)

        # #10 Memory summarization for long conversations
        messages = self._compress_history(history, messages)

        inputs = {"messages": messages}
        trace_lines = []
        final_answer = ""

        for step in self.graph.stream(inputs, config={"recursion_limit": 25}, stream_mode="values"):
            step_messages = step.get("messages", [])
            if not step_messages:
                continue
            last_msg = step_messages[-1]
            msg_type = type(last_msg).__name__

            if msg_type == "AIMessage":
                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    for tc in last_msg.tool_calls:
                        trace_lines.append(f"🧠 **Thought** → Calling tool: `{tc['name']}`")
                        trace_lines.append(f"   **Input:** `{tc['args']}`")
                else:
                    final_answer = last_msg.content
                    trace_lines.append("✅ **Final Answer Generated**")

            elif msg_type == "ToolMessage":
                tool_name = getattr(last_msg, "name", "tool")
                content = last_msg.content
                preview = content[:300] + "..." if len(content) > 300 else content
                trace_lines.append(f"🔍 **Observation from `{tool_name}`:**\n```\n{preview}\n```")

        reasoning_trace = "\n\n".join(trace_lines) if trace_lines else "No trace available."
        # #1 Self-Reflection — quality-check the answer before returning
        final_answer = self._self_reflect(user_message, final_answer)
        return final_answer, reasoning_trace

    async def astream(self, user_message: str, history: List[Tuple[str, str]] = None) -> AsyncIterator[str]:
        """
        #13 Streaming — yields tokens one by one using astream_events.
        Used by the /api/chat/stream SSE endpoint.
        """
        history = history or []
        from core.context import image_path_var
        has_image = bool(image_path_var.get())
        system_prompt = self._build_system_prompt(user_message, has_image)
        search_query = self._rewrite_query(user_message, history)
        messages = self._build_messages(search_query if search_query != user_message else user_message,
                                        history, system_prompt)
        messages = self._compress_history(history, messages)
        inputs = {"messages": messages}

        async for event in self.graph.astream_events(inputs, version="v2", config={"recursion_limit": 25}):
            event_type = event.get("event", "")
            # Stream only the final LLM text tokens (not tool call reasoning)
            if event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    # Only yield if not a tool_call chunk
                    if not (hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks):
                        yield chunk.content
