import asyncio
import logging
import time
from app.config import settings
from app.retrieval import vector_retriever, graph_retriever, sparse_retriever

logger = logging.getLogger(__name__)

_LAST_DIAG: dict = {}


def last_retrieval_diag() -> dict:
    return _LAST_DIAG


async def hybrid_retrieve(query: str, where: dict | None = None, top_k: int | None = None,
                           include_graph: bool = True, collection_name: str | None = None) -> list[dict]:
    global _LAST_DIAG
    t0 = time.time()
    k = top_k or settings.top_k
    alpha = settings.hybrid_alpha
    t_vec = time.time()
    vec_task = vector_retriever.retrieve(query, top_k=k, where=where, collection_name=collection_name)
    graph_task = graph_retriever.retrieve(query, top_k=k // 2) if include_graph else asyncio.sleep(0, result=[])
    meta_task = asyncio.sleep(0, result=[])
    vec, graph_hits, meta_hits = await asyncio.gather(vec_task, graph_task, meta_task)
    vec_ms = int((time.time() - t_vec) * 1000)
    sparse_hits = sparse_retriever.sparse_retrieve(query, top_k=k, where=where, collection_name=collection_name)
    seen: dict[str, dict] = {}
    for h in vec:
        cid = h.get("chunk_id") or h.get("id") or h.get("text", "")[:50]
        h["score"] = h.get("score", 0) * alpha + 0.1
        seen[cid] = h
    for h in sparse_hits:
        cid = h.get("chunk_id") or h.get("id") or h.get("text", "")[:50]
        h["score"] = h.get("score", 0) * (1 - alpha) + 0.15
        if cid in seen:
            seen[cid]["score"] = min(1.0, seen[cid]["score"] + h["score"] * 0.3)
        else:
            seen[cid] = h
    for h in graph_hits:
        cid = h.get("chunk_id") or h.get("text", "")[:50]
        h["score"] = h.get("score", 0) * (1 - alpha) + 0.2
        if cid in seen:
            seen[cid]["score"] = min(1.0, seen[cid]["score"] + 0.12)
        else:
            seen[cid] = h
    # Heading-only fragments ("DATA PROTECTION BOARD OF INDIA", "CHAPTER VI ...") are all capitals and carry
    # no content, but crowd out real clauses. Short real clauses (any lowercase text) are kept.
    merged = sorted((h for h in seen.values() if any(ch.islower() for ch in (h.get("text") or ""))),
                    key=lambda x: x.get("score", 0), reverse=True)
    for m in merged:
        if not m.get("citation") and m.get("metadata"):
            m["citation"] = m["metadata"].get("citation")
    from app.retrieval.reranker import rerank
    reranked = rerank(query, merged[:k * 2], top_n=min(k, settings.rerank_top_n))
    total_ms = int((time.time() - t0) * 1000)
    from app.knowledge_base.embedding_generator import last_embed_latency_ms
    _LAST_DIAG = {
        "query_len": len(query), "vector_results": len(vec),
        "sparse_results": len(sparse_hits), "graph_results": len(graph_hits),
        "rrf_merged": len(merged), "final_results": len(reranked),
        "embed_ms": last_embed_latency_ms(), "retrieval_ms": vec_ms, "total_ms": total_ms,
        "top_k": k, "scores": [round(m.get("score", 0), 3) for m in reranked[:k]],
    }
    logger.info("hybrid vec=%d sparse=%d graph=%d rrf=%d rerank=%d ms=%d",
                len(vec), len(sparse_hits), len(graph_hits), len(merged), len(reranked), total_ms)
    return reranked


async def retrieve_with_citations(query: str, top_k: int = 8, collection_name: str | None = None) -> list[dict]:
    return await hybrid_retrieve(query, top_k=top_k, collection_name=collection_name)
