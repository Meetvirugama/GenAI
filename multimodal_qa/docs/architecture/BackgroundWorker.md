# Background Worker Architecture

We have migrated synchronous document ingestion into a **Celery Background Worker** pipeline.

## Motivation
Previously, when a user uploaded a massive 500-page PDF, the `/api/upload` endpoint would block while the application parsed, chunked, and embedded the text. This led to:
- HTTP timeout errors (FastAPI closing connection).
- Blocked web server threads, slowing down the application for other users.
- Loss of state if a crash occurred midway through embedding.

## Architecture
We now use **Celery** connected to **Redis** (which acts as both the Message Broker and Result Backend).

1. **Client Upload**: The user uploads a file to `/api/upload`.
2. **Task Dispatch**: The server immediately saves the file to disk and dispatches `process_document_task.delay(files, session_id)`.
3. **Immediate Return**: The server returns a `200 OK` with a `task_id` in less than 50ms.
4. **Worker Processing**: The Celery worker picks up the job. It updates its state as it progresses through `PARSING` and `EMBEDDING` phases.
5. **Polling**: The client polls `/api/tasks/{task_id}` to retrieve real-time progress updates from Redis.

## Fault Tolerance
The `process_document_task` is decorated with `@shared_task(bind=True, max_retries=3)`. If the HuggingFace embedding model crashes, or the Vector Database is momentarily unreachable, the Celery worker will automatically catch the exception and safely retry the task up to 3 times with a 30-second backoff.

## Scaling
To process more documents concurrently, simply scale the `celery_worker` service in `docker-compose.yml`:
```bash
docker-compose up --scale celery_worker=3 -d
```
