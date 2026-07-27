import logging
from typing import Any

import fitz  # PyMuPDF

from .base import BaseParser

logger = logging.getLogger(__name__)

class PDFParser(BaseParser):
    def __init__(self):
        try:
            # pyrefly: ignore [missing-import]
            from docling.document_converter import DocumentConverter
            self.docling_converter = DocumentConverter()
        except ImportError:
            logger.warning("Docling is not installed. PDF parsing will fallback.")
            self.docling_converter = None
        except Exception as e:
            logger.warning(f"Docling initialization failed: {e}")
            self.docling_converter = None

    def _is_scanned(self, file_path: str) -> bool:
        """Heuristic to detect if PDF is scanned (low text volume)."""
        try:
            doc = fitz.open(file_path)
            if len(doc) == 0:
                return False
            text_pages = 0
            for page in doc:
                if len(page.get_text().strip()) > 50:
                    text_pages += 1
            # If less than 10% of pages have extractable text, assume scanned
            return (text_pages / len(doc)) < 0.1
        except Exception as e:
            logger.error(f"Error checking if scanned: {e}")
            return False

    def _extract_with_ocr(self, file_path: str) -> dict[str, Any]:
        """OCR Fallback using pdf2image and pytesseract"""
        import pytesseract
        from pdf2image import convert_from_path
        
        logger.info(f"Using OCR fallback for {file_path}")
        text_content = []
        pages = []
        try:
            images = convert_from_path(file_path)
            for i, img in enumerate(images):
                text = pytesseract.image_to_string(img)
                text_content.append(text)
                pages.append({"page_num": i + 1, "text": text})
            return {
                "text": "\n\n".join(text_content),
                "pages": pages,
                "tables": [],
                "images": [],
                "metadata": {"source": file_path, "type": "scanned_pdf"},
                "sections": []
            }
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return {"text": "", "tables": [], "images": [], "metadata": {}, "sections": []}

    def _extract_with_pymupdf(self, file_path: str) -> dict[str, Any]:
        """Fast fallback using PyMuPDF"""
        logger.info(f"Using PyMuPDF fallback for {file_path}")
        try:
            doc = fitz.open(file_path)
            text_content = []
            pages = []
            for i, page in enumerate(doc):
                page_text = page.get_text()
                text_content.append(page_text)
                pages.append({"page_num": i + 1, "text": page_text})
            return {
                "text": "\n\n".join(text_content).strip(),
                "pages": pages,
                "tables": [],
                "images": [],
                "metadata": {"source": file_path, "title": doc.metadata.get("title", "")},
                "sections": []
            }
        except Exception as e:
            logger.error(f"PyMuPDF failed: {e}")
            return {"text": "", "tables": [], "images": [], "metadata": {}, "sections": []}

    def _extract(self, file_path: str) -> dict[str, Any]:
        if self._is_scanned(file_path):
            return self._extract_with_ocr(file_path)
            
        # Try Docling First
        if self.docling_converter:
            try:
                logger.info(f"Attempting Docling extraction for {file_path}")
                result = self.docling_converter.convert(file_path)
                md_text = result.document.export_to_markdown()
                return {
                    "text": md_text,
                    "pages": [{"page_num": 1, "text": md_text}],
                    "tables": [], # Docling markdown includes tables naturally
                    "images": [],
                    "metadata": {"source": file_path},
                    "sections": []
                }
            except Exception as e:
                logger.warning(f"Docling extraction failed: {e}")
                
        # PyMuPDF fallback
        return self._extract_with_pymupdf(file_path)
