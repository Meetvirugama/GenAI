# NexusIQ — Backend

A production-grade Multimodal AI Agent backend powered by **FastAPI**, **LangGraph**, **Groq** (LLM), **Gemini** (Vision), **ChromaDB**, **Redis**, and **SQLite**. The agent intelligently routes queries between uploaded document search (RAG), live web search, and AI image analysis.

## Features

| Feature | Implementation |
|---|---|
| **LangGraph ReAct Agent** | Autonomous tool routing via `create_react_agent` |
| **Hybrid RAG** | BM25 + Dense vector search with cross-encoder re-ranking |
| **SSE Streaming** | Token-by-token streaming via `POST /api/chat/stream` |
| **Celery Background Worker** | Non-blocking document indexing via Redis broker |
| **Google OAuth + JWT** | Stateless `Authorization: Bearer <token>` auth |
| **Redis Conversation Memory** | 30-minute TTL ephemeral sessions |
| **Gemini Vision** | Image analysis via `google-generativeai` SDK |
| **Web Search** | Live DuckDuckGo search with LRU caching |
| **SQLite Audit Log** | Persistent security & compliance trail |
| **Rate Limiting** | SlowAPI — 30/min (chat), 10/hr (upload) |

## Quick Start (Local Development)

### Prerequisites
- Python 3.9+
- Redis running on `localhost:6379`
- Node.js v18+ (for the frontend)
- API Keys: `GROQ_API_KEY_1`, `GEMINI_API_KEY`

### 1. Install Dependencies

```bash
cd multimodal_qa
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy from the root MultiModel directory
cp ../.env.example ../.env
```

Edit `../.env` with your keys. Minimum required:

```env
GROQ_API_KEY_1=gsk_...
GEMINI_API_KEY=AIza...
SECRET_KEY=a_long_random_string_here
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
FRONTEND_URL=http://localhost:5174
```

### 3. Start the Backend

```bash
# Terminal 1 — FastAPI
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 7860

# Terminal 2 — Celery Worker (document indexing)
source venv/bin/activate
celery -A app.core.celery_app worker --pool=solo --loglevel=info
```

### 4. Start the Frontend

```bash
cd ../frontend
npm install
npm run dev
# Opens on http://localhost:5173 (or 5174 if that port is in use)
```

## Docker (Production)

```bash
cd GenAI-main/MultiModel
cp .env.example .env   # Fill in your keys
docker compose up --build -d
```

Services launched:
- **FastAPI Backend** → `http://localhost:7860`
- **Celery Worker** (document indexing)
- **Redis** (broker + memory)
- **PostgreSQL** (user profiles + audit logs)
- **Qdrant** (production vector store)

## API Endpoints Summary

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat` | Synchronous chat (returns full answer + trace) |
| `POST` | `/api/chat/stream` | Streaming SSE chat (token-by-token) |
| `POST` | `/api/upload` | Upload documents/images for indexing |
| `GET` | `/api/tasks/{id}` | Poll Celery indexing task status |
| `GET` | `/api/sessions` | List user's chat sessions |
| `GET` | `/api/sessions/{id}/messages` | Get messages in a session |
| `DELETE` | `/api/sessions/{id}` | Delete session (Redis + uploads + vector store) |
| `POST` | `/api/messages/{id}/feedback` | Submit thumbs up/down feedback |
| `GET` | `/api/search` | Full-text search across user messages |
| `GET` | `/login/google` | Initiate Google OAuth flow |
| `GET` | `/auth` | Google OAuth callback |
| `GET` | `/api/me` | Get current authenticated user |

**Interactive API docs:** `http://localhost:7860/docs`

## Folder Structure

```
multimodal_qa/
├── app/
│   ├── agent/        # LangGraph agent: workflow.py, prompts.py
│   ├── api/          # FastAPI routers: routes.py, auth.py, dependencies.py
│   ├── core/         # Config, Logger, ContextVars, Database, Security, Memory
│   ├── rag/          # Document loader, chunker, vector store, retrieval, Celery tasks
│   ├── tools/        # LangChain tools: document.py, search.py, vision.py
│   └── vision/       # Gemini Vision integration (gemini_vision.py)
├── docs/             # Full technical documentation
├── tests/            # Pytest suite
├── Dockerfile
└── requirements.txt
```

## Testing

```bash
pytest tests/ -v
```

See the [`docs/`](docs/README.md) directory for full technical documentation.
