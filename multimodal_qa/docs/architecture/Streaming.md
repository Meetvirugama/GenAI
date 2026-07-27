# Streaming Architecture & Cancellation

Our application employs Server-Sent Events (SSE) to deliver a real-time typing experience to the user.

## Frontend Client
The React frontend uses the native fetch API to read the SSE stream chunk-by-chunk in `api.ts`.
We use an `AbortController` linked to the fetch request's `signal`.
When a user clicks "Stop Generating", `abortController.abort()` is called. This instantly drops the TCP connection to the backend.

## Backend Handler
The FastAPI backend serves the stream via `@chat_router.post("/chat/stream")`.
When the user triggers the AbortController, the web server (Uvicorn/Starlette) detects the disconnected socket and throws an `asyncio.CancelledError` inside the generator.
We trap this error explicitly:
```python
except asyncio.CancelledError:
    # Save whatever partial text was generated to Redis memory so it's not lost
    redis_memory.save_message(...)
    raise
```

## Reconnection
Because we aggressively save the partial response to Redis upon cancellation, if the user immediately sends a follow-up question, the conversational memory remains fully intact. The agent is aware of what it had partially generated before it was cut off.
