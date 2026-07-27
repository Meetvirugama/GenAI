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
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Allow local HTTP for OAuth
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from app.core.config import Config
from app.core.logger import get_logger
from app.core.database import init_db
from app.api.auth import auth_router
from app.api.routes import chat_router


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
from app.rag.vector_store import VectorStore
from app.rag.document_loader import DocumentLoader
from app.rag.document_retriever import DocumentRetriever
from app.tools.document import get_search_tool
from app.tools.vision import describe_image
from app.tools.search import search_web
from app.agent.workflow import MultimodalAgent

vector_store = VectorStore()
doc_loader = DocumentLoader()
document_retriever = DocumentRetriever(vector_store)
search_doc_tool = get_search_tool(document_retriever)
tools = [search_doc_tool, search_web, describe_image]
agent = MultimodalAgent(tools=tools)

# FastAPI App
app = FastAPI(title="NexusIQ")

# #1 Rate Limiter registration
from app.core.security import limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SessionMiddleware, secret_key=Config.SECRET_KEY)
origins = [o.strip() for o in Config.FRONTEND_URL.split(",")] if Config.FRONTEND_URL else []
if not origins:
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    logger.info(f"🚀 Launching FastAPI on http://0.0.0.0:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
