"""Graph Store — Neo4j with in-memory fallback. Nodes: Entity, Obligation, Right, Principle, Clause, Document. Relationships with provenance."""
import logging
from typing import Any, Dict, List
from app.knowledge_base.triplet_extractor import Triplet

logger = logging.getLogger(__name__)

_FALLBACK_TRIPLETS: list[Triplet] = []

_DRIVER = None
_RETRY_AT = 0.0


def _driver():
    """Shared Neo4j driver, or None, decided once per process (same reasoning as vector_store._qdrant:
    no per-request connect timeouts, and no switching to an empty graph mid-run)."""
    global _DRIVER, _RETRY_AT
    import time
    if _DRIVER is not None:
        return _DRIVER
    if time.time() < _RETRY_AT:
        return None
    try:
        from neo4j import GraphDatabase  # type: ignore
        from app.config import settings
        if settings.mock_llm:
            raise RuntimeError("mock uses fallback")
        from app.config import port_open
        if not port_open(settings.neo4j_uri):
            raise RuntimeError(f"nothing listening at {settings.neo4j_uri}")
        drv = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()), connection_timeout=2)
        drv.verify_connectivity()
        _DRIVER = drv
        return drv
    except Exception as e:
        logger.info("neo4j unavailable, using in-memory graph: %s", e)
        _RETRY_AT = float("inf")
        return None

def upsert_triplets(triplets: List[Triplet]):
    drv = _driver()
    if drv is None:
        _FALLBACK_TRIPLETS.extend(triplets)
        logger.info("graph upsert fallback n=%d total=%d", len(triplets), len(_FALLBACK_TRIPLETS))
        return
    try:
        with drv.session() as sess:
            for t in triplets:
                # Merge nodes, create relationship with provenance
                sess.run("""
                    MERGE (s:Entity {name: $sub})
                    MERGE (o:Entity {name: $obj})
                    MERGE (s)-[r:REL {predicate: $pred}]->(o)
                    SET r.source_chunk_id=$cid, r.source_document=$doc, r.section=$sec, r.page=$page, r.evidence=$ev
                """, sub=t.subject, obj=t.object, pred=t.predicate, cid=t.source_chunk_id, doc=t.source_document, sec=t.section, page=t.page, ev=t.evidence_text)
        logger.info("graph upsert neo4j n=%d", len(triplets))
    except Exception as e:
        logger.warning("graph upsert fallback after neo4j err %s", e)
        _FALLBACK_TRIPLETS.extend(triplets)

def traverse(query: str, top_k: int = 8) -> List[Dict[str, Any]]:
    """Keyword-ish graph traversal — returns matching triplets with provenance."""
    lower = query.lower()
    drv = _driver()
    if drv is None:
        out=[]
        for t in _FALLBACK_TRIPLETS:
            if lower in t.subject.lower() or lower in t.object.lower() or lower in t.predicate.lower() or lower in (t.section or "").lower():
                out.append({"subject": t.subject, "predicate": t.predicate, "object": t.object, "source_chunk_id": t.source_chunk_id, "source_document": t.source_document, "section": t.section, "page": t.page, "evidence": t.evidence_text, "score": 0.8})
            if len(out) >= top_k: break
        return out
    try:
        with drv.session() as sess:
            # Simple match on subject/object contains
            res = sess.run("""
                MATCH (s)-[r:REL]->(o)
                WHERE toLower(s.name) CONTAINS toLower($q) OR toLower(o.name) CONTAINS toLower($q) OR toLower(r.predicate) CONTAINS toLower($q)
                RETURN s.name as subject, r.predicate as predicate, o.name as object, r.source_chunk_id as cid, r.source_document as doc, r.section as section, r.page as page, r.evidence as ev LIMIT $k
            """, q=query, k=top_k)
            return [{"subject": r["subject"], "predicate": r["predicate"], "object": r["object"], "source_chunk_id": r["cid"], "source_document": r["doc"], "section": r["section"], "page": r["page"], "evidence": r["ev"], "score": 0.85} for r in res]
    except Exception as e:
        logger.warning("graph traverse fallback %s", e)
        return []

def reset_for_tests():
    global _FALLBACK_TRIPLETS
    _FALLBACK_TRIPLETS.clear()
    # keep neo4j data — not deleting prod; tests use fallback
