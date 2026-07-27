from abc import ABC, abstractmethod
from typing import Dict, Any
from app.core.logger import get_logger

logger = get_logger(__name__)

class BaseParser(ABC):
    def extract(self, file_path: str) -> Dict[str, Any]:
        """
        Extracts content from a document.
        Returns a dictionary containing text, pages, tables, images, metadata, and sections.
        """
        try:
            return self._extract(file_path)
        except Exception:
            logger.exception(f"Error parsing {file_path}")
            return {"text": "", "pages": [], "tables": [], "images": [], "metadata": {}, "sections": []}

    @abstractmethod
    def _extract(self, file_path: str) -> Dict[str, Any]:
        """Implementation of document extraction to be provided by subclasses."""
        pass
