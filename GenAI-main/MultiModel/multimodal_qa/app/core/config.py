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
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/history.db")
    
    # Auth
    SECRET_KEY = os.getenv("SECRET_KEY") or "change-me-in-production-secret-key"
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or SECRET_KEY
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_MINUTES = 60 * 24 * 7 # 7 days
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

    
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
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    @classmethod
    def validate(cls):
        """Validates that all required configuration variables are set."""
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable is not set. Please set it in your .env file or environment.")
        if cls.SECRET_KEY == "change-me-in-production-secret-key":
            import logging
            logging.getLogger(__name__).warning(
                "SECRET_KEY is not set in environment. Using insecure default. "
                "Set SECRET_KEY in your .env file before deploying to production."
            )

# Validate configuration on import
# Config.validate() # We can defer this to app startup so it doesn't crash during imports if .env is missing.
