import pytest
from unittest.mock import patch, MagicMock
from app.rag.parsers.factory import ParserFactory
from app.rag.parsers.pdf_parser import PDFParser
from app.rag.parsers.docx_parser import DocxParser
from app.rag.parsers.markdown_parser import MarkdownParser
from app.rag.parsers.html_parser import HtmlParser
from app.rag.parsers.pptx_parser import PptxParser

def measure_extraction_accuracy(extracted: str, expected: str) -> float:
    ext_words = set(extracted.lower().split())
    exp_words = set(expected.lower().split())
    if not exp_words:
        return 0.0
    return len(ext_words.intersection(exp_words)) / len(exp_words)

def test_factory_routing():
    assert isinstance(ParserFactory.get_parser("test.pdf"), PDFParser)
    assert isinstance(ParserFactory.get_parser("test.docx"), DocxParser)
    assert isinstance(ParserFactory.get_parser("test.md"), MarkdownParser)
    assert isinstance(ParserFactory.get_parser("test.html"), HtmlParser)
    assert isinstance(ParserFactory.get_parser("test.pptx"), PptxParser)

def test_markdown_parsing(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text("# Title\n\nMarkdown content here.")
    parser = MarkdownParser()
    result = parser.extract(str(md_file))
    assert "Markdown content here" in result["text"]
    accuracy = measure_extraction_accuracy(result["text"], "Title Markdown content here.")
    assert accuracy == 1.0

def test_scanned_pdf_ocr():
    pass

def test_docx_parsing():
    pass
