"""
tests/test_unit_agent.py
=========================
Comprehensive unit tests for agent/graph.py.
Target: 80%+ coverage of MultimodalAgent.
"""
import os
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

os.environ.setdefault("GROQ_API_KEY", "fake-groq-key")
os.environ.setdefault("GEMINI_API_KEY", "fake-gemini-key")


# ── MultimodalAgent ────────────────────────────────────────────────────────────

@pytest.fixture
def agent_with_mock_llm():
    """Create an agent with a mocked LLM to avoid real API calls."""
    with patch("app.services.agent.workflow.ChatGroq") as mock_groq_class:
        mock_llm = MagicMock()
        mock_llm.with_fallbacks.return_value = mock_llm
        mock_groq_class.return_value = mock_llm

        with patch("app.services.agent.workflow.create_react_agent") as mock_react:
            mock_graph = MagicMock()
            mock_react.return_value = mock_graph

            from app.services.agent.workflow import MultimodalAgent
            agent = MultimodalAgent([])
            agent.llm = mock_llm
            agent.workflow = mock_graph
            yield agent, mock_llm, mock_graph


# ── _build_system_prompt ───────────────────────────────────────────────────────

class TestBuildSystemPrompt:
    def test_with_image_includes_image_prompts(self, agent_with_mock_llm):
        agent, _, _ = agent_with_mock_llm
        prompt = agent._build_system_prompt("Analyze this chart", has_image=True)
        from app.services.agent.prompts import CHART_TABLE_PROMPT, IMAGE_ANALYSIS_PROMPT
        assert IMAGE_ANALYSIS_PROMPT in prompt
        assert CHART_TABLE_PROMPT in prompt

    def test_without_image_excludes_image_prompts(self, agent_with_mock_llm):
        agent, _, _ = agent_with_mock_llm
        prompt = agent._build_system_prompt("Hello", has_image=False)
        from app.services.agent.prompts import IMAGE_ANALYSIS_PROMPT
        assert IMAGE_ANALYSIS_PROMPT not in prompt

    def test_research_keywords_trigger_research_prompt(self, agent_with_mock_llm):
        agent, _, _ = agent_with_mock_llm
        prompt = agent._build_system_prompt("Compare vs alternative approaches", has_image=False)
        from app.services.agent.prompts import RESEARCH_PROMPT
        assert RESEARCH_PROMPT in prompt

    def test_code_keywords_trigger_code_prompt(self, agent_with_mock_llm):
        agent, _, _ = agent_with_mock_llm
        prompt = agent._build_system_prompt("Write a Python function to sort", has_image=False)
        from app.services.agent.prompts import CODE_ANALYSIS_PROMPT
        assert CODE_ANALYSIS_PROMPT in prompt

    def test_document_keywords_trigger_doc_prompt(self, agent_with_mock_llm):
        agent, _, _ = agent_with_mock_llm
        prompt = agent._build_system_prompt("Summarize this PDF document", has_image=False)
        from app.services.agent.prompts import DOCUMENT_ANALYSIS_PROMPT
        assert DOCUMENT_ANALYSIS_PROMPT in prompt

    def test_always_includes_base_prompt(self, agent_with_mock_llm):
        agent, _, _ = agent_with_mock_llm
        prompt = agent._build_system_prompt("Hello", has_image=False)
        from app.services.agent.prompts import BASE_SYSTEM_PROMPT
        assert BASE_SYSTEM_PROMPT in prompt

    def test_always_includes_qa_formatting(self, agent_with_mock_llm):
        agent, _, _ = agent_with_mock_llm
        prompt = agent._build_system_prompt("Hello", has_image=False)
        from app.services.agent.prompts import QA_FORMATTING_PROMPT
        assert QA_FORMATTING_PROMPT in prompt


# ── _self_reflect ──────────────────────────────────────────────────────────────

class TestSelfReflect:
    def test_short_answer_skips_reflection(self, agent_with_mock_llm):
        agent, mock_llm, _ = agent_with_mock_llm
        short_answer = "Yes."
        result = agent._self_reflect("Question?", short_answer)
        assert result == short_answer
        mock_llm.invoke.assert_not_called()

    def test_pass_verdict_returns_original(self, agent_with_mock_llm):
        agent, mock_llm, _ = agent_with_mock_llm
        mock_llm.invoke.return_value.content = "PASS"
        long_answer = "This is a detailed answer with more than 30 characters for testing."
        result = agent._self_reflect("Q", long_answer)
        assert result == long_answer

    def test_revise_verdict_appends_note(self, agent_with_mock_llm):
        agent, mock_llm, _ = agent_with_mock_llm
        mock_llm.invoke.return_value.content = "REVISE: The answer is incomplete."
        long_answer = "This is a somewhat incomplete answer with more than 30 chars."
        result = agent._self_reflect("Q", long_answer)
        assert "Auto-review note" in result
        assert long_answer in result

    def test_llm_exception_returns_original(self, agent_with_mock_llm):
        agent, mock_llm, _ = agent_with_mock_llm
        mock_llm.invoke.side_effect = Exception("LLM unavailable")
        long_answer = "This is a long enough answer that should trigger reflection attempt."
        result = agent._self_reflect("Q", long_answer)
        assert result == long_answer


# ── _rewrite_query ─────────────────────────────────────────────────────────────

class TestRewriteQuery:
    def test_no_history_returns_original(self, agent_with_mock_llm):
        agent, _, _ = agent_with_mock_llm
        result = agent._rewrite_query("What is Python?", [])
        assert result == "What is Python?"

    def test_long_specific_query_no_rewrite(self, agent_with_mock_llm):
        agent, _, _ = agent_with_mock_llm
        long_query = "What are the main advantages of using machine learning for NLP tasks?"
        result = agent._rewrite_query(long_query, [("prev Q", "prev A")])
        assert result == long_query

    def test_contextual_query_rewrites(self, agent_with_mock_llm):
        agent, mock_llm, _ = agent_with_mock_llm
        mock_llm.invoke.return_value.content = "What is the second problem in the document?"
        result = agent._rewrite_query("What about that second one?", [("Tell me problems", "There are 3 problems")])
        assert result == "What is the second problem in the document?"

    def test_llm_exception_returns_original(self, agent_with_mock_llm):
        agent, mock_llm, _ = agent_with_mock_llm
        mock_llm.invoke.side_effect = Exception("API error")
        original = "What about that?"
        result = agent._rewrite_query(original, [("prior Q", "prior A")])
        assert result == original

    def test_starts_with_it_triggers_rewrite(self, agent_with_mock_llm):
        agent, mock_llm, _ = agent_with_mock_llm
        mock_llm.invoke.return_value.content = "What is the capital of France?"
        result = agent._rewrite_query("It is great, right?", [("Q", "A")])
        assert result is not None


# ── _build_messages ────────────────────────────────────────────────────────────

class TestBuildMessages:
    def test_no_history(self, agent_with_mock_llm):
        agent, _, _ = agent_with_mock_llm
        messages = agent._build_messages("Hello", [], "System prompt here")
        assert len(messages) == 2  # SystemMessage + HumanMessage
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[1], HumanMessage)

    def test_with_history(self, agent_with_mock_llm):
        agent, _, _ = agent_with_mock_llm
        history = [("user q", "ai answer"), ("user q2", "ai answer2")]
        messages = agent._build_messages("New question", history, "Sys")
        # SystemMessage + 2 pairs (4 msgs) + current HumanMessage
        assert len(messages) == 6

    def test_system_message_content(self, agent_with_mock_llm):
        agent, _, _ = agent_with_mock_llm
        messages = agent._build_messages("Q", [], "My system prompt")
        assert messages[0].content == "My system prompt"

    def test_last_message_is_current_query(self, agent_with_mock_llm):
        agent, _, _ = agent_with_mock_llm
        messages = agent._build_messages("Current question", [], "Sys")
        assert messages[-1].content == "Current question"


# ── _compress_history ──────────────────────────────────────────────────────────

class TestCompressHistory:
    def test_short_history_unchanged(self, agent_with_mock_llm):
        agent, _, _ = agent_with_mock_llm
        history_pairs = [("u", "a")] * 5  # Under threshold of 10
        messages = [SystemMessage(content="sys"), HumanMessage(content="q")]
        result = agent._compress_history(history_pairs, messages)
        assert result == messages  # Unchanged

    def test_long_history_compressed(self, agent_with_mock_llm):
        agent, mock_llm, _ = agent_with_mock_llm
        mock_llm.invoke.return_value.content = "Summary of conversation."
        history_pairs = [("user_q", "ai_a")] * 15  # Over threshold
        messages = [SystemMessage(content="sys"), HumanMessage(content="current")]
        result = agent._compress_history(history_pairs, messages)
        # Should have SystemMessage + summary + recent pairs + current
        assert len(result) > 0

    def test_summarization_exception_returns_original(self, agent_with_mock_llm):
        agent, mock_llm, _ = agent_with_mock_llm
        mock_llm.invoke.side_effect = Exception("LLM error")
        history_pairs = [("u", "a")] * 15
        messages = [SystemMessage(content="sys"), HumanMessage(content="q")]
        result = agent._compress_history(history_pairs, messages)
        assert result == messages  # Fallback to original


# ── run() method ───────────────────────────────────────────────────────────────

class TestAgentRun:
    def test_run_returns_tuple(self, agent_with_mock_llm):
        agent, mock_llm, mock_graph = agent_with_mock_llm

        mock_ai_msg = MagicMock()
        mock_ai_msg.content = "Final answer here."
        mock_ai_msg.tool_calls = []
        type(mock_ai_msg).__name__ = "AIMessage"

        mock_graph.stream.return_value = [
            {"messages": [mock_ai_msg]}
        ]
        mock_llm.invoke.return_value.content = "PASS"

        with patch("app.core.context.image_path_var") as mock_var:
            mock_var.get.return_value = None
            result = agent.run("What is Python?")

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_run_with_tool_calls_builds_trace(self, agent_with_mock_llm):
        agent, mock_llm, mock_graph = agent_with_mock_llm

        mock_tool_msg = MagicMock()
        mock_tool_msg.content = "Tool result content"
        mock_tool_msg.name = "search_documents"
        type(mock_tool_msg).__name__ = "ToolMessage"

        mock_ai_with_tools = MagicMock()
        mock_ai_with_tools.tool_calls = [{"name": "search_documents", "args": {"query": "q"}}]
        type(mock_ai_with_tools).__name__ = "AIMessage"

        mock_final_ai = MagicMock()
        mock_final_ai.content = "Final answer"
        mock_final_ai.tool_calls = []
        type(mock_final_ai).__name__ = "AIMessage"

        mock_graph.stream.return_value = [
            {"messages": [mock_ai_with_tools]},
            {"messages": [mock_tool_msg]},
            {"messages": [mock_final_ai]},
        ]
        mock_llm.invoke.return_value.content = "PASS"

        with patch("app.core.context.image_path_var") as mock_var:
            mock_var.get.return_value = None
            answer, trace = agent.run("Search this document")

        assert "search_documents" in trace


# ── astream() method ───────────────────────────────────────────────────────────

class TestAgentAStream:
    @pytest.mark.asyncio
    async def test_astream_yields_tokens(self, agent_with_mock_llm):
        agent, mock_llm, mock_graph = agent_with_mock_llm

        mock_chunk = MagicMock()
        mock_chunk.content = "Hello"
        mock_chunk.tool_call_chunks = []

        async def fake_astream_events(inputs, version, config):
            yield {"event": "on_chat_model_stream", "data": {"chunk": mock_chunk}}
            yield {"event": "on_other_event", "data": {}}

        mock_graph.astream_events = fake_astream_events

        with patch("app.core.context.image_path_var") as mock_var:
            mock_var.get.return_value = None
            mock_llm.invoke.return_value.content = "rewritten query"
            tokens = []
            async for token in agent.astream("Hello"):
                tokens.append(token)

        assert "Hello" in tokens

    @pytest.mark.asyncio
    async def test_astream_skips_tool_call_chunks(self, agent_with_mock_llm):
        agent, mock_llm, mock_graph = agent_with_mock_llm

        mock_chunk_tool = MagicMock()
        mock_chunk_tool.content = "tool content"
        mock_chunk_tool.tool_call_chunks = [{"id": "tc1"}]

        mock_chunk_text = MagicMock()
        mock_chunk_text.content = "text content"
        mock_chunk_text.tool_call_chunks = []

        async def fake_astream_events(inputs, version, config):
            yield {"event": "on_chat_model_stream", "data": {"chunk": mock_chunk_tool}}
            yield {"event": "on_chat_model_stream", "data": {"chunk": mock_chunk_text}}

        mock_graph.astream_events = fake_astream_events

        with patch("app.core.context.image_path_var") as mock_var:
            mock_var.get.return_value = None
            mock_llm.invoke.return_value.content = "rewritten"
            tokens = []
            async for token in agent.astream("Hello"):
                tokens.append(token)

        assert "tool content" not in tokens
        assert "text content" in tokens
