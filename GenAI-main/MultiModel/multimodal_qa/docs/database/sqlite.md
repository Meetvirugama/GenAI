# Relational Database Architecture

## Overview
NexusIQ uses a relational database (SQL) for persistent, structured data storage such as user profiles and system audit logs.

## Engine & ORM
- **Engine:** `sqlite:///./data/history.db` (for local development). The production Docker environment uses **PostgreSQL**.
- **ORM:** SQLAlchemy is used to define declarative models and manage database sessions (`app/core/database.py`).

## Schema

### 1. `User` Table (`users`)
Stores authenticated user profiles retrieved from Google OAuth.
- **id:** Primary Key (Integer, auto-incremented).
- **email:** Unique string identifier.
- **name:** The user's display name.
- **created_at:** Timestamp of first login.

### 2. `AuditLog` Table (`audit_logs`)
Provides a persistent security and compliance trail of user actions.
- **id:** Primary Key (Integer).
- **user_id:** Foreign key to `User.id` (nullable for anonymous actions).
- **action:** String representing the action (`chat`, `chat_stream`, `upload`).
- **session_id:** String mapping to the active chat session.
- **input_preview:** Truncated string of the user's message or uploaded filenames.
- **ip_address:** Captured IP address of the client.
- **status:** Result of the action (`success`, `blocked`, `error`).
- **detail:** Extended error message or security flag detail (e.g. `prompt_injection`).
- **timestamp:** DateTime of the event.

## Session Management (FastAPI)
Database sessions are injected into FastAPI route handlers using the `Depends(get_db)` dependency injection pattern defined in `app/api/dependencies.py`.
