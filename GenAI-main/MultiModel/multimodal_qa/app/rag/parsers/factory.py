from .base import BaseParser
from .pdf_parser import PDFParser
from .docx_parser import DocxParser
from .pptx_parser import PptxParser
from .html_parser import HtmlParser
from .markdown_parser import MarkdownParser
import os

class ParserFactory:
    @staticmethod
    def get_parser(file_path: str) -> BaseParser:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return PDFParser()
        elif ext in [".docx", ".doc"]:
            return DocxParser()
        elif ext in [".pptx", ".ppt"]:
            return PptxParser()
        elif ext in [".html", ".htm"]:
            return HtmlParser()
        elif ext in [".md", ".markdown"]:
            return MarkdownParser()
        else:
            raise ValueError(f"No parser found for extension {ext}")
