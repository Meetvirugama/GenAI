import time

import pytest
from app.services.rag.chunker import AdvancedChunker
from langchain.schema import Document


def test_recursive_chunk_overlap():
    chunker = AdvancedChunker(chunk_size=100, chunk_overlap=20, parent_chunk_size=300)
    text = "A" * 150
    doc = Document(page_content=text, metadata={"source": "test.txt", "page_number": 1})
    
    # Disable parent-child and semantic to isolate recursive
    chunks = chunker.chunk_documents([doc], use_semantic=False, use_parent_child=False)
    
    assert len(chunks) == 2
    assert len(chunks[0].page_content) == 100
    assert len(chunks[1].page_content) == 70  # 150 - 100 + 20 (overlap)
    
def test_parent_child_lookup():
    chunker = AdvancedChunker(chunk_size=50, chunk_overlap=10, parent_chunk_size=200)
    text = "This is a long sentence that should ideally be split into multiple children but kept within one parent chunk to ensure we don't lose the surrounding context."
    doc = Document(page_content=text, metadata={"source": "test.txt"})
    
    chunks = chunker.chunk_documents([doc], use_semantic=False, use_parent_child=True)
    
    assert len(chunks) > 1
    # Check parent ID and text exist in child metadata
    for c in chunks:
        assert "parent_id" in c.metadata
        assert "parent_text" in c.metadata
        assert c.page_content in c.metadata["parent_text"]

def test_metadata_retention():
    chunker = AdvancedChunker(chunk_size=50, chunk_overlap=10)
    text = "# Section 1\nSome text inside section 1."
    doc = Document(page_content=text, metadata={"page_number": 5})
    
    chunks = chunker.chunk_documents([doc], use_semantic=False, use_parent_child=False)
    
    assert len(chunks) == 1
    assert chunks[0].metadata["page_number"] == 5
    assert "Header 1" in chunks[0].metadata  # From MarkdownHeaderTextSplitter

@pytest.mark.skip(reason="Performance test, skip in normal suite")
def test_performance_benchmark():
    """Benchmark recursive vs semantic chunking."""
    chunker = AdvancedChunker(chunk_size=500, chunk_overlap=100)
    text = "This is a dummy sentence to benchmark performance. " * 1000
    doc = Document(page_content=text, metadata={})
    
    # Recursive
    t0 = time.time()
    chunker.chunk_documents([doc], use_semantic=False, use_parent_child=False)
    t_recursive = time.time() - t0
    
    # Semantic
    t0 = time.time()
    chunker.chunk_documents([doc], use_semantic=True, use_parent_child=False)
    t_semantic = time.time() - t0
    
    print(f"Recursive Time: {t_recursive:.4f}s")
    print(f"Semantic Time: {t_semantic:.4f}s")
    assert t_semantic > t_recursive
