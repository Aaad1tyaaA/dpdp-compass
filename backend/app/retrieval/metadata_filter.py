"""Metadata filter — exact/structured filtering."""
from app.knowledge_base.metadata_store import filter as meta_filter

async def retrieve(where: dict, top_k: int = 8) -> list[dict]:
    hits = meta_filter(where)[:top_k]
    return [{
        "chunk_id": h.get("chunk_id"),
        "text": h.get("text",""),
        "source_document": h.get("source_document"),
        "section": h.get("section"),
        "clause": h.get("clause"),
        "page": h.get("page"),
        "citation": h.get("citation"),
        "score": 1.0,
        "type": "metadata",
        "metadata": h,
    } for h in hits]
