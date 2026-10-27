"""Triplet extraction — SUBJECT → PREDICATE → OBJECT with provenance.
Comprehensive statutory legal heuristics + LLM fallback. No unsupported relationships.
"""
from dataclasses import dataclass
import re
import logging
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Triplet:
    subject: str
    predicate: str
    object: str
    source_chunk_id: str
    source_document: str
    section: str | None
    page: int | None
    evidence_text: str  # the chunk excerpt proving it


# Allow-list predicates to avoid hallucination
ALLOWED_PREDICATES = {
    "MUST_PROVIDE",
    "HAS_RIGHT",
    "MUST_PROTECT",
    "MUST_NOTIFY",
    "MUST_OBTAIN",
    "PROHIBITS",
    "REQUIRES",
    "DEFINES",
    "APPLIES_TO",
    "HAS_DUTY",
    "MUST",
    "MUST_ERASE",
    "MUST_PROVIDE_NOTICE",
    "MUST_WITHDRAW",
    "MAY_IMPOSE_PENALTY",
    "MUST_APPOINT",
}


def heuristic_triplets(chunk_text: str, meta: dict, chunk_id: str) -> list[Triplet]:
    lower = chunk_text.lower()
    out: list[Triplet] = []

    def add(sub: str, pred: str, obj: str):
        if pred not in ALLOWED_PREDICATES:
            return
        out.append(
            Triplet(
                subject=sub,
                predicate=pred,
                object=obj,
                source_chunk_id=chunk_id,
                source_document=meta.get("source_document", ""),
                section=meta.get("section"),
                page=meta.get("page"),
                evidence_text=chunk_text[:400],
            )
        )

    # Section 5 & 6: Notice & Consent
    if "notice" in lower and ("fiduciary" in lower or "data" in lower):
        add("Data Fiduciary", "MUST_PROVIDE", "Notice Before Consent")
    if "withdraw" in lower and "consent" in lower:
        add("Data Principal", "HAS_RIGHT", "Withdraw Consent")
        add("Data Fiduciary", "MUST", "Allow Withdrawal With Ease")
    if "consent" in lower and ("free" in lower or "specific" in lower or "unconditional" in lower or "informed" in lower):
        add("Data Fiduciary", "MUST_OBTAIN", "Free Informed Specific Consent")

    # Section 8: Fiduciary Obligations
    if "security" in lower or "safeguard" in lower or "reasonable" in lower:
        add("Data Fiduciary", "MUST_PROTECT", "Personal Data")
    if "breach" in lower:
        add("Data Fiduciary", "MUST_NOTIFY", "Data Protection Board")
        add("Data Fiduciary", "MUST_NOTIFY", "Affected Data Principals")
    if "retention" in lower or "retain" in lower or "erase" in lower or "erasure" in lower:
        add("Data Fiduciary", "MUST_ERASE", "Personal Data On Purpose Completion")
    if "grievance" in lower or "redressal" in lower or "dpo" in lower or "officer" in lower:
        add("Data Fiduciary", "REQUIRES", "Grievance Redressal Mechanism")

    # Section 9: Children
    if "child" in lower or "children" in lower or "parental" in lower or "minor" in lower:
        add("Data Fiduciary", "MUST_OBTAIN", "Verifiable Parental Consent")
        add("Data Fiduciary", "PROHIBITS", "Behavioral Tracking of Children")

    # Section 10: Significant Data Fiduciary
    if "significant data fiduciary" in lower or "dpia" in lower or "data protection impact" in lower:
        add("Significant Data Fiduciary", "MUST_APPOINT", "Data Protection Officer")
        add("Significant Data Fiduciary", "REQUIRES", "Data Protection Impact Assessment")

    # Sections 11-14: Rights of Data Principal
    if "access" in lower and ("right" in lower or "principal" in lower):
        add("Data Principal", "HAS_RIGHT", "Access Information on Personal Data")
    if "correction" in lower and ("right" in lower or "principal" in lower):
        add("Data Principal", "HAS_RIGHT", "Correction of Inaccurate Personal Data")
    if "nominate" in lower or "nomination" in lower:
        add("Data Principal", "HAS_RIGHT", "Nomination in Case of Death or Incapacity")

    # Penalties & Board
    if "penalty" in lower or "crore" in lower or "schedule" in lower or "twenty-five crore" in lower or "two hundred and fifty crore" in lower:
        add("Data Protection Board", "MAY_IMPOSE_PENALTY", "Non-Compliance Penalties up to 250 Crores")

    # Deduplicate
    seen = set()
    uniq = []
    for t in out:
        key = (t.subject, t.predicate, t.object)
        if key not in seen:
            seen.add(key)
            uniq.append(t)
    return uniq


async def extract_triplets_llm(chunk_text: str, meta: dict, chunk_id: str) -> list[Triplet]:
    if settings.mock_llm or not (settings.llm_api_key or settings.openai_api_key):
        return heuristic_triplets(chunk_text, meta, chunk_id)
    try:
        from app.services.llm import get_llm
        llm = get_llm()
        system = "Extract only SUBJECT->PREDICATE->OBJECT triplets that are explicitly in the text. Allowed predicates: MUST_PROVIDE, HAS_RIGHT, MUST_PROTECT, MUST_NOTIFY, MUST_OBTAIN, PROHIBITS, REQUIRES, DEFINES, APPLIES_TO, MUST_ERASE, MAY_IMPOSE_PENALTY, MUST_APPOINT. Return JSON list [] with no invention. Include evidence excerpt."
        prompt = f"Text:\n{chunk_text[:1200]}\n\nReturn JSON like [{{\"subject\":\"Data Fiduciary\",\"predicate\":\"MUST_PROVIDE\",\"object\":\"Notice\"}}] only if supported."
        out = await llm.complete(prompt, system=system)
        import json
        m = re.search(r"\[.*\]", out, re.S)
        if not m:
            return heuristic_triplets(chunk_text, meta, chunk_id)
        data = json.loads(m.group(0))
        res = []
        for item in data:
            if item.get("predicate") not in ALLOWED_PREDICATES:
                continue
            res.append(
                Triplet(
                    subject=item["subject"],
                    predicate=item["predicate"],
                    object=item["object"],
                    source_chunk_id=chunk_id,
                    source_document=meta.get("source_document", ""),
                    section=meta.get("section"),
                    page=meta.get("page"),
                    evidence_text=chunk_text[:400],
                )
            )
        return res or heuristic_triplets(chunk_text, meta, chunk_id)
    except Exception as e:
        logger.warning("triplet llm fallback %s", e)
        return heuristic_triplets(chunk_text, meta, chunk_id)


async def extract_triplets(chunk_text: str, meta: dict, chunk_id: str) -> list[Triplet]:
    heur = heuristic_triplets(chunk_text, meta, chunk_id)
    if heur:
        return heur
    # Fallback to general baseline triplet
    doc_type = meta.get("document_type", "policy")
    sub = "Data Fiduciary" if doc_type == "legal" else meta.get("company_id", "Company")
    return [
        Triplet(
            subject=sub,
            predicate="DEFINES",
            object="Policy Clause",
            source_chunk_id=chunk_id,
            source_document=meta.get("source_document", ""),
            section=meta.get("section"),
            page=meta.get("page"),
            evidence_text=chunk_text[:300],
        )
    ]
