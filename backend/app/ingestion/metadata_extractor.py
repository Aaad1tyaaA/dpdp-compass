import re
from dataclasses import dataclass, field

PRINCIPLES = [
    "Consent", "Purpose Limitation", "Storage Limitation", "Accountability",
    "Transparency", "Security Safeguards", "Children Protection", "Data Minimisation",
]

OBLIGATION_KEYWORDS = {
    "consent": "Consent",
    "notice": "Notice/Disclosure",
    "withdraw": "Consent Withdrawal",
    "accuracy": "Accuracy",
    "security": "Security Safeguards",
    "breach": "Breach Notification",
    "retention": "Retention Limitation",
    "erasure": "Data Erasure",
    "children": "Children Data",
    "grievance": "Grievance Redressal",
    "dpo": "DPO Appointment",
    "transfer": "Cross-Border Transfer",
    "nomination": "Nomination",
    "correction": "Data Correction",
}


@dataclass
class ChunkMetadata:
    chunk_id: str
    source_document: str
    section: str | None
    subsection: str | None
    clause_id: str | None
    page_number: int | None
    document_type: str
    authority_level: str
    language: str
    entity: str | None
    entities: list[str]
    obligation_type: str | None
    legal_principle: str | None
    citation: str
    source_type: str
    document_id: str | None = None
    company_id: str | None = None
    document_hash: str | None = None
    chunk_index: int = 0


def _detect_entities(text: str) -> list[str]:
    entities = []
    checks = {
        "Data Principal": "data principal",
        "Data Fiduciary": "data fiduciary",
        "Data Processor": "data processor",
        "Data Protection Board": "data protection board",
        "Consent Manager": "consent manager",
    }
    lower = text.lower()
    for name, pattern in checks.items():
        if pattern in lower:
            entities.append(name)
    return entities


def _detect_principle(text: str) -> str | None:
    lower = text.lower()
    for p in PRINCIPLES:
        if p.lower() in lower:
            return p
    return None


def _detect_obligation(text: str) -> str | None:
    lower = text.lower()
    for kw, label in OBLIGATION_KEYWORDS.items():
        if kw in lower:
            return label
    return None


def extract_metadata(chunk_text: str, chunk_id: str, source_document: str, section: str | None,
                      clause_id: str | None, page_number: int | None, document_type: str,
                      authority_level: str, language: str = "en", document_id: str | None = None,
                      company_id: str | None = None, document_hash: str | None = None,
                      source_type: str | None = None) -> ChunkMetadata:
    entities = _detect_entities(chunk_text)
    citation = f"{source_document}"
    if section:
        citation += f" {section}"
    if clause_id:
        citation += f" {clause_id}"
    if page_number:
        citation += f" p.{page_number}"
    resolved_source_type = (source_type or ("LEGAL" if document_type in ("legal", "dpdp") else "POLICY")).upper()
    return ChunkMetadata(
        chunk_id=chunk_id,
        source_document=source_document,
        section=section,
        subsection=None,
        clause_id=clause_id,
        page_number=page_number,
        document_type=document_type,
        authority_level=authority_level,
        language=language,
        entity=entities[0] if entities else None,
        entities=entities,
        obligation_type=_detect_obligation(chunk_text),
        legal_principle=_detect_principle(chunk_text),
        citation=citation,
        source_type=resolved_source_type,
        document_id=document_id,
        company_id=company_id,
        document_hash=document_hash,
    )
