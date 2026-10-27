import logging
from app.ingestion.parsers.base_parser import BaseParser, ParsedDocument
from app.ingestion.parsers.pdf_parser import PyPDF2Parser
from app.ingestion.parsers.pdf_fallback_parser import PDFFallbackParser
from app.ingestion.parsers.docx_parser import DocxParser
from app.ingestion.parsers.txt_parser import TxtParser
from app.ingestion.parsers.html_parser import HtmlParser

logger = logging.getLogger(__name__)

ALL_PARSERS: list[BaseParser] = [
    PyPDF2Parser(),
    PDFFallbackParser(),
    DocxParser(),
    TxtParser(),
    HtmlParser(),
]


def parse_document(content: bytes, filename: str, document_id: str) -> ParsedDocument:
    for parser in ALL_PARSERS:
        if parser.can_parse(filename):
            try:
                result = parser.parse(content, filename, document_id)
                if result.raw_text and len(result.raw_text.strip()) > 10:
                    return result
                logger.warning("Parser %s produced insufficient text for %s", type(parser).__name__, filename)
            except Exception as e:
                logger.warning("Parser %s failed for %s: %s", type(parser).__name__, filename, e)
                continue
    raise ValueError(f"No parser could handle {filename}")
