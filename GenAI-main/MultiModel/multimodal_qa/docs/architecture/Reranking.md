# Cross-Encoder Reranking

The RAG Retrieval pipeline now supports an optional **Cross-Encoder Reranking** step to drastically improve answer quality and Top-K accuracy.

## The Problem with Bi-Encoders (Dense Search)
Standard vector search (Dense Search) uses a Bi-Encoder. It calculates the embedding for the query and the embedding for the document entirely separately, and then calculates the cosine similarity. This is extremely fast (able to search millions of documents in milliseconds) but loses nuanced context because the query and document never "see" each other during embedding generation.

## The Cross-Encoder Solution
A Cross-Encoder passes both the Query and the Document simultaneously into the Transformer network (e.g. `[CLS] Query [SEP] Document [SEP]`). The attention mechanism can directly compare words in the query to words in the document. 
- **Pros**: Massive jump in semantic understanding, accuracy, and nuance matching.
- **Cons**: Extremely computationally expensive. You cannot pre-compute embeddings. It takes `O(N)` time where N is the number of documents.

## Our Implementation
We use a two-stage retrieval pipeline when `use_reranker=True`:
1. **Stage 1 (Bi-Encoder)**: Fast vector search retrieves the top `K=20` documents.
2. **Stage 2 (Cross-Encoder)**: We pass the query and those 20 documents through `BAAI/bge-reranker-base`. It scores them, and we return the absolute best `K=5` documents to the LLM.

This gives us the best of both worlds: the speed of Bi-Encoders with the accuracy of Cross-Encoders.

## Fallback
If the `sentence-transformers` library is missing, or the model fails to load, `BGEReranker` gracefully falls back to returning the original documents without modification.

## Benchmarking
Run `pytest tests/benchmark_reranker.py -s` to evaluate the latency tradeoff. You will typically see a ~500ms latency increase when the reranker is enabled, but Top-1 accuracy significantly improves for tricky queries.
