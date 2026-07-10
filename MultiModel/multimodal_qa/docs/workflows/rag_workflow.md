# RAG (Retrieval-Augmented Generation) Workflow

The process of taking raw PDF files and turning them into searchable embeddings is handled by the `rag/` module.

## Workflow

```mermaid
flowchart TD
    A[User Uploads PDF] --> B[FastAPI: /api/upload]
    B -->|Background Task| C[DocumentLoader.load_pdfs]
    C --> D[Gemini Vision exact markdown extraction]
    D --> E[MarkdownHeaderTextSplitter]
    E --> F[Hierarchical text chunks]
    F -->|Return chunks| B
    B -->|Background Task| G[VectorStore.add_documents]
    G --> H[HuggingFace Embeddings]
    H --> I[(Pinecone / ChromaDB)]
```

## 1. Document Parsing (`document_loader.py`)
- The `DocumentLoader` class accepts a list of file paths.
- It iterates through each path, uploading the PDF securely to Gemini's File API to perform highly accurate layout-preserving Markdown extraction.
- The raw markdown is split logically using `MarkdownHeaderTextSplitter`, ensuring that headers and tables remain structurally intact.
- **Performance:** This entire parsing pipeline runs asynchronously, ensuring the React frontend remains responsive during heavy processing.

## 2. Embedding (`vector_store.py`)
- The parsed chunks are passed to `add_documents()`.
- Metadata is attached to every chunk. Crucially, the `session_id` is appended to the metadata, ensuring users can only retrieve chunks they personally uploaded.
- The chunks are converted into vector embeddings using the `all-MiniLM-L6-v2` model.

## 3. Retrieval (`retriever.py`)
- When the `search_documents` tool is invoked, `DocumentRetriever` queries the vector database using the user's prompt.
- **Security (XML Sanitization):** Before returning the chunks to the LLM, the retriever scrubs `<` and `>` characters from the raw text, converting them to `&lt;` and `&gt;`. The scrubbed text is then wrapped in `<context>` tags. This neutralizes "Indirect Prompt Injection" attacks where a malicious user hides fake LLM instructions (e.g. `</context> Ignore previous instructions`) inside a PDF file.
