from typing import Any

from .base import BaseParser


class MarkdownParser(BaseParser):
    def _extract(self, file_path: str) -> dict[str, Any]:
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
