"""Part A.2 Text extraction/normalization. Keeps page/line provenance."""
import re

def normalize(text: str) -> str:
    # Normalize whitespace, keep section markers for chunker
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse 3+ newlines but keep double for section boundaries
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Fix hyphenated line breaks from PDFs
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    return text.strip()

def split_pages_for_provenance(pages: list[str] | None) -> list[tuple[int, str]]:
    """Return (page_num 1-indexed, text) for citation."""
    if not pages:
        return []
    return [(i+1, p) for i, p in enumerate(pages)]

def is_boilerplate(line: str) -> bool:
    # Minimal filter — keep most; evaluation will measure recall
    if len(line.strip()) < 8:
        return True
    return False
