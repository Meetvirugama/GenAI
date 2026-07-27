from .base import BaseParser
from typing import Dict, Any

class MarkdownParser(BaseParser):
    def _extract(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, 'r', encoding='utf-8') as f:
            md_text = f.read()
        return {
            "text": md_text,
            "pages": [{"page_num": 1, "text": md_text}],
            "tables": [],
            "images": [],
            "metadata": {"source": file_path},
            "sections": []
        }
