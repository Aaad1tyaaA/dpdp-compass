"""Embedding generation — configurable, singleton (perf fix), LangChain-compatible. Same model for docs+queries."""
from typing import List
import logging
import time
from app.config import settings

logger = logging.getLogger(__name__)

# Singleton cache — fixes ~89s reload-per-call
_MODEL_CACHE: dict[str, object] = {}
_LAST_EMBED_LATENCY_MS: int = 0

def _mock_embed(texts: List[str]) -> List[List[float]]:
    import hashlib
    out = []
    for t in texts:
        h = hashlib.sha256(t.encode()).digest()
        vec = [(b / 255.0) for b in (h * 12)[:384]]
        out.append(vec)
    return out

def _get_st_model(model_name: str):
    """Load once, reuse. Returns None if unavailable (falls back to mock)."""
    if model_name in _MODEL_CACHE:
        return _MODEL_CACHE[model_name]
    try:
        from app.compass.retrieval import embedder
        m = embedder(model_name)
        _MODEL_CACHE[model_name] = m
        logger.info("embeddings model loaded %s", model_name)
        return m
    except Exception as e:
        logger.debug("embeddings load failed %s: %s", model_name, e)
        return None

def get_langchain_embeddings():
    """LangChain Embeddings abstraction when langchain-huggingface installed; else None (custom path kept)."""
    try:
        from langchain_huggingface import HuggingFaceEmbeddings  # type: ignore
        return HuggingFaceEmbeddings(model_name=settings.embedding_model)  # type: ignore
    except Exception:
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings  # type: ignore
            return HuggingFaceEmbeddings(model_name=settings.embedding_model)  # type: ignore
        except Exception as e:
            logger.debug("langchain embeddings unavailable: %s", e)
            return None

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    global _LAST_EMBED_LATENCY_MS
    t0 = time.time()
    model_name = settings.embedding_model
    # In mock mode use deterministic hash so unit tests never need a key/model download
    if settings.mock_llm:
        embs = _mock_embed(texts)
        _LAST_EMBED_LATENCY_MS = int((time.time()-t0)*1000)
        return embs
    m = _get_st_model(model_name)
    if m is None:
        embs = _mock_embed(texts)
        _LAST_EMBED_LATENCY_MS = int((time.time()-t0)*1000)
        return embs
    try:
        embs = m.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()  # type: ignore
        _LAST_EMBED_LATENCY_MS = int((time.time()-t0)*1000)
        logger.info("embeddings model=%s n=%d ms=%d", model_name, len(texts), _LAST_EMBED_LATENCY_MS)
        return embs
    except Exception as e:
        logger.warning("embeddings fallback mock: %s", type(e).__name__)
        embs = _mock_embed(texts)
        _LAST_EMBED_LATENCY_MS = int((time.time()-t0)*1000)
        return embs

def last_embed_latency_ms() -> int:
    return _LAST_EMBED_LATENCY_MS

async def generate_embeddings_async(texts: List[str]) -> List[List[float]]:
    return generate_embeddings(texts)
