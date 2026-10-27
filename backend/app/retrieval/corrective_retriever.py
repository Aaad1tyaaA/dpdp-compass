import logging
from typing import Optional

logger = logging.getLogger(__name__)

DETECTABLE_CONCEPTS = {
    "retention": ["retention", "retention period", "data retention", "storage limitation", "data erasure", "erasure", "deletion"],
    "consent": ["consent", "withdrawal of consent", "withdraw consent", "free consent", "informed consent"],
    "security": ["security", "security safeguards", "data security", "encryption", "protection"],
    "breach": ["breach", "data breach", "breach notification", "notify board"],
    "children": ["children", "child", "minor", "parental consent", "verifiable parental consent"],
    "rights": ["rights", "access", "correction", "nomination", "grievance", "erasure right"],
    "purpose": ["purpose", "purpose limitation", "lawful purpose", "processing purpose"],
    "sharing": ["sharing", "third party", "processor", "cross-border", "transfer"],
}


def detect_missing_concepts(retrieved_texts: list[str], query: str) -> list[str]:
    combined = " ".join(retrieved_texts).lower() + " " + query.lower()
    missing = []
    for concept, keywords in DETECTABLE_CONCEPTS.items():
        if not any(kw in combined for kw in keywords):
            missing.append(concept)
    return missing


async def corrective_retrieve(base_query: str, retrieved_texts: list[str],
                               retrieve_fn, max_retries: int = 2) -> list[dict]:
    from app.config import settings
    max_retries = min(max_retries, settings.max_corrective_retries)
    missing = detect_missing_concepts(retrieved_texts, base_query)
    if not missing:
        return []
    extra_hits: list[dict] = []
    for concept in missing[:max_retries]:
        target_query = f"{base_query} {concept} DPDP Act"
        try:
            hits = await retrieve_fn(target_query, top_k=4)
            extra_hits.extend(hits)
        except Exception as e:
            logger.warning("corrective retrieve failed for concept %s: %s", concept, e)
    return extra_hits
