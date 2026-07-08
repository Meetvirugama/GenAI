# Database Architecture

## Overview
The application utilizes two completely distinct databases to serve different purposes within the system:
1. **SQLite:** A relational database used for structured data (Users, Profiles, and future Chat History mapping).
2. **ChromaDB:** A vector database used strictly for embedding and retrieving semantic documents (PDF RAG).

---

## 1. Relational Database (SQLite)

### Engine & ORM
- **Engine:** `sqlite:///history.db`
- **ORM:** SQLAlchemy is used to define declarative models and manage database sessions.

### Schema
Currently, the SQLite database implements a `User` table:
- **id:** Primary Key (Integer, auto-incremented).
- **email:** Unique string identifier retrieved from Google OAuth.
- **name:** The user's display name.

*Future Expansion:* The relational database is perfectly positioned to store conversation histories (`Thread` and `Message` tables), mapping them to a `user_id` to provide persistent, multi-device chat histories.

### Session Management (Backend)
Database sessions are injected into FastAPI route handlers using the `Depends(get_db)` dependency injection pattern defined in `core/db.py`.

---

## 2. Vector Database (ChromaDB)

### Purpose
ChromaDB handles the unstructured data. When a user uploads a PDF, the document is chunked, embedded via HuggingFace `all-MiniLM-L6-v2`, and stored here.

### Session Isolation
To ensure users do not search across other users' or other sessions' documents, ChromaDB documents are tagged with metadata during insertion:
`metadata={"session_id": session_id}`

During retrieval, the query is aggressively filtered by this `session_id`, ensuring strict tenant isolation per conversation thread.
