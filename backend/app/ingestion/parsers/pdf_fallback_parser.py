import io
import logging
from app.ingestion.parsers.base_parser import BaseParser, ParsedDocument, ParsedPage

logger = logging.getLogger(__name__)


class PDFFallbackParser(BaseParser):
    def can_parse(self, filename: str) -> bool:
        return filename.lower().endswith(".pdf")

    def parse(self, content: bytes, filename: str, document_id: str) -> ParsedDocument:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(content))
            pages = []
            page_texts = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages.append(ParsedPage(page_number=i + 1, text=text))
                page_texts.append(text)
            raw_text = "\n\n".join(page_texts)
            return ParsedDocument(
                document_id=document_id,
                document_name=filename,
                document_type="pdf",
                pages=pages,
                raw_text=raw_text,
                metadata={"parser": "PyPDF2_fallback", "page_count": len(pages)},
            )
        except Exception as e:
            logger.error("PyPDF2 fallback also failed for %s: %s", filename, e)
            raise
