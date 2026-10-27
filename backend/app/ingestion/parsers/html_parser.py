import logging
from app.ingestion.parsers.base_parser import BaseParser, ParsedDocument, ParsedPage

logger = logging.getLogger(__name__)


class HtmlParser(BaseParser):
    def can_parse(self, filename: str) -> bool:
        return filename.lower().endswith((".html", ".htm"))

    def parse(self, content: bytes, filename: str, document_id: str) -> ParsedDocument:
        try:
            from bs4 import BeautifulSoup
            raw_html = content.decode("utf-8", errors="ignore")
            soup = BeautifulSoup(raw_html, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            return ParsedDocument(
                document_id=document_id,
                document_name=filename,
                document_type="html",
                pages=[ParsedPage(page_number=1, text=text)],
                raw_text=text,
                metadata={"parser": "beautifulsoup", "char_count": len(text)},
            )
        except ImportError:
            logger.warning("BeautifulSoup not installed, falling back to regex HTML strip")
            import re
            raw = content.decode("utf-8", errors="ignore")
            text = re.sub(r"<[^>]+>", " ", raw)
            text = re.sub(r"\s+", " ", text).strip()
            return ParsedDocument(
                document_id=document_id,
                document_name=filename,
                document_type="html",
                pages=[ParsedPage(page_number=1, text=text)],
                raw_text=text,
                metadata={"parser": "regex_fallback"},
            )
