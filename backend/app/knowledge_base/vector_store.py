import logging
import math
import uuid
from typing import Any
from app.config import settings, reveal

logger = logging.getLogger(__name__)

_FALLBACK: dict[str, dict] = {}
_VERSION = 0  # bumped on every write, so derived indexes (BM25) know when to rebuild


def version() -> int:
    return _VERSION
_qdrant_client = None


def _to_valid_point_id(val: Any) -> str:
    s = str(val)
    try:
        int(s)
        return s
    except ValueError:
        pass
    try:
        uuid.UUID(s)
        return s
    except (ValueError, TypeError):
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, s))


_qdrant_retry_at = 0.0


def _qdrant():
    """Connected client, or None. Availability is decided once per process: retrying mid-run cost
    a 5s+ connect timeout on a random request, and a Qdrant that appears later would be *empty*
    while the indexed data lives in the in-memory fallback. Restart the API to switch stores."""
    global _qdrant_client, _qdrant_retry_at
    if _qdrant_client is not None:
        return _qdrant_client
    import time
    if time.time() < _qdrant_retry_at:
        return None
    try:
        if settings.mock_llm and not settings.qdrant_api_key:
            raise RuntimeError("mock mode")
        from app.config import port_open
        if not port_open(settings.qdrant_url):
            raise RuntimeError(f"nothing listening at {settings.qdrant_url}")
        from qdrant_client import QdrantClient
        client = QdrantClient(url=settings.qdrant_url, api_key=reveal(settings.qdrant_api_key), timeout=5, check_compatibility=False)
        _ensure_collection(client, settings.qdrant_legal_collection)
        _ensure_collection(client, settings.qdrant_company_collection)
        _ensure_collection(client, settings.qdrant_collection)
        _qdrant_client = client
        return client
    except Exception as e:
        logger.info("qdrant unavailable, using in-memory store: %s", e)
        _qdrant_retry_at = float("inf")
        return None


def _ensure_collection(client, name: str):
    try:
        client.get_collection(name)
    except Exception:
        from qdrant_client.models import Distance, VectorParams
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
        )
        logger.info("created qdrant collection: %s", name)


def upsert(ids: list[str], texts: list[str], embeddings: list[list[float]],
           metadatas: list[dict[str, Any]], collection_name: str | None = None):
    global _VERSION
    _VERSION += 1
    collection = collection_name or settings.qdrant_legal_collection
    qc = _qdrant()
    if qc is not None:
        try:
            from qdrant_client.models import PointStruct
            points = [
                PointStruct(
                    id=_to_valid_point_id(ids[i]),
                    vector=embeddings[i],
                    payload={"chunk_id": str(ids[i]), "text": texts[i], **metadatas[i]}
                )
                for i in range(len(ids))
            ]
            qc.upsert(collection_name=collection, points=points)
            logger.info("vector upsert qdrant collection=%s n=%d", collection, len(ids))
            return
        except Exception as e:
            logger.warning("qdrant upsert failed %s: %s", collection, e)
    for i, _id in enumerate(ids):
        key = f"{collection}:{_id}"
        _FALLBACK[key] = {"text": texts[i], "embedding": embeddings[i], "metadata": metadatas[i]}
    logger.info("vector upsert fallback collection=%s n=%d", collection, len(ids))


def query(query_embedding: list[float], top_k: int = 8, where: dict | None = None,
          collection_name: str | None = None) -> list[dict[str, Any]]:
    collection = collection_name or settings.qdrant_legal_collection
    qc = _qdrant()
    if qc is not None:
        try:
            flt = None
            if where:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                must = [FieldCondition(key=k, match=MatchValue(value=v)) for k, v in where.items()]
                flt = Filter(must=must)
            res = qc.query_points(collection_name=collection, query=query_embedding, limit=top_k, query_filter=flt)
            out = []
            for p in getattr(res, "points", res):
                payload = getattr(p, "payload", {}) or {}
                out.append({"id": str(getattr(p, "id", "")), "text": payload.get("text", ""),
                            "metadata": payload, "score": float(getattr(p, "score", 0))})
            return out
        except Exception as e:
            logger.warning("qdrant query failed %s: %s", collection, e)
    scored = []
    prefix = f"{collection}:"
    for key, rec in _FALLBACK.items():
        if not key.startswith(prefix):
            continue
        if where and any(rec["metadata"].get(k) != v for k, v in where.items()):
            continue
        sc = _cosine(query_embedding, rec["embedding"])
        scored.append({"id": key[len(prefix):], "text": rec["text"], "metadata": rec["metadata"], "score": sc})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def records(collection_name: str | None = None) -> list[dict[str, Any]]:
    """All {id, text, metadata} in a collection, with the same ids query() returns (for the keyword index)."""
    collection = collection_name or settings.qdrant_legal_collection
    qc = _qdrant()
    if qc is not None:
        try:
            out, offset = [], None
            while True:
                points, offset = qc.scroll(collection_name=collection, limit=256, offset=offset, with_payload=True, with_vectors=False)
                out += [{"id": str(p.id), "text": (p.payload or {}).get("text", ""), "metadata": p.payload or {}} for p in points]
                if offset is None:
                    return out
        except Exception as e:
            logger.warning("qdrant scroll failed %s: %s", collection, e)
    prefix = f"{collection}:"
    return [{"id": k[len(prefix):], "text": r["text"], "metadata": r["metadata"]} for k, r in _FALLBACK.items() if k.startswith(prefix)]


def count(collection_name: str | None = None) -> int:
    collection = collection_name or settings.qdrant_legal_collection
    qc = _qdrant()
    if qc is not None:
        try:
            c = qc.count(collection_name=collection)
            return getattr(c, "count", 0)
        except Exception:
            pass
    prefix = f"{collection}:"
    return sum(1 for k in _FALLBACK if k.startswith(prefix))


def reset_for_tests():
    global _FALLBACK, _qdrant_client, _VERSION
    _VERSION += 1
    _FALLBACK.clear()
    qc = _qdrant()
    if qc is not None:
        for coll in [settings.qdrant_legal_collection, settings.qdrant_company_collection, settings.qdrant_collection]:
            try:
                qc.delete_collection(collection_name=coll)
                _ensure_collection(qc, coll)
            except Exception:
                pass
    _qdrant_client = None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
