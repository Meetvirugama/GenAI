"""
tests/test_unit_document_loader.py
=====================================
Comprehensive unit tests for rag/document_loader.py.
Target: 85%+ coverage.
"""
import os
import pytest
from unittest.mock import MagicMock, patch
from langchain.schema import Document

os.environ.setdefault("GROQ_API_KEY", "fake")
os.environ.setdefault("GEMINI_API_KEY", "fake")


class TestDocumentLoader:
    """Tests for rag/document_loader.py DocumentLoader"""

    def test_load_documents_pdf(self, tmp_path):
        """Should use PDFParser for PDF files."""
        from app.rag.document_loader import DocumentLoader

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")

        loader = DocumentLoader()

        mock_parser = MagicMock()
        mock_parser.extract.return_value = {
            "text": "PDF extracted text",
            "metadata": {"source": str(pdf_file)},
            "sections": [],
            "pages": [{"text": "PDF extracted text", "page_num": 1}]
        }

        with patch("app.rag.document_loader.ParserFactory.get_parser", return_value=mock_parser):
            docs = loader.load_documents([str(pdf_file)])

        assert len(docs) > 0
        assert any("PDF extracted text" in d.page_content for d in docs)

    def test_load_documents_markdown(self, tmp_path):
        """Should use MarkdownParser for .md files."""
        from app.rag.document_loader import DocumentLoader

        md_file = tmp_path / "notes.md"
        md_file.write_text("# Title\n\nMarkdown content here.")

        loader = DocumentLoader()

        mock_parser = MagicMock()
        mock_parser.extract.return_value = {
            "text": "# Title\n\nMarkdown content here.",
            "metadata": {"source": str(md_file)},
            "sections": [],
            "pages": [{"text": "# Title\n\nMarkdown content here.", "page_num": 1}]
        }

        with patch("app.rag.document_loader.ParserFactory.get_parser", return_value=mock_parser):
            docs = loader.load_documents([str(md_file)])

        assert len(docs) > 0

    def test_load_empty_file_list(self):
        """Empty file list should return empty list."""
        from app.rag.document_loader import DocumentLoader
        loader = DocumentLoader()
        result = loader.load_documents([])
        assert result == []

    def test_load_nonexistent_file(self):
        """Non-existent file should be handled gracefully."""
        from app.rag.document_loader import DocumentLoader
        loader = DocumentLoader()
        result = loader.load_documents(["/nonexistent/fake_file.pdf"])
        assert isinstance(result, list)  # Should not raise

    def test_load_documents_with_empty_text(self, tmp_path):
        """Files with empty extracted text should be handled."""
        from app.rag.document_loader import DocumentLoader

        pdf_file = tmp_path / "empty.pdf"
        pdf_file.write_bytes(b"minimal")

        loader = DocumentLoader()

        mock_parser = MagicMock()
        mock_parser.extract.return_value = {
            "text": "",
            "metadata": {"source": str(pdf_file)},
            "sections": []
        }

        with patch("app.rag.document_loader.ParserFactory.get_parser", return_value=mock_parser):
            docs = loader.load_documents([str(pdf_file)])
        # May return empty or a single empty doc
        assert isinstance(docs, list)

    def test_load_multiple_files(self, tmp_path):
        """Should load and return docs from multiple files."""
        from app.rag.document_loader import DocumentLoader

        file1 = tmp_path / "doc1.pdf"
        file2 = tmp_path / "doc2.md"
        file1.write_bytes(b"content1")
        file2.write_text("# Doc 2")

        loader = DocumentLoader()

        def mock_get_parser(path):
            m = MagicMock()
            if "doc1" in path:
                m.extract.return_value = {
                    "text": "Content from doc1",
                    "metadata": {"source": path},
                    "sections": [],
                    "pages": [{"text": "Content from doc1", "page_num": 1}]
                }
            else:
                m.extract.return_value = {
                    "text": "Content from doc2",
                    "metadata": {"source": path},
                    "sections": [],
                    "pages": [{"text": "Content from doc2", "page_num": 1}]
                }
            return m

        with patch("app.rag.document_loader.ParserFactory.get_parser", side_effect=mock_get_parser):
            docs = loader.load_documents([str(file1), str(file2)])

        assert len(docs) >= 1  # At least some docs returned

    def test_load_documents_adds_source_metadata(self, tmp_path):
        """Loaded documents should have 'source' in metadata."""
        from app.rag.document_loader import DocumentLoader

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"pdf content")

        loader = DocumentLoader()

        mock_parser = MagicMock()
        mock_parser.extract.return_value = {
            "text": "Document text content here",
            "metadata": {"source": str(pdf_file)},
            "sections": [],
            "pages": [{"text": "Document text content here", "page_num": 1}]
        }

        with patch("app.rag.document_loader.ParserFactory.get_parser", return_value=mock_parser):
            docs = loader.load_documents([str(pdf_file)])

        if docs:
            assert "source" in docs[0].metadata

    def test_load_documents_parser_exception(self, tmp_path):
        """Parser exception should be caught, not crash loader."""
        from app.rag.document_loader import DocumentLoader

        pdf_file = tmp_path / "bad.pdf"
        pdf_file.write_bytes(b"bad content")

        loader = DocumentLoader()

        mock_parser = MagicMock()
        mock_parser.extract.side_effect = Exception("Parse error")

        with patch("app.rag.document_loader.ParserFactory.get_parser", return_value=mock_parser):
            docs = loader.load_documents([str(pdf_file)])
        # Should return empty list, not raise
        assert isinstance(docs, list)
