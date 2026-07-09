# Multimodal Q&A Pro - Backend

A powerful hybrid AI Agent backend powered by FastAPI, LangGraph, Groq, ChromaDB, and SQLite. This agent intelligently routes queries between PDF document search, live web search, and image analysis.

## Features
- **FastAPI Backend:** A robust REST API serving endpoints for chat, uploads, and authentication.
- **Google OAuth Login:** Seamless user authentication integrated with session middleware.
- **Local RAG (Retrieval-Augmented Generation):** Upload PDFs and perform semantic search using ChromaDB and HuggingFace embeddings.
- **Vision Studio:** Upload images and analyze them using Groq Vision (`llama-3.2-11b-vision-preview`).
- **Live Web Search:** Fetches real-time internet data via DuckDuckGo.
- **Agentic Routing:** LangGraph agent automatically decides which tools to use for any given query.
- **SQLite Database:** Stores user profiles and session information for a multi-user environment.

## Getting Started

### Prerequisites
1. Python 3.9+
2. Node.js (for the frontend, see `../frontend/README.md`)

### Setup Instructions
1. Navigate to the backend directory:
   ```bash
   cd multimodal_qa
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Environment Configuration:
   - Copy `.env.example` to `.env`
   - Add your `GROQ_API_KEY`
   - Set up your Google OAuth credentials (`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`)
   - Ensure a strong `SECRET_KEY` for session management

### Running the Server
Start the FastAPI server (it runs on port 7860 by default):
```bash
python main.py
```
Or directly using Uvicorn:
```bash
uvicorn main:app --host 127.0.0.1 --port 7860 --reload
```

## Architecture Overview
The backend integrates with a React/Vite frontend. The API handles:
- `/api/upload`: PDF processing and vectorization
- `/api/chat`: Multi-modal queries routed via LangGraph
- `/login/google` & `/auth`: OAuth flow
- `/api/me`: User session verification

Please see the `docs/` folder for more detailed technical architecture and setup guides.
