import re
import hashlib
from dataclasses import dataclass, field


@dataclass
class ClauseChunk:
    id: str
    text: str
    section: str | None
    subsection: str | None
    clause_id: str | None
    page_number: int | None
    source_document: str
    document_type: str
    authority_level: str
    language: str = "en"
    entities: list[str] = field(default_factory=list)
    obligation_type: str | None = None
    legal_principle: str | None = None
    chunk_index: int = 0


def _make_chunk_id(source: str, index: int, text: str) -> str:
    h = hashlib.md5(f"{source}:{index}:{text[:200]}".encode()).hexdigest()[:12]
    return f"chunk_{h}"


def _detect_section_heading(text: str) -> tuple[str | None, str | None]:
    # Strip markdown heading markers like "## " or "# "
    body = re.sub(r"^\s*#+\s*", "", text)
    m = re.match(r"^\s*(?:Section|SECTION)\s+(\d+[A-Z]?)(?:\((\d+)\))?\s*[:\-]?\s*(.*)", body)
    if m:
        sec = f"Section {m.group(1)}"
        sub = m.group(2)
        return sec, sub
    m2 = re.match(r"^\s*(\d+)\.\s*\(?([A-Z]?)\)?\s+(.+)", body)
    if m2:
        return f"Section {m2.group(1)}", m2.group(2) or None
    m3 = re.match(r"^\s*(?:Section|SECTION)\s+([A-Z][A-Z0-9]*)\s*[:\-]?\s*(.*)", body)
    if m3:
        return f"Section {m3.group(1)}", None
    return None, None


def _is_clause_boundary(text: str) -> bool:
    body = re.sub(r"^\s*#+\s*", "", text.strip())
    return bool(re.match(r"^\s*(?:\d+\.)|(?:Section\s+\d+)|(?:CHAPTER|Chapter)|(?:Section\s+[A-Z])", body))


def _split_long(text: str, max_chars: int) -> list[str]:
    """Split an over-long section into pieces of at most max_chars, preferring sub-clause boundaries
    "(1)", "(2)"... then sentence ends. Previously everything past max_chars was silently dropped —
    e.g. DPDP Act Section 8(8)-(11) (DPO, grievance redressal) was never indexed."""
    if len(text) <= max_chars:
        return [text]
    units: list[str] = []
    for piece in re.split(r"(?=\(\d+\)\s)", text):
        while len(piece) > max_chars:  # one sub-clause longer than the limit: cut at a sentence/space
            cut = max(piece.rfind(". ", 0, max_chars), piece.rfind(" ", 0, max_chars))
            cut = cut + 1 if cut > max_chars // 2 else max_chars
            units.append(piece[:cut])
            piece = piece[cut:]
        if piece.strip():
            units.append(piece)
    out, buf = [], ""
    for u in units:
        if buf and len(buf) + len(u) > max_chars:
            out.append(buf.strip())
            buf = ""
        buf += u
    if buf.strip():
        out.append(buf.strip())
    return out


def clause_aware_chunk(text: str, source_document: str = "", document_type: str = "legal",
                       authority_level: str = "PRIMARY", max_chunk_chars: int = 2000) -> list[ClauseChunk]:
    parts = re.split(r"\n(?=\s*#+\s*(?:Section|SECTION)\s+|\s*(?:Section|SECTION)\s+\d+|\d+\.\s|[A-Z][A-Z\s]{5,}\n)", text)
    chunks: list[ClauseChunk] = []
    current_section = None
    current_subsection = None
    for i, raw in enumerate(parts):
        stripped = raw.strip()
        if not stripped or len(stripped) < 20:
            continue
        sec, sub = _detect_section_heading(stripped)
        if sec:
            current_section = sec
        if sub:
            current_subsection = sub
        pieces = _split_long(stripped, max_chunk_chars)
        for j, chunk_text in enumerate(pieces):
            chunks.append(ClauseChunk(
                id=_make_chunk_id(source_document, f"{i}.{j}" if j else i, chunk_text),
                text=chunk_text,
                section=current_section,
                subsection=current_subsection,
                clause_id=f"Clause {i + 1}" + (f".{j + 1}" if len(pieces) > 1 else ""),
                page_number=None,
                source_document=source_document,
                document_type=document_type,
                authority_level=authority_level,
                chunk_index=len(chunks),
            ))
    if not chunks and text.strip():
        for j, chunk_text in enumerate(_split_long(text.strip(), max_chunk_chars)):
            chunks.append(ClauseChunk(
                id=_make_chunk_id(source_document, j, chunk_text[:200]),
                text=chunk_text,
                section="Section 1",
                subsection=None,
                clause_id=f"Clause {j + 1}",
                page_number=None,
                source_document=source_document,
                document_type=document_type,
                authority_level=authority_level,
                chunk_index=j,
            ))
    return chunks
