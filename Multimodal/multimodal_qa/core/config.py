import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Centralized configuration for the Multimodal Q&A Pro application."""
    
    # API Keys
    GROQ_API_KEYS = [v for k, v in os.environ.items() if k.startswith("GROQ_API_KEY") and v]
    GROQ_API_KEY = GROQ_API_KEYS[0] if GROQ_API_KEYS else None
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:09012007@localhost:5432/MultiModal_AI")
    
    # Auth
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey_for_fastapi_sessions")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

    
    # Models
    LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    VISION_MODEL = os.getenv("VISION_MODEL", "gemini-2.5-flash")
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    
    # Pinecone
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX = os.getenv("PINECONE_INDEX")
    
    # RAG Settings
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 100
    CHROMA_PERSIST_DIR = os.path.join(os.getcwd(), "data", "chroma_db")
    
    @classmethod
    def validate(cls):
        """Validates that all required configuration variables are set."""
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable is not set. Please set it in your .env file or environment.")

# Validate configuration on import
# Config.validate() # We can defer this to app startup so it doesn't crash during imports if .env is missing.
