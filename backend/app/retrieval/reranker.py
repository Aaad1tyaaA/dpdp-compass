import logging

logger = logging.getLogger(__name__)

_reranker_model = None


def _get_reranker():
    global _reranker_model
    if _reranker_model is not None:
        return _reranker_model
    try:
        from sentence_transformers import CrossEncoder
        from app.config import settings
        _reranker_model = CrossEncoder(settings.reranker_model)
        logger.info("reranker loaded: %s", settings.reranker_model)
        return _reranker_model
    except Exception as e:
        logger.debug("reranker unavailable: %s", e)
        return None


def rerank(query: str, candidates: list[dict], top_n: int = 5) -> list[dict]:
    if not candidates:
        return []
    model = _get_reranker()
    if model is None:
        return candidates[:top_n]
    try:
        # ~2000 chars is the model's 512-token window; cutting at 512 *chars* hid e.g. Section 8(5)
        # ("reasonable security safeguards"), which sits past char 512 of the Section 8 chunk.
        pairs = [(query, c.get("text", "")[:2000]) for c in candidates]
        scores = model.predict(pairs)
        for i, c in enumerate(candidates):
            c["rerank_score"] = float(scores[i])
        candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
    except Exception as e:
        logger.warning("rerank failed: %s", e)
    return candidates[:top_n]
