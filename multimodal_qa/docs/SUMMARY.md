# NexusIQ Documentation

## Summary

**NexusIQ** is a production-grade, multimodal AI agent platform. It provides a FastAPI backend that orchestrates a LangGraph ReAct agent to answer user questions by intelligently combining three data sources: uploaded local documents (RAG), live web search, and AI image analysis.

## Architecture Highlights

| Layer | Technology |
|---|---|
| **Backend Framework** | FastAPI (Python 3.9+) |
| **Frontend** | React 18 + Vite + TypeScript |
| **Agent Framework** | LangGraph `create_react_agent` (ReAct pattern) |
| **LLM** | Groq — `llama-3.3-70b-versatile` (primary), `llama-3.1-8b-instant` (fallback) |
| **Vision** | Google Gemini — `gemini-2.5-flash` via `google-generativeai` SDK |
| **Embeddings** | HuggingFace — `all-MiniLM-L6-v2` (runs locally, no API key) |
| **Vector Store** | ChromaDB (local) or Pinecone (cloud, optional) |
| **SQL Database** | SQLite (local dev) or PostgreSQL (production via Docker) |
| **Memory** | Redis — ephemeral sessions with 30-minute TTL |
| **Background Worker** | Celery + Redis broker |
| **Web Search** | DuckDuckGo with LRU query caching |

## Document Index

### Setup
- [Installation & Environment Configuration](setup/installation.md)

### Architecture
- [System Overview](architecture/overview.md)
- [Authentication & JWT Flow](architecture/authentication.md)
- [Streaming (SSE) Architecture](architecture/Streaming.md)
- [Background Worker (Celery)](architecture/BackgroundWorker.md)
- [Conversation Memory (Redis)](architecture/ConversationMemory.md)
- [Document Parser Architecture](architecture/parser.md)
- [Chunking Strategy](architecture/Chunking.md)
- [Retrieval Architecture](architecture/retrieval.md)
- [Cross-Encoder Reranking](architecture/Reranking.md)

### Services
- [LangGraph Agent](services/agent.md)
- [Tools & Integrations](services/tools.md)

### Security
- [Security & Threat Model](security/security.md)

### Components
- [Frontend UI](components/ui.md)

### Database
- [SQLite Schema](database/sqlite.md)
- [Vector Store](database/vector_store.md)

### Performance
- [Performance Notes](performance/performance.md)
