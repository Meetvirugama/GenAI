# LangGraph Agent

## Overview
The core intelligence of the application resides in `agent/graph.py`. It utilizes **LangGraph**, a library for building stateful, multi-actor applications with LLMs.

## The ReAct Architecture
The `MultimodalAgent` implements a **Reasoning + Acting (ReAct)** pattern. Instead of a simple Q&A pipeline, the agent:
1. Evaluates the user's question.
2. Formulates a plan (Reasoning).
3. Calls the appropriate tool (Acting).
4. Observes the result.
5. Synthesizes a final answer.

## LLM Configuration
The agent is powered by Groq's high-speed inference engine.
- **Primary Model:** `llama3-70b-8192` (Configurable via `LLM_MODEL`)
- **Fallback Model:** `llama3-8b-8192` 

**Resilience (SRE Fix):** The agent uses LangChain's `.with_fallbacks()` method. If the primary 70b model hits a rate limit or fails, it seamlessly retries the request against the smaller, faster 8b model.

Furthermore, the `agent.run()` method is wrapped in a `tenacity` `@retry` decorator, which applies an **Exponential Backoff** (min: 2s, max: 10s, up to 3 attempts) for any unhandled exceptions during execution.

## System Prompt
The agent's behavior is strictly governed by the `SYSTEM_PROMPT`. 
Key directives include:
- **Decision Guidelines:** Explicit rules on when to use `describe_image` vs `search_documents` vs `search_web`.
- **Conflict Resolution:** If the internet and local documents contradict each other, the agent is instructed to treat the local documents as the "PRIMARY SOURCE OF TRUTH."
- **Prompt Injection Defense:** A critical directive telling the LLM to ignore all instructions found within `<context>` and `<chunk>` tags, preventing malicious PDFs from hijacking the agent.

## Execution Flow (`run` method)
1. **Input Formatting:** The user's message and pruned chat history are formatted into LangChain Message objects.
2. **Streaming Loop:** `self.graph.stream()` is called. The agent loops up to 5 times (`recursion_limit: 5`) to prevent infinite tool loops.
3. **Trace Generation:** As the agent streams `AIMessage` (tool calls) and `ToolMessage` (observations) events, they are captured, formatted using Markdown, and appended to a `trace_lines` array.
4. **Final Return:** The method returns both the synthesized `final_answer` and the raw `reasoning_trace` for UI rendering.
