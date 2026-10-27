import io
import logging
from app.ingestion.parsers.base_parser import BaseParser, ParsedDocument, ParsedPage

logger = logging.getLogger(__name__)


class PyPDF2Parser(BaseParser):
    def can_parse(self, filename: str) -> bool:
        return filename.lower().endswith(".pdf")

    def parse(self, content: bytes, filename: str, document_id: str) -> ParsedDocument:
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            pages = []
            page_texts = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages.append(ParsedPage(page_number=i + 1, text=text))
                page_texts.append(text)
            raw_text = "\n\n".join(page_texts)
            total_chars = sum(len(p.text) for p in pages)
            if total_chars < 50:
                logger.warning("PyPDF2 extracted insufficient text from %s (%d chars)", filename, total_chars)
                return ParsedDocument(
                    document_id=document_id,
                    document_name=filename,
                    document_type="pdf",
                    pages=pages,
                    raw_text=raw_text,
                    metadata={"parser": "pypdf", "status": "insufficient_text", "char_count": total_chars},
                )
            return ParsedDocument(
                document_id=document_id,
                document_name=filename,
                document_type="pdf",
                pages=pages,
                raw_text=raw_text,
                metadata={"parser": "pypdf", "char_count": total_chars, "page_count": len(pages)},
            )
        except Exception as e:
            logger.error("PyPDF2 parse failed for %s: %s", filename, e)
            raise
