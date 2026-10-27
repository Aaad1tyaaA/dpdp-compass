import re
from dataclasses import dataclass, field

CHAPTER_PATTERN = re.compile(r"^(?:CHAPTER|Chapter)\s+(\d+|[IVXLC]+)", re.MULTILINE)
SECTION_PATTERN = re.compile(r"^\s*(\d+)\.\s*\(?([1-9A-Z]?)\)?\s*([^\n]{5,200})", re.MULTILINE)
SUBSECTION_PATTERN = re.compile(r"^\s*\(?(\d+[a-z]?)\)?\s+([A-Z][^\n]{5,200})", re.MULTILINE)
CLAUSE_KEYWORDS = re.compile(
    r"\b(definitions|interpretation|application|consent|notice|rights|obligations|penalty|"
    r"power|offences|transitional|miscellaneous|schedule)\b",
    re.IGNORECASE,
)


@dataclass
class DetectedStructure:
    chapters: list[dict] = field(default_factory=list)
    sections: list[dict] = field(default_factory=list)
    subsections: list[dict] = field(default_factory=list)


def detect_structure(text: str) -> DetectedStructure:
    struct = DetectedStructure()
    for m in CHAPTER_PATTERN.finditer(text):
        struct.chapters.append({"number": m.group(1), "offset": m.start(), "title": m.group(0).strip()})
    for m in SECTION_PATTERN.finditer(text):
        struct.sections.append({
            "number": m.group(1),
            "sub": m.group(2) or None,
            "title": m.group(3).strip(),
            "offset": m.start(),
        })
    for m in SUBSECTION_PATTERN.finditer(text):
        struct.subsections.append({"number": m.group(1), "title": m.group(2).strip(), "offset": m.start()})
    return struct
