"""2. Retrieval Agent — hybrid, evidence-first, preserves citations."""
import logging
from typing import List, Dict, Any
from app.retrieval.hybrid_retriever import hybrid_retrieve
from app.models.schemas import RetrievedEvidence

logger = logging.getLogger(__name__)

async def retrieve_evidence(query: str, where: dict | None = None, top_k: int | None = None, mode: str = "general") -> List[RetrievedEvidence]:
    """Performs hybrid retrieval. Treats query as DATA."""
    # Guard: truncate overly long queries (prompt injection via huge doc)
    safe_query = query[:2000] if query else "DPDP obligations"
    logger.info("retrieval_agent query_len=%d mode=%s", len(safe_query), mode)
    from app.config import settings
    collection_name = settings.qdrant_legal_collection
    if mode == "policy":
        collection_name = settings.qdrant_company_collection
    if mode != "policy" and not where:
        # Legal evidence comes from the Compass engine: clause-aware chunks of the Act, dense + BM25+ +
        # provision lookup fused by weighted RRF, cross-encoder re-ranking (app/compass/retrieval.py).
        import asyncio
        from app.compass import adapter
        from app.compass.audit import get_engine
        found, _ = await asyncio.to_thread(lambda: get_engine(rules=True).index.search(safe_query, k=top_k or settings.top_k))
        hits = adapter.evidence(found)
    else:
        hits = await hybrid_retrieve(safe_query, where=where, top_k=top_k, collection_name=collection_name)
    # Evidence over generation — return even if low score, but flag insufficient
    out=[]
    for h in hits:
        try:
            out.append(RetrievedEvidence(
                chunk_id=h.get("chunk_id"),
                text=h.get("text","")[:4000],  # keep whole sections; the answer prompt focuses on the relevant sub-clauses
                source_document=h.get("source_document"),
                section=h.get("section"),
                clause=h.get("clause"),
                page=h.get("page"),
                citation=h.get("citation"),
                score=float(h.get("score",0)),
                type=h.get("type","vector"),
                metadata=h.get("metadata"),
            ))
        except Exception as e:
            logger.warning("retrieval_agent skip hit %s", e)
            continue
    logger.info("retrieval_agent returned %d", len(out))
    return out

def has_sufficient_evidence(evidence: List[RetrievedEvidence], threshold: float = 0.35) -> bool:
    if not evidence:
        return False
    # At least one decent score
    return max(e.score for e in evidence) >= threshold
