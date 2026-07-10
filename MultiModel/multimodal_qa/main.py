"""
NexusIQ — Application Entrypoint

Run with:
    python main.py
"""
import sys
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

# Ensure project root is on the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Allow local HTTP for OAuth
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from core.config import Config
from core.logger import get_logger
from core.db import init_db
from api.auth import auth_router
from api.routes import chat_router


logger = get_logger("main")

# Initialize DB
init_db()

# Validate API key before loading models
try:
    Config.validate()
    logger.info("✅ Configuration validated.")
except ValueError as e:
    logger.error(str(e))
    sys.exit(1)

# Initialize App Dependencies
from rag.vector_store import VectorStore
from rag.document_loader import DocumentLoader
from rag.retriever import DocumentRetriever
from tools.document import get_search_tool
from tools.vision import describe_image
from tools.search import search_web
from agent.graph import MultimodalAgent

vector_store = VectorStore()
doc_loader = DocumentLoader()
document_retriever = DocumentRetriever(vector_store)
search_doc_tool = get_search_tool(document_retriever)
tools = [search_doc_tool, search_web, describe_image]
agent = MultimodalAgent(tools=tools)

# FastAPI App
app = FastAPI(title="NexusIQ")

# #1 Rate Limiter registration
from core.security import limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SessionMiddleware, secret_key=Config.SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.agent = agent
app.state.doc_loader = doc_loader
app.state.vector_store = vector_store

# Include API Routers
app.include_router(auth_router)
app.include_router(chat_router)

if __name__ == "__main__":
    port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
    logger.info(f"🚀 Launching FastAPI on http://127.0.0.1:{port}")
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
