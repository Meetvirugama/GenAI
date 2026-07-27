# Conversation Memory Architecture

We have fully migrated our Conversation Memory off persistent SQL databases (`history.db`) and into **Redis**.

## The Problem
Previously, chat history (messages, traces, feedback) was stored indefinitely in a SQLite database. This caused:
- **Disk Bloat**: Infinite persistence means disk usage continually increases.
- **Privacy Concerns**: Chat data lingered longer than necessary.
- **Latency**: Disk I/O for saving every token stream and message.

## The Redis Solution
By storing the active conversation in an in-memory Redis datastore, we achieve:
1. **Zero Disk Storage**: Conversations are strictly ephemeral.
2. **Automatic 30-Minute Expiration**: Redis natively handles TTL (Time To Live). If a user abandons a chat for 30 minutes, it is automatically wiped from memory. No cron jobs or database cleanup scripts are required.
3. **High Speed**: Writing to a Redis list is magnitudes faster than SQL row inserts, particularly under concurrent user load.

## Data Structures
- **Messages**: Stored in a Redis `List` keyed by `session:{session_id}:messages`. We use `RPUSH` to append new messages.
- **Metadata**: Stored in a Redis `String` containing a JSON blob keyed by `session:{session_id}:meta`. Contains the title, timestamp, and active status.
- **User Sessions**: A Redis `Set` keyed by `user:{user_id}:sessions` that groups all active session IDs for a specific user.

## Client Impact
The frontend API no longer needs to send the massive `history` array on every `POST /api/chat` request. The backend autonomously tracks the state using only the `session_id`.
