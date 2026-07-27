"""
tests/test_unit_enrichment.py
==============================
Comprehensive unit tests for rag/enrichment.py (DocumentEnricher).
Target: 85%+ coverage.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from langchain.schema import Document

import os
os.environ.setdefault("GROQ_API_KEY", "fake-groq-key")


class TestDocumentEnricher:
    """Tests for DocumentEnricher in rag/enrichment.py"""

    @patch("app.rag.enrichment.ChatGroq")
    def test_enrich_chunk_success(self, mock_groq):
        """Should enrich a document chunk with summary and keywords."""
        from app.rag.enrichment import DocumentEnricher, ChunkMetadata

        mock_llm = MagicMock()
        mock_result = ChunkMetadata(
            summary="A concise summary of the chunk.",
            keywords=["python", "programming", "language", "tutorial", "beginner"]
        )
        mock_llm.invoke.return_value = mock_result
        mock_groq.return_value.with_structured_output.return_value = mock_llm

        enricher = DocumentEnricher()
        doc = Document(
            page_content="Python is a high-level programming language. " * 10,
            metadata={"source": "python.pdf"}
        )
        result = enricher.enrich_chunk(doc)

        assert result.metadata.get("summary") == "A concise summary of the chunk."
        assert "python" in result.metadata.get("keywords", "")

    @patch("app.rag.enrichment.ChatGroq")
    def test_enrich_chunk_empty_content_skips_llm(self, mock_groq):
        """Empty content chunks should be returned without LLM call."""
        from app.rag.enrichment import DocumentEnricher

        mock_llm = MagicMock()
        mock_groq.return_value.with_structured_output.return_value = mock_llm

        enricher = DocumentEnricher()
        doc = Document(page_content="   ", metadata={"source": "empty.pdf"})
        result = enricher.enrich_chunk(doc)

        mock_llm.invoke.assert_not_called()
        assert result is doc  # Same object returned

    @patch("app.rag.enrichment.ChatGroq")
    def test_enrich_chunk_whitespace_only_skips(self, mock_groq):
        """Whitespace-only content should not trigger LLM enrichment."""
        from app.rag.enrichment import DocumentEnricher

        mock_llm = MagicMock()
        mock_groq.return_value.with_structured_output.return_value = mock_llm

        enricher = DocumentEnricher()
        doc = Document(page_content="\n\t\r\n", metadata={})
        enricher.enrich_chunk(doc)
        mock_llm.invoke.assert_not_called()

    @patch("app.rag.enrichment.ChatGroq")
    def test_enrich_chunk_llm_exception_returns_original(self, mock_groq):
        """LLM exception during enrichment should return original doc unchanged."""
        from app.rag.enrichment import DocumentEnricher

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM API error")
        mock_groq.return_value.with_structured_output.return_value = mock_llm

        enricher = DocumentEnricher()
        doc = Document(
            page_content="This is substantial content. " * 10,
            metadata={"source": "test.pdf"}
        )
        result = enricher.enrich_chunk(doc)

        # Should return the original doc (no metadata added)
        assert "summary" not in result.metadata
        assert result.page_content == doc.page_content

    @patch("app.rag.enrichment.ChatGroq")
    def test_enrich_chunk_non_chunkmetadata_result(self, mock_groq):
        """If LLM returns non-ChunkMetadata, metadata should not be set."""
        from app.rag.enrichment import DocumentEnricher

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "just a string, not ChunkMetadata"
        mock_groq.return_value.with_structured_output.return_value = mock_llm

        enricher = DocumentEnricher()
        doc = Document(page_content="Content here. " * 10, metadata={})
        result = enricher.enrich_chunk(doc)
        assert "summary" not in result.metadata

    @patch("app.rag.enrichment.ChatGroq")
    def test_enrich_documents_empty_list(self, mock_groq):
        """Empty document list should return empty list immediately."""
        from app.rag.enrichment import DocumentEnricher

        mock_groq.return_value.with_structured_output.return_value = MagicMock()
        enricher = DocumentEnricher()
        result = enricher.enrich_documents([])
        assert result == []

    @patch("app.rag.enrichment.ChatGroq")
    def test_enrich_documents_parallel_execution(self, mock_groq):
        """Multiple documents should be enriched in parallel."""
        from app.rag.enrichment import DocumentEnricher, ChunkMetadata

        mock_llm = MagicMock()
        mock_result = ChunkMetadata(
            summary="Summary.",
            keywords=["key1", "key2", "key3", "key4", "key5"]
        )
        mock_llm.invoke.return_value = mock_result
        mock_groq.return_value.with_structured_output.return_value = mock_llm

        enricher = DocumentEnricher()
        docs = [
            Document(page_content=f"Document {i} content. " * 10, metadata={"idx": i})
            for i in range(5)
        ]
        results = enricher.enrich_documents(docs, max_workers=3)
        assert len(results) == 5

    @patch("app.rag.enrichment.ChatGroq")
    def test_enrich_documents_thread_exception_uses_fallback(self, mock_groq):
        """Thread exceptions should use fallback (unenriched doc)."""
        from app.rag.enrichment import DocumentEnricher

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("Thread failure")
        mock_groq.return_value.with_structured_output.return_value = mock_llm

        enricher = DocumentEnricher()
        docs = [Document(page_content="Content " * 20, metadata={"source": "test.pdf"})]
        results = enricher.enrich_documents(docs)
        # Should still have 1 result (the original, unenriched doc)
        assert len(results) == 1

    @patch("app.rag.enrichment.ChatGroq")
    def test_enrich_chunk_truncates_content(self, mock_groq):
        """Content should be truncated to 2000 chars in the enrichment prompt."""
        from app.rag.enrichment import DocumentEnricher, ChunkMetadata

        captured_prompts = []
        mock_llm = MagicMock()
        def capture_invoke(prompt):
            captured_prompts.append(prompt)
            result = ChunkMetadata(summary="s", keywords=["k1","k2","k3","k4","k5"])
            return result
        mock_llm.invoke.side_effect = capture_invoke
        mock_groq.return_value.with_structured_output.return_value = mock_llm

        enricher = DocumentEnricher()
        # Create content longer than 2000 chars without short repeating patterns
        long_content = "".join(f"{i:04d}" for i in range(1000))
        doc = Document(page_content=long_content, metadata={})
        enricher.enrich_chunk(doc)

        assert len(captured_prompts) == 1
        # The prompt should contain at most 2000 chars of content
        # The substring from 2000 to end should NOT be in the prompt
        assert long_content[2000:2100] not in captured_prompts[0]


class TestChunkMetadataModel:
    def test_chunk_metadata_creation(self):
        from app.rag.enrichment import ChunkMetadata
        meta = ChunkMetadata(
            summary="Test summary.",
            keywords=["a", "b", "c", "d", "e"]
        )
        assert meta.summary == "Test summary."
        assert len(meta.keywords) == 5

    def test_chunk_metadata_requires_summary(self):
        from app.rag.enrichment import ChunkMetadata
        with pytest.raises(Exception):
            ChunkMetadata(keywords=["a"])  # Missing summary
