# Advanced Chunking Architecture

This document describes the multi-strategy chunking pipeline implemented in `rag/chunker.py`.

## Strategies

### 1. Heading-Based Chunking (First Pass)
Documents containing Markdown headers (`#`, `##`, `###`) are initially split semantically by section. The section header is stored in the chunk's metadata (e.g., `{"Header 1": "Introduction"}`). This ensures chunks do not bleed across completely different conceptual topics.

### 2. Parent-Child Chunking (Hierarchical)
Small text chunks (e.g., 500 characters) are ideal for precision during vector search. However, LLMs perform better when provided with broader surrounding context. 
- **Implementation**: The pipeline creates large "Parent" chunks (e.g., 2000 chars), then splits them into smaller "Child" chunks (500 chars).
- **Storage**: The `parent_id` and full `parent_text` are injected directly into the Child's metadata. 
- **Retrieval**: The vector search retrieves the precise Child chunk. The LLM prompt can then extract `metadata["parent_text"]` to read the full context.

### 3. Recursive Chunking (Fallback / Default)
When Semantic Chunking is disabled, `RecursiveCharacterTextSplitter` acts on the section fragments. It attempts to split on logical breakpoints (paragraphs `\n\n`, then sentences `\n`, then words) up to the specified `chunk_size`.
- Overlap ensures sentences bisected at the boundary are not lost.

### 4. Semantic Chunking (Optional)
Uses `langchain_experimental.text_splitter.SemanticChunker` coupled with the configured `HuggingFaceEmbeddings` model. It breaks text into sentences, calculates semantic similarity between sequential sentences, and groups them until the similarity drops below a percentile threshold.
- **Pros**: Highly coherent chunks.
- **Cons**: Requires embedding generation during ingestion, significantly slowing down upload times. (Benchmark shows ~10-20x slower than Recursive).

## Metadata Schema
Every chunk produced by the pipeline guarantees:
- `source`: The original file path.
- `page_number`: The specific page or slide index (extracted by the new paginated parsers).
- `Header X`: The active markdown heading.
- `parent_id`: MD5 hash of the parent chunk.
- `parent_text`: The broader context window.
