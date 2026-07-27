# Setup & Installation

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.9+ | Dockerfile uses `python:3.9-slim` |
| Node.js | 18+ | For the React frontend |
| Redis | Any | Required for Celery worker + conversation memory |
| Git | Any | |

### Required API Keys

| Key | Where to get it | Purpose |
|---|---|---|
| `GROQ_API_KEY_1` | [console.groq.com](https://console.groq.com) | LLM inference (required) |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) | Image vision analysis (required for image uploads) |
| `GOOGLE_CLIENT_ID` | [Google Cloud Console → OAuth 2.0](https://console.cloud.google.com) | User authentication (required for login) |
| `GOOGLE_CLIENT_SECRET` | Same as above | User authentication (required for login) |
| `PINECONE_API_KEY` | [app.pinecone.io](https://app.pinecone.io) | Cloud vector store (optional, defaults to local ChromaDB) |

---

## Local Development Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd GenAI-main/MultiModel
```

### 2. Create a Virtual Environment (Backend)

```bash
cd multimodal_qa
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` in the `MultiModel/` root directory:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# ── Required ──────────────────────────────────────────────────────────────────
GROQ_API_KEY_1=gsk_your_groq_key_here

# Required for image analysis
GEMINI_API_KEY=AIza_your_gemini_key_here

# Required for Google Login
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx

# Required for session security (generate a strong random string)
SECRET_KEY=replace_with_a_long_random_secret

# ── Frontend URL ──────────────────────────────────────────────────────────────
# Set to the URL where your frontend is running
# During local dev, Vite uses 5173 (or 5174 if 5173 is taken)
FRONTEND_URL=http://localhost:5174

# ── Optional ──────────────────────────────────────────────────────────────────
# Additional Groq keys for automatic load balancing / fallback
GROQ_API_KEY_2=gsk_your_second_key

# Override the default LLM or Vision model
LLM_MODEL=llama-3.3-70b-versatile
VISION_MODEL=gemini-2.5-flash

# Use Pinecone instead of local ChromaDB
# PINECONE_API_KEY=pcsk_your_key
# PINECONE_INDEX=your_index_name

# Redis (defaults to localhost)
REDIS_URL=redis://localhost:6379/0

# SQLite (defaults to ./data/history.db)
# DATABASE_URL=sqlite:///./data/history.db
```

> **Google OAuth setup:** In the Google Cloud Console, add `http://localhost:7860/auth` as an **Authorized redirect URI** for your OAuth 2.0 client.

### 4. Start Redis

```bash
# macOS (Homebrew)
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis
```

### 5. Start the Backend

```bash
# Terminal 1 — FastAPI server
cd multimodal_qa
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 7860

# Terminal 2 — Celery worker (processes document uploads)
cd multimodal_qa
source venv/bin/activate
celery -A app.core.celery_app worker --pool=solo --loglevel=info
```

### 6. Start the Frontend

```bash
# Terminal 3
cd frontend
npm install
npm run dev
```

The frontend will open at **http://localhost:5173** (or **5174** if that port is busy).

---

## Docker (Production)

The project includes a `docker-compose.yml` in the `MultiModel/` root directory.

```bash
cd GenAI-main/MultiModel
cp .env.example .env   # Fill in all required keys
docker compose up --build -d
```

This starts:
- FastAPI backend on port `7860`
- React frontend via Nginx on port `5173`  
- Redis on port `6379`
- PostgreSQL on port `5432`
- Qdrant vector database on port `6333`

Health check:
```bash
docker compose ps
```

---

## All Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY_1` | — | **Required.** Groq API key (supports `GROQ_API_KEY_1`, `_2`, `_3` … for load balancing) |
| `GEMINI_API_KEY` | — | Required for image uploads and vision features |
| `GOOGLE_CLIENT_ID` | — | Required for Google OAuth login |
| `GOOGLE_CLIENT_SECRET` | — | Required for Google OAuth login |
| `SECRET_KEY` | insecure default | Session middleware signing key. **Must be set in production.** |
| `JWT_SECRET_KEY` | same as `SECRET_KEY` | Signs JWT access tokens |
| `FRONTEND_URL` | `http://localhost:5173` | OAuth redirect target after successful login |
| `DATABASE_URL` | `sqlite:///./data/history.db` | SQLAlchemy DB URL. Use PostgreSQL in production. |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Primary Groq LLM model |
| `VISION_MODEL` | `gemini-2.5-flash` | Gemini vision model |
| `PINECONE_API_KEY` | — | Optional. Enables Pinecone cloud vector store |
| `PINECONE_INDEX` | — | Pinecone index name (required if using Pinecone) |

---

## Running Tests

```bash
cd multimodal_qa
source venv/bin/activate
pytest tests/ -v
```
