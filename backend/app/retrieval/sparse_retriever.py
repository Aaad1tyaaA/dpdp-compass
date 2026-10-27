"""BM25 keyword retrieval, the lexical half of hybrid search.

The index is built lazily per collection straight from the vector store, and rebuilt when that
collection's size changes (new uploads). Previously nothing ever built it, so keyword search
silently returned [] and "hybrid" retrieval was vector-only, missing exact legal phrasing
such as "security safeguards".
"""
import logging
import re

logger = logging.getLogger(__name__)

_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "shall", "such", "any", "are", "was", "has", "have",
    "does", "how", "what", "who", "can", "may", "will", "not", "you", "your", "our", "its", "into", "under",
    "which", "their", "they", "them", "been", "being", "about", "also", "than", "then", "there", "these",
}
_INDEX: dict[str, tuple[int, object, list[dict]]] = {}  # collection -> (store version, BM25Plus, docs)


def _tokens(text: str) -> list[str]:
    # 5-char prefix stems: "secure"/"security"/"secured" all match; BM25's IDF damps any collisions.
    return [w[:5] for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in _STOP]


def _index_for(collection: str):
    from app.knowledge_base import vector_store
    cached = _INDEX.get(collection)
    if cached and cached[0] == vector_store.version():
        return cached[1], cached[2]
    docs = vector_store.records(collection)
    if not docs:
        return None, []
    try:
        # BM25Plus, not Okapi: Okapi's IDF is 0 for a term in half the docs, so small collections
        # (e.g. a single uploaded policy) returned nothing.
        from rank_bm25 import BM25Plus
    except ImportError:
        logger.warning("rank_bm25 not installed, sparse retrieval disabled")
        return None, []
    toks = [_tokens(d["text"]) for d in docs]
    for d, t in zip(docs, toks):
        d["_terms"] = set(t)  # precomputed once, used to filter non-matching docs per query
    bm25 = BM25Plus(toks)
    _INDEX[collection] = (vector_store.version(), bm25, docs)
    logger.info("BM25 index built collection=%s docs=%d", collection, len(docs))
    return bm25, docs


def sparse_retrieve(query: str, top_k: int = 8, where: dict | None = None, collection_name: str | None = None) -> list[dict]:
    from app.config import settings
    collection = collection_name or settings.qdrant_legal_collection
    bm25, docs = _index_for(collection)
    q = _tokens(query)
    if bm25 is None or not q:
        return []
    scores = bm25.get_scores(q)
    qset = set(q)
    hits = []
    for doc, score in zip(docs, scores):
        meta = doc.get("metadata", {})
        if not qset & doc["_terms"] or (where and any(meta.get(k) != v for k, v in where.items())):
            continue  # BM25Plus scores every doc > 0; only keep ones that share a query term
        hits.append({
            "chunk_id": doc["id"], "text": doc["text"], "metadata": meta,
            "source_document": meta.get("source_document"), "section": meta.get("section"),
            "clause_id": meta.get("clause_id"), "page_number": meta.get("page_number"),
            "citation": meta.get("citation"), "score": float(score), "type": "sparse",
        })
    hits.sort(key=lambda h: h["score"], reverse=True)
    top = hits[0]["score"] if hits else 1.0
    for h in hits:
        h["score"] /= top  # normalise to 0..1 so it blends with cosine scores
    return hits[:top_k]
