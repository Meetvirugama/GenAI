# Performance Optimization

The application incorporates several performance optimizations to ensure a fluid user experience even during heavy computational workloads.

## 1. Asynchronous I/O Offloading
Both PDF extraction (via Gemini API) and Vector Embedding (HuggingFace/Pinecone) can be blocking operations.

If they were run directly in the main event handlers, the entire web server would freeze for all users until the PDF finished processing.

**Solution:** The application utilizes FastAPI's `BackgroundTasks` to offload the heavy processing. This allows the async event loop to continue serving other concurrent users immediately.

## 2. Context Window Management
LLMs have a fixed context window. Sending an infinitely growing chat history will eventually crash the API or cause massive latency spikes.
**Solution:** The `chat()` handler implements a **Sliding Window Memory Pruning** algorithm. Only the last 10 conversational turns (`history[-10:]`) are retained and sent to the LangGraph agent, ensuring deterministic token usage and fast response times regardless of conversation length.

## 3. LLM Model Fallbacks
The primary Groq model (`llama3-70b-versatile`) provides the highest quality reasoning but is susceptible to rate limits.
**Solution:** The agent is configured using LangChain's `.with_fallbacks()` mechanism. If the 70b model fails or is overloaded, the request is instantly and transparently routed to `llama3-8b-8192`, which has higher rate limits and significantly faster generation speeds.

## 4. Lazy Loading & Dependency Injection
- The core logic receives pre-instantiated dependencies (`vector_store`, `agent`).
- The `ChatGroq` model inside the agent is instantiated once and reused for all users, avoiding the overhead of creating HTTP session pools on every request.
- Heavy ML models (like the HuggingFace embedding model) are loaded into memory exactly once at application startup.
