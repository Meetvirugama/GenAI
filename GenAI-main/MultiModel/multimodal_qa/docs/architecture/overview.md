# Architecture Overview

## High-Level Architecture

NexusIQ uses a modern full-stack architecture: a **React/Vite** frontend communicates with a **FastAPI** backend. The core intelligence is a **LangGraph ReAct Agent** that routes queries to three specialized tools.

```mermaid
flowchart TB
    subgraph Frontend["React Frontend (Port 5174)"]
        UI["Chat UI / Session Manager"]
    end

    subgraph Backend["FastAPI Backend (Port 7860)"]
        Router["API Router\n/api/chat\n/api/chat/stream\n/api/upload"]
        Auth["Auth\n/login/google\n/auth\n/api/me"]
        Agent["LangGraph ReAct Agent\n(create_react_agent)"]
        Security["Security Layer\nRate Limit · Injection Filter · Output Sanitizer"]
    end

    subgraph Tools["Agent Tools"]
        DocTool["search_documents\n(RAG + BM25 + Reranker)"]
        WebTool["search_web\n(DuckDuckGo + LRU Cache)"]
        VisionTool["describe_image\n(Gemini Vision)"]
    end

    subgraph Storage["Storage"]
        ChromaDB["ChromaDB\n(Local Vector Store)"]
        Redis["Redis\n(Memory + Celery Broker)"]
        SQLite["SQLite\n(User Profiles + Audit Log)"]
        Uploads["Local Disk\n(Uploaded Files)"]
    end

    subgraph External["External APIs"]
        Groq["Groq API\n(LLM)"]
        Gemini["Gemini API\n(Vision)"]
        DDG["DuckDuckGo"]
    end

    UI -- "JWT Bearer Token" --> Router
    UI --> Auth
    Router --> Security
    Security --> Agent
    Agent --> DocTool
    Agent --> WebTool
    Agent --> VisionTool

    DocTool --> ChromaDB
    WebTool --> DDG
    VisionTool --> Gemini
    Agent --> Groq

    Router --> Redis
    Router --> SQLite
    Router --> Uploads
```

## Request Lifecycle

### Streaming Chat (`POST /api/chat/stream`)

```mermaid
sequenceDiagram
    participant Browser
    participant FastAPI
    participant Agent as LangGraph Agent
    participant Groq
    participant Tool as Tool (Docs/Web/Vision)
    participant Redis

    Browser->>FastAPI: POST /api/chat/stream {message, session_id, image_path}
    FastAPI->>FastAPI: Security checks (rate limit, injection filter)
    FastAPI->>FastAPI: session_id_var.set() / image_path_var.set()
    FastAPI->>Redis: get_history_pairs(session_id)
    Redis-->>FastAPI: [(user, ai), ...]
    FastAPI->>Agent: astream(message, history)
    Agent->>Groq: Build prompt + stream
    Groq-->>Agent: tool_call: search_documents
    Agent->>Tool: asyncio.to_thread(tool.run, query)  ← ContextVar safe
    Tool-->>Agent: XML context block
    Agent->>Groq: Continue with context
    loop Token streaming
        Groq-->>Agent: token
        Agent-->>FastAPI: yield token
        FastAPI-->>Browser: data: {"token": "..."}
    end
    FastAPI->>Redis: save_message(user + assistant)
    FastAPI-->>Browser: data: {"done": true, "confidence": {...}}
    FastAPI-->>Browser: data: [DONE]
```

### Document Upload (`POST /api/upload`)

```mermaid
sequenceDiagram
    participant Browser
    participant FastAPI
    participant Celery
    participant Redis
    participant ChromaDB

    Browser->>FastAPI: POST /api/upload (multipart/form-data)
    FastAPI->>FastAPI: Validate extension, MIME type, size, malware scan
    FastAPI->>FastAPI: Save file to data/uploads/{user}/{session_id}/
    FastAPI->>Celery: process_document_task.delay(file_paths, session_id)
    FastAPI-->>Browser: {"status": "processing", "task_id": "..."}

    Celery->>Celery: PARSING — DocLoader → ParserFactory → chunks
    Celery->>Celery: EMBEDDING — VectorStore.add_documents(chunks, session_id)
    Celery->>ChromaDB: Store embeddings with {session_id} metadata
    Celery-->>Redis: Task result = SUCCESS / FAILURE

    Browser->>FastAPI: GET /api/tasks/{task_id}  (polling)
    FastAPI->>Redis: AsyncResult(task_id).status
    FastAPI-->>Browser: {"status": "SUCCESS", "chunks": 47}
```

## Dependency Injection

`main.py` initializes all singletons and attaches them to `app.state`. Each request accesses them via `request.app.state.*`.

```python
# main.py
vector_store      = VectorStore()          # ChromaDB / Pinecone
document_retriever = DocumentRetriever(vector_store)
search_doc_tool   = get_search_tool(document_retriever)
tools             = [search_doc_tool, search_web, describe_image]
agent             = MultimodalAgent(tools=tools)

app.state.agent        = agent
app.state.vector_store = vector_store
app.state.doc_loader   = DocumentLoader()
```

## Folder Structure

```text
multimodal_qa/
├── app/
│   ├── agent/
│   │   ├── workflow.py      # MultimodalAgent: run(), astream(), _rewrite_query(), _compress_history()
│   │   └── prompts.py       # Adaptive system prompt modules
│   ├── api/
│   │   ├── routes.py        # All /api/* endpoints
│   │   ├── auth.py          # Google OAuth + JWT endpoints
│   │   └── dependencies.py  # get_db(), get_current_user()
│   ├── core/
│   │   ├── config.py        # Centralized Config class
│   │   ├── context.py       # session_id_var, image_path_var (ContextVars)
│   │   ├── database.py      # SQLAlchemy models: User, AuditLog
│   │   ├── memory.py        # RedisMemoryManager
│   │   ├── security.py      # Rate limiter, injection filter, output sanitizer
│   │   ├── celery_app.py    # Celery application config
│   │   └── logger.py        # Structured logging
│   ├── rag/
│   │   ├── document_loader.py   # Orchestrates parsing + chunking
│   │   ├── chunker.py           # Multi-strategy chunker
│   │   ├── vector_store.py      # ChromaDB / Pinecone VectorStore
│   │   ├── document_retriever.py # Hybrid search + cross-encoder reranker
│   │   ├── tasks.py             # Celery task: process_document_task
│   │   ├── parsers/             # PDFParser, DocxParser, PptxParser, HtmlParser, MarkdownParser
│   │   └── retrieval/           # RetrieverFactory + 9 strategy classes + BGEReranker
│   ├── tools/
│   │   ├── document.py    # search_documents (sync + async coroutine)
│   │   ├── search.py      # search_web (DuckDuckGo + LRU cache)
│   │   ├── vision.py      # describe_image (Gemini Vision)
│   │   └── base.py        # @safe_call decorator
│   ├── vision/
│   │   ├── gemini_vision.py  # GeminiVision class (describe_image, adescribe_image, pdf_to_markdown)
│   │   └── utils.py          # prepare_image_for_api(), encode_image_to_base64()
│   └── main.py           # Application entrypoint
├── frontend/             # React + Vite + TypeScript UI
├── docs/                 # This documentation
├── tests/                # Pytest suite
├── Dockerfile
└── requirements.txt
```
