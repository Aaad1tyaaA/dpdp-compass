"""Offline KB builder — Document → chunks → metadata → triplets → embeddings → Hybrid stores → 3 layers.
Supports directory input (Windows-safe glob): python -m app.knowledge_base.builder ..\\data\\legal
"""
import logging
import time
from dataclasses import asdict
from pathlib import Path
from app.ingestion.document_loader import RawDocument, load_from_bytes
from app.ingestion.parser import normalize
from app.ingestion.chunker import clause_aware_chunk
from app.ingestion.metadata_extractor import extract_metadata
from app.knowledge_base.triplet_extractor import extract_triplets
from app.knowledge_base.embedding_generator import generate_embeddings
from app.knowledge_base import vector_store, graph_store, metadata_store

logger = logging.getLogger(__name__)

SUPPORTED = {".pdf", ".txt", ".md", ".docx"}

def discover_files(inputs: list[str]) -> list[Path]:
    """Windows-safe: expand directories via glob internally (no shell wildcard needed)."""
    out: list[Path] = []
    for inp in inputs:
        p = Path(inp)
        if p.is_dir():
            for ext in SUPPORTED:
                out.extend(sorted(p.glob(f"*{ext}")))
        elif p.is_file():
            if p.suffix.lower() in SUPPORTED:
                out.append(p)
            else:
                logger.warning("builder skip unsupported %s", p)
        else:
            # Try glob pattern as-is
            for m in sorted(Path(".").glob(inp)):
                if m.is_file() and m.suffix.lower() in SUPPORTED:
                    out.append(m)
    # Dedupe
    seen: dict[str, Path] = {}
    for f in out:
        seen[str(f.resolve())] = f
    return list(seen.values())

async def build_from_document(doc: RawDocument) -> dict:
    t0 = time.time()
    text = normalize(doc.text)
    if not text.strip():
        logger.warning("builder empty extraction %s — possible scanned PDF needing OCR", doc.source_document)
        return {"doc_id": doc.doc_id, "chunks": 0, "triplets": 0, "embeddings": 0, "error": "empty extraction (OCR may be required)", "duration_ms": 0}
    chunks = clause_aware_chunk(text)
    logger.info("builder chunks %s n=%d", doc.source_document, len(chunks))
    doc_type = "legal" if "dpdp" in doc.source_document.lower() or "act" in doc.source_document.lower() else "policy"
    authority = "PRIMARY" if doc_type == "legal" else "REFERENCE"
    metadatas, texts = [], []
    for c in chunks:
        meta = extract_metadata(
            chunk_text=c.text, chunk_id=c.id, source_document=doc.source_document,
            section=c.section, clause_id=c.clause, page_number=None,
            document_type=doc_type, authority_level=authority,
            document_id=doc.doc_id,
        )
        metadatas.append(asdict(meta))
        texts.append(c.text)
    all_triplets = []
    for c, m in zip(chunks, metadatas):
        trips = await extract_triplets(c.text, m, c.id)
        all_triplets.extend(trips)
    embs = generate_embeddings(texts)
    ids = [m["chunk_id"] for m in metadatas]
    vector_store.upsert(ids, texts, embs, metadatas)
    graph_store.upsert_triplets(all_triplets)
    metadata_store.upsert(metadatas, texts)
    from app.ingestion.chunker import build_knowledge_layers
    layers = build_knowledge_layers(chunks)
    return {"doc_id": doc.doc_id, "chunks": len(chunks), "embeddings": len(embs), "triplets": len(all_triplets),
            "layers": layers, "vector_count": vector_store.count(), "duration_ms": int((time.time()-t0)*1000)}

async def build_from_bytes(content: bytes, filename: str) -> dict:
    doc = load_from_bytes(content, filename)
    return await build_from_document(doc)

async def build_from_paths(paths: list[Path]) -> dict:
    t0 = time.time()
    docs = len(paths); chunks = 0; embs = 0; trips = 0; vecs = 0; graphs = 0; fails = 0
    per_doc = []
    for p in paths:
        try:
            r = await build_from_bytes(p.read_bytes(), p.name)
            if r.get("error"):
                fails += 1
            chunks += r.get("chunks", 0); embs += r.get("embeddings", 0); trips += r.get("triplets", 0)
            per_doc.append({"file": p.name, **{k: v for k, v in r.items() if k != "layers"}})
        except Exception as e:
            logger.warning("builder failed %s: %s", p, e)
            fails += 1
            per_doc.append({"file": p.name, "error": str(e)[:200]})
    try:
        vecs = vector_store.count()
    except Exception:
        vecs = chunks
    try:
        from app.knowledge_base.graph_store import _FALLBACK_TRIPLETS
        graphs = len(_FALLBACK_TRIPLETS)
    except Exception:
        graphs = trips
    report = {"documents": docs, "chunks": chunks, "embeddings": embs, "vector_records": vecs,
              "triplets": trips, "graph_relationships": graphs, "failures": fails,
              "duration_ms": int((time.time()-t0)*1000), "per_doc": per_doc}
    logger.info("ingestion report %s", report)
    return report

if __name__ == "__main__":
    import sys, asyncio
    async def _run():
        files = discover_files(sys.argv[1:] or ["data/legal"])
        print(f"Discovered {len(files)} files: {[f.name for f in files]}")
        report = await build_from_paths(files)
        print(f"Documents processed: {report['documents']}")
        print(f"Chunks created: {report['chunks']}")
        print(f"Embeddings generated: {report['embeddings']}")
        print(f"Vector records: {report['vector_records']}")
        print(f"Triplets extracted: {report['triplets']}")
        print(f"Graph relationships: {report['graph_relationships']}")
        print(f"Failures: {report['failures']}")
    asyncio.run(_run())
