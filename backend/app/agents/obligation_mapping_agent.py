"""3. Obligation Mapping Agent — maps retrieved legal evidence to structured obligations."""
import logging
import json
import re
from typing import List
from app.models.schemas import RetrievedEvidence, Obligation
from app.services.llm import get_llm
from app.config import settings

logger = logging.getLogger(__name__)


def _to_list(value) -> list[str]:
    """Coerce conditions/exceptions (LLM may return str or null) into a list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()][:3]
    if isinstance(value, str):
        parts = re.split(r"[;,\n]", value)
        return [p.strip() for p in parts if p.strip()][:3]
    return []

SYSTEM = """You are the Obligation Mapping Agent. Given retrieved DPDP legal evidence, list applicable obligations.
- Only obligations explicitly supported by evidence.
- For each: obligation, source, section, applies_to (Data Fiduciary/Principal/Processor), conditions, exceptions, principle.
- Return JSON array. No invention."""

FALLBACK_OBLIGATIONS = [
    {"obligation": "Provide clear notice before collecting personal data", "obligation_id": "DPDP-6", "source": "DPDP Act", "section": "Section 6", "applies_to": "Data Fiduciary", "principle": "Transparency"},
    {"obligation": "Obtain free, specific, informed, unconditional consent with clear affirmative action", "obligation_id": "DPDP-6(1)", "source": "DPDP Act", "section": "Section 6(1)", "applies_to": "Data Fiduciary", "principle": "Consent"},
    {"obligation": "Provide easy mechanism to withdraw consent, as easy as giving consent", "obligation_id": "DPDP-6(4)", "source": "DPDP Act", "section": "Section 6(4)", "applies_to": "Data Fiduciary", "principle": "Consent"},
    {"obligation": "Process personal data only for disclosed lawful purposes", "obligation_id": "DPDP-6(2)", "source": "DPDP Act", "section": "Section 6(2)", "applies_to": "Data Fiduciary", "principle": "Purpose Limitation"},
    {"obligation": "Adapt reasonable security safeguards, including appropriate encryption, to protect personal data", "obligation_id": "DPDP-8(5)", "source": "DPDP Act", "section": "Section 8(5)", "applies_to": "Data Fiduciary", "principle": "Security Safeguards"},
    {"obligation": "Notify Board and affected Data Principal of personal data breach within 72 hours", "obligation_id": "DPDP-8(6)", "source": "DPDP Act", "section": "Section 8(6)", "applies_to": "Data Fiduciary", "principle": "Accountability"},
    {"obligation": "Stop processing and erase personal data upon withdrawal of consent or when purpose is served", "obligation_id": "DPDP-8(7)", "source": "DPDP Act", "section": "Section 8(7)", "applies_to": "Data Fiduciary", "principle": "Storage Limitation"},
    {"obligation": "Appoint a Data Protection Officer and make their details publicly available", "obligation_id": "DPDP-8(9)", "source": "DPDP Act", "section": "Section 8(9)", "applies_to": "Data Fiduciary", "principle": "Accountability"},
    {"obligation": "Establish a grievance redressal mechanism and acknowledge/respond to complaints", "obligation_id": "DPDP-8(10)", "source": "DPDP Act", "section": "Section 8(10)", "applies_to": "Data Fiduciary", "principle": "Accountability"},
    {"obligation": "Obtain verifiable parental consent before processing children's personal data", "obligation_id": "DPDP-9", "source": "DPDP Act", "section": "Section 9", "applies_to": "Data Fiduciary", "principle": "Children Protection"},
    {"obligation": "Ensure rights of access, correction, completion and erasure are honoured", "obligation_id": "DPDP-11/12", "source": "DPDP Act", "section": "Section 11-12", "applies_to": "Data Fiduciary", "principle": "Data Principal Rights"},
]

CANONICAL_FIDUCIARY_IDS = {o["obligation_id"] for o in FALLBACK_OBLIGATIONS}


def _dedupe_obligations(obligations: list[Obligation]) -> list[Obligation]:
    seen: set[str] = set()
    out: list[Obligation] = []
    for o in obligations:
        key = (o.obligation_id or o.obligation)[:60].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(o)
    return out


async def map_obligations(evidence: List[RetrievedEvidence], company_context: str = "", use_llm: bool = True) -> List[Obligation]:
    # Always ground the canonical Data Fiduciary obligations (even if retrieval missed them),
    # enriched by evidence where available. This keeps company audits comprehensive.
    canonical: list[Obligation] = []
    text_lower = " ".join(e.text.lower() for e in evidence)
    for tmpl in FALLBACK_OBLIGATIONS:
        # attach evidence whose text mentions this obligation's keywords
        kw = [w for w in tmpl["obligation"].lower().replace(",", " ").split() if len(w) > 3]
        matched = [e for e in evidence if any(k in e.text.lower() for k in kw[:4])]
        canonical.append(Obligation(**tmpl, evidence=matched[:2] or evidence[:1], conditions=[], exceptions=[]))

    if not evidence:
        logger.warning("obligation_mapping no evidence → canonical only")
        return canonical

    # If mock, return canonical grounded obligations (no LLM)
    if not use_llm or settings.mock_llm or not (settings.llm_api_key or settings.openai_api_key):
        return canonical

    llm = get_llm()
    ev_text = "\n\n".join(f"[{e.source_document} {e.section}] {e.text[:600]}" for e in evidence[:6])
    prompt = f"Legal Evidence:\n{ev_text}\n\nCompany context: {company_context[:400]}\n\nMap obligations as JSON array."
    try:
        raw = await llm.complete(prompt, system=SYSTEM)
        # Extract JSON array
        import re
        m = re.search(r"\[.*\]", raw, re.S)
        if not m:
            raise ValueError("no JSON array")
        data = json.loads(m.group(0))
        additional: list[Obligation] = []
        for item in data:
            try:
                # skip if it duplicates a canonical obligation
                oid = item.get("obligation_id") or (item.get("section") or "")
                if oid and oid in CANONICAL_FIDUCIARY_IDS:
                    continue
                oblig = Obligation(
                    obligation=(item.get("obligation") or "").strip()[:300],
                    obligation_id=item.get("obligation_id"),
                    source=(item.get("source") or "DPDP Act"),
                    section=item.get("section"),
                    applies_to=item.get("applies_to"),
                    conditions=_to_list(item.get("conditions")),
                    exceptions=_to_list(item.get("exceptions")),
                    evidence=evidence[:2],
                    principle=item.get("principle"),
                )
                if oblig.obligation:
                    additional.append(oblig)
            except Exception as per_item:
                logger.warning("obligation_mapping skip item: %s", per_item)
        merged = _dedupe_obligations(canonical + additional)
        logger.info("obligation_mapping llm n=%d (canonical=%d additional=%d)", len(merged), len(canonical), len(additional))
        return merged[:len(canonical) + 4]  # all canonical + up to 4 evidence-backed extras
    except Exception as e:
        logger.warning("obligation_mapping fallback %s", e)
        return canonical
