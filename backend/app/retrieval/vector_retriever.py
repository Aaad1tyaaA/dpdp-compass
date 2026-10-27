from app.knowledge_base.embedding_generator import generate_embeddings
from app.knowledge_base import vector_store
from app.config import settings


async def retrieve(query: str, top_k: int | None = None, where: dict | None = None,
                   collection_name: str | None = None) -> list[dict]:
    k = top_k or settings.top_k
    collection = collection_name or settings.qdrant_legal_collection
    emb = generate_embeddings([query])[0]
    hits = vector_store.query(emb, top_k=k, where=where, collection_name=collection)
    out = []
    for h in hits:
        meta = h.get("metadata", {})
        out.append({
            "chunk_id": h.get("id"),
            "text": h.get("text", ""),
            "source_document": meta.get("source_document"),
            "section": meta.get("section"),
            "clause_id": meta.get("clause_id"),
            "page_number": meta.get("page_number"),
            "citation": meta.get("citation"),
            "score": h.get("score", 0),
            "type": "vector",
            "metadata": meta,
        })
    return out
