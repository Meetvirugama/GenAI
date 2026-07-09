# Vector Database

Because the application deals exclusively with document context rather than structured relational data, there is no SQL database (e.g., PostgreSQL, MySQL) or ORM used in this project. All persistent state is managed by a Vector Database.

## Pinecone Integration
- **Role:** The primary production database for storing vector embeddings.
- **Why Pinecone?** It provides ultra-fast, serverless semantic search with high availability, which is required for an enterprise-ready RAG application.
- **Connection:** The connection is initialized via `langchain_pinecone.PineconeVectorStore` using the `PINECONE_API_KEY` and `PINECONE_INDEX_NAME` environment variables.

## Local ChromaDB Fallback
If the application is deployed locally without a Pinecone API key, the `VectorStore` class gracefully degrades to using **ChromaDB**.
- **Role:** An in-memory, local vector store used for development, testing, or hackathon deployments where cloud infrastructure isn't available.

## Schema (Metadata)
When chunks are inserted into the database, they do not follow a traditional table schema. Instead, they are stored as dense vectors with attached JSON metadata.

The metadata schema for every chunk is:
```json
{
  "source": "filename.pdf",
  "page": 12,
  "session_id": "uuid-v4-string"
}
```

## Session Isolation & Security
Because there is no traditional Authentication/Authorization layer (users do not log in), the `session_id` metadata field serves as a pseudo-tenant ID.

When a user searches for a document (via the `search_documents` tool), a `filter={"session_id": current_session_id}` argument is passed to the retriever. This guarantees that User A can never accidentally (or maliciously) retrieve documents uploaded by User B, effectively isolating concurrent sessions on a shared deployment.
