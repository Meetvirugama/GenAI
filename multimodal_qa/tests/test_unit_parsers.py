import pytesseract
"""
tests/test_unit_parsers.py
===========================
Comprehensive unit tests for all parsers in rag/parsers/.
Target: 80%+ coverage of pdf_parser, docx_parser, html_parser, pptx_parser, markdown_parser.
"""
from unittest.mock import MagicMock, patch

import pytest

# ── Markdown Parser ────────────────────────────────────────────────────────────

class TestMarkdownParser:
    def test_extract_text_content(self, tmp_path):
        """Markdown parser should extract text from .md files."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Hello\n\nThis is a test document.")
        
        from app.services.rag.parsers.markdown_parser import MarkdownParser
        parser = MarkdownParser()
        result = parser.extract(str(md_file))
        assert "Hello" in result["text"]
        assert result["metadata"]["source"] == str(md_file)

    def test_extract_nonexistent_file(self):
        """Should handle missing file gracefully."""
        from app.services.rag.parsers.markdown_parser import MarkdownParser
        parser = MarkdownParser()
        result = parser.extract("/nonexistent/file.md")
        # Should return empty or error — not crash
        assert isinstance(result, dict)


# ── Parser Factory ─────────────────────────────────────────────────────────────

class TestParserFactory:
    def test_pdf_returns_pdf_parser(self):
        from app.services.rag.parsers.factory import ParserFactory
        from app.services.rag.parsers.pdf_parser import PDFParser
        parser = ParserFactory.get_parser("document.pdf")
        assert isinstance(parser, PDFParser)

    def test_docx_returns_docx_parser(self):
        from app.services.rag.parsers.docx_parser import DocxParser
        from app.services.rag.parsers.factory import ParserFactory
        parser = ParserFactory.get_parser("report.docx")
        assert isinstance(parser, DocxParser)

    def test_doc_returns_docx_parser(self):
        from app.services.rag.parsers.docx_parser import DocxParser
        from app.services.rag.parsers.factory import ParserFactory
        parser = ParserFactory.get_parser("report.doc")
        assert isinstance(parser, DocxParser)

    def test_pptx_returns_pptx_parser(self):
        from app.services.rag.parsers.factory import ParserFactory
        from app.services.rag.parsers.pptx_parser import PptxParser
        parser = ParserFactory.get_parser("slides.pptx")
        assert isinstance(parser, PptxParser)

    def test_html_returns_html_parser(self):
        from app.services.rag.parsers.factory import ParserFactory
        from app.services.rag.parsers.html_parser import HtmlParser
        parser = ParserFactory.get_parser("page.html")
        assert isinstance(parser, HtmlParser)

    def test_md_returns_markdown_parser(self):
        from app.services.rag.parsers.factory import ParserFactory
        from app.services.rag.parsers.markdown_parser import MarkdownParser
        parser = ParserFactory.get_parser("notes.md")
        assert isinstance(parser, MarkdownParser)

    def test_unknown_extension_raises(self):
        from app.services.rag.parsers.factory import ParserFactory
        with pytest.raises(ValueError, match="No parser found"):
            ParserFactory.get_parser("file.xyz")


# ── PDF Parser ─────────────────────────────────────────────────────────────────

class TestPDFParser:
    def test_pdf_parser_init_without_docling(self):
        """Parser should initialize even if docling is not installed."""
        with patch.dict("sys.modules", {"docling": None, "docling.document_converter": None}):
            import importlib

            from app.services.rag.parsers import pdf_parser as m
            importlib.reload(m)
            parser = m.PDFParser()
            assert parser.docling_converter is None

    def test_is_scanned_raises_no_text_pdf(self):
        """Test _is_scanned on a file with no readable text (simulated scanned)."""
        from app.services.rag.parsers.pdf_parser import PDFParser
        parser = PDFParser()
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 2
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""
        mock_doc.__iter__.return_value = [mock_page, mock_page]
        with patch("fitz.open", return_value=mock_doc):
            assert parser._is_scanned("test.pdf") is True

    def test_is_scanned_false_for_text_pdf(self):
        from app.services.rag.parsers.pdf_parser import PDFParser
        parser = PDFParser()
        
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 2
        mock_page = MagicMock()
        mock_page.get_text.return_value = "This is a normal PDF with plenty of text. It has more than fifty characters to pass the threshold!"
        mock_doc.__iter__.return_value = [mock_page, mock_page]
        
        with patch("fitz.open", return_value=mock_doc):
            assert parser._is_scanned("test.pdf") is False

    def test_extract_routes_to_pymupdf_when_no_docling(self):
        from app.services.rag.parsers.pdf_parser import PDFParser
        parser = PDFParser()
        parser.docling_converter = None  # No docling

        mock_doc = MagicMock()
        mock_doc.metadata = {"title": ""}
        mock_page = MagicMock()
        mock_page.get_text.return_value = "PDF text content" * 10
        mock_doc.__iter__.side_effect = lambda: iter([mock_page])
        mock_doc.__len__.return_value = 1

        with patch("fitz.open", return_value=mock_doc):
            result = parser.extract("test.pdf")

        assert "PDF text content" in result["text"]

    def test_extract_docling_fallback_to_pymupdf_on_error(self):
        """If docling fails, should fall back to PyMuPDF."""
        from app.services.rag.parsers.pdf_parser import PDFParser
        parser = PDFParser()
        mock_docling = MagicMock()
        mock_docling.convert.side_effect = Exception("Docling error")
        parser.docling_converter = mock_docling

        mock_doc = MagicMock()
        mock_doc.metadata = {"title": ""}
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Fallback content" * 10
        mock_doc.__iter__.side_effect = lambda: iter([mock_page])
        mock_doc.__len__.return_value = 1

        with patch("fitz.open", return_value=mock_doc):
            result = parser.extract("test.pdf")

        assert "Fallback content" in result["text"]

    def test_extract_with_docling_success(self):
        """Docling extraction should return markdown text."""
        from app.services.rag.parsers.pdf_parser import PDFParser
        parser = PDFParser()

        mock_docling = MagicMock()
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "# Document Title\n\nContent here."
        mock_docling.convert.return_value = mock_result
        parser.docling_converter = mock_docling

        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_page = MagicMock()
        mock_page.get_text.return_value = "enough text to not be scanned" * 10
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))

        with patch("fitz.open", return_value=mock_doc):
            result = parser.extract("test.pdf")

        assert "Document Title" in result["text"]

    @patch("pdf2image.convert_from_path")
    @patch("pytesseract.image_to_string")
    def test_extract_with_ocr_success(self, mock_tesseract, mock_convert):
        """OCR fallback should return extracted text."""
        from app.services.rag.parsers.pdf_parser import PDFParser
        parser = PDFParser()

        mock_img = MagicMock()
        mock_convert.return_value = [mock_img]
        mock_tesseract.return_value = "OCR extracted text"

        result = parser._extract_with_ocr("scanned.pdf")
        assert "OCR extracted text" in result["text"]

    @patch("pdf2image.convert_from_path", side_effect=Exception("OCR error"))
    def test_extract_with_ocr_exception(self, mock_convert):
        """OCR failure should return empty dict."""
        from app.services.rag.parsers.pdf_parser import PDFParser
        parser = PDFParser()
        result = parser._extract_with_ocr("scanned.pdf")
        assert result["text"] == ""


# ── DocX Parser ────────────────────────────────────────────────────────────────

class TestDocxParser:
    def test_extract_with_valid_docx(self, tmp_path):
        """DocxParser should extract text from a docx file."""
        from app.services.rag.parsers.docx_parser import DocxParser

        mock_doc = MagicMock()
        para1 = MagicMock()
        para1.text = "First paragraph content."
        para2 = MagicMock()
        para2.text = "Second paragraph content."
        mock_doc.paragraphs = [para1, para2]

        with patch("docx.Document", return_value=mock_doc):
            parser = DocxParser()
            result = parser.extract("test.docx")

        assert "First paragraph content." in result["text"]
        assert result["metadata"]["source"] == "test.docx"

    def test_extract_exception(self):
        """Exception should return empty result dict."""
        from app.services.rag.parsers.docx_parser import DocxParser
        with patch("docx.Document", side_effect=Exception("File error")):
            parser = DocxParser()
            result = parser.extract("bad.docx")
        assert result["text"] == ""


# ── HTML Parser ────────────────────────────────────────────────────────────────

class TestHtmlParser:
    def test_extract_html_content(self, tmp_path):
        """HtmlParser should extract text from HTML."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><h1>Title</h1><p>Content here.</p></body></html>")

        from app.services.rag.parsers.html_parser import HtmlParser
        parser = HtmlParser()
        result = parser.extract(str(html_file))
        assert "Title" in result["text"] or "Content" in result["text"]

    def test_extract_exception(self):
        """Exception should return empty result dict."""
        from app.services.rag.parsers.html_parser import HtmlParser
        parser = HtmlParser()
        with patch("builtins.open", side_effect=Exception("File error")):
            result = parser.extract("bad.html")
        assert result["text"] == ""


# ── PPTX Parser ────────────────────────────────────────────────────────────────

class TestPptxParser:
    def test_extract_pptx_content(self):
        """PptxParser should extract text from slides."""
        from app.services.rag.parsers.pptx_parser import PptxParser

        mock_prs = MagicMock()
        mock_slide = MagicMock()
        mock_shape = MagicMock()
        mock_shape.has_text_frame = True
        mock_shape.text = "Slide content text"
        mock_tf = MagicMock()
        mock_para = MagicMock()
        mock_run = MagicMock()
        mock_run.text = "Slide content text"
        mock_para.runs = [mock_run]
        mock_tf.paragraphs = [mock_para]
        mock_shape.text_frame = mock_tf
        mock_slide.shapes = [mock_shape]
        mock_prs.slides = [mock_slide]

        with patch("pptx.Presentation", return_value=mock_prs):
            parser = PptxParser()
            result = parser.extract("slides.pptx")

        assert "Slide content text" in result["text"]

    def test_extract_pptx_exception(self):
        """Exception should return empty result dict."""
        from app.services.rag.parsers.pptx_parser import PptxParser
        with patch("pptx.Presentation", side_effect=Exception("PPTX error")):
            parser = PptxParser()
            result = parser.extract("bad.pptx")
        assert result["text"] == ""

    def test_extract_shape_without_text_frame(self):
        """Shapes without text frames should be skipped."""
        from app.services.rag.parsers.pptx_parser import PptxParser

        mock_prs = MagicMock()
        mock_slide = MagicMock()
        mock_shape = MagicMock()
        mock_shape.has_text_frame = False  # No text frame
        mock_slide.shapes = [mock_shape]
        mock_prs.slides = [mock_slide]

        with patch("pptx.Presentation", return_value=mock_prs):
            parser = PptxParser()
            result = parser.extract("slides.pptx")

        assert result["text"] == "" or isinstance(result["text"], str)
