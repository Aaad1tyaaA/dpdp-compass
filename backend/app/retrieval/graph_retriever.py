"""Graph retriever — traverses triplets, returns provenance-linked evidence."""
from app.knowledge_base.graph_store import traverse

async def retrieve(query: str, top_k: int = 6) -> list[dict]:
    hits = traverse(query, top_k=top_k)
    out=[]
    for h in hits:
        out.append({
            "chunk_id": h.get("source_chunk_id"),
            "text": h.get("evidence",""),
            "source_document": h.get("source_document"),
            "section": h.get("section"),
            "page": h.get("page"),
            "citation": f"{h.get('source_document','')} {h.get('section','')} p.{h.get('page','?')}",
            "score": h.get("score", 0.75),
            "type": "graph",
            "subject": h.get("subject"),
            "predicate": h.get("predicate"),
            "object": h.get("object"),
            "metadata": h,
        })
    return out
