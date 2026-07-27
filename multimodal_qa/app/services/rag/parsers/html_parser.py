from typing import Any

from .base import BaseParser


class HtmlParser(BaseParser):
    def _extract(self, file_path: str) -> dict[str, Any]:
        from bs4 import BeautifulSoup
        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text(separator="\n", strip=True)
        title = soup.title.string if soup.title else ""
        
        return {
            "text": text,
            "pages": [{"page_num": 1, "text": text}],
            "tables": [],
            "images": [],
            "metadata": {"source": file_path, "title": title},
            "sections": []
        }
