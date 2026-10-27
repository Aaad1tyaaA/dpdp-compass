import logging
from app.ingestion.parsers.base_parser import BaseParser, ParsedDocument, ParsedPage

logger = logging.getLogger(__name__)


class TxtParser(BaseParser):
    def can_parse(self, filename: str) -> bool:
        return filename.lower().endswith((".txt", ".md", ".csv", ".json"))

    def parse(self, content: bytes, filename: str, document_id: str) -> ParsedDocument:
        try:
            text = content.decode("utf-8", errors="ignore")
            return ParsedDocument(
                document_id=document_id,
                document_name=filename,
                document_type="text",
                pages=[ParsedPage(page_number=1, text=text)],
                raw_text=text,
                metadata={"parser": "text", "char_count": len(text)},
            )
        except Exception as e:
            logger.error("TXT parse failed for %s: %s", filename, e)
            raise
