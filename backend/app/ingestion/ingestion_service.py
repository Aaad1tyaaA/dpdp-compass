import hashlib
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from app.config import settings
from app.ingestion.parsers import parse_document
from app.ingestion.clause_chunker import clause_aware_chunk, ClauseChunk
from app.ingestion.metadata_extractor import extract_metadata, ChunkMetadata

logger = logging.getLogger(__name__)


def compute_document_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _store_original(content: bytes, document_id: str, filename: str) -> Path:
    storage = Path(settings.upload_storage_path) / document_id
    storage.mkdir(parents=True, exist_ok=True)
    dest = storage / filename
    dest.write_bytes(content)
    return dest


async def ingest_document(content: bytes, filename: str, document_id: str | None = None,
                          company_id: str | None = None, source_type: str = "LEGAL",
                          authority_level: str = "PRIMARY", source_document: str | None = None) -> dict:
    t0 = time.time()
    doc_id = document_id or f"doc_{uuid.uuid4().hex[:8]}"
    doc_hash = compute_document_hash(content)
    source_type = source_type.upper()
    authority_level = authority_level.upper()
    src_name = source_document or filename
    _store_original(content, doc_id, filename)
    parsed = parse_document(content, filename, doc_id)
    chunks = clause_aware_chunk(
        parsed.raw_text, source_document=src_name,
        document_type=parsed.document_type, authority_level=authority_level,
    )
    metadata_list: list[ChunkMetadata] = []
    texts: list[str] = []
    for i, chunk in enumerate(chunks):
        page_num = chunk.page_number
        meta = extract_metadata(
            chunk_text=chunk.text, chunk_id=chunk.id, source_document=src_name,
            section=chunk.section, clause_id=chunk.clause_id, page_number=page_num,
            document_type=parsed.document_type, authority_level=authority_level,
            language=parsed.metadata.get("language", "en"),
            document_id=doc_id, company_id=company_id, document_hash=doc_hash,
            source_type=source_type,
        )
        metadata_list.append(meta)
        texts.append(chunk.text)
    from app.knowledge_base.embedding_generator import generate_embeddings
    embeddings = generate_embeddings(texts)
    ids = [m.chunk_id for m in metadata_list]
    meta_dicts = [
        {
            "chunk_id": m.chunk_id, "source_document": m.source_document,
            "section": m.section, "subsection": m.subsection, "clause_id": m.clause_id,
            "page_number": m.page_number, "document_type": m.document_type,
            "authority_level": m.authority_level, "language": m.language,
            "entity": m.entity, "obligation_type": m.obligation_type,
            "legal_principle": m.legal_principle, "citation": m.citation,
            "source_type": m.source_type, "document_id": m.document_id,
            "company_id": m.company_id, "document_hash": m.document_hash,
        }
        for m in metadata_list
    ]
    from app.knowledge_base.vector_store import upsert as vector_upsert
    if source_type == "LEGAL":
        collection = settings.qdrant_legal_collection
    else:
        collection = settings.qdrant_company_collection
    vector_upsert(ids, texts, embeddings, meta_dicts, collection_name=collection)
    triplets: list[tuple[str, str, str]] = []
    if settings.enable_knowledge_graph:
        from app.knowledge_base.triplet_extractor import extract_triplets as extract_trip
        for chunk_obj, meta in zip(chunks, metadata_list):
            meta_dict = {
                "source_document": meta.source_document, "section": meta.section,
                "clause_id": meta.clause_id, "page": meta.page_number,
                "source_type": meta.source_type,
            }
            trips = await extract_trip(chunk_obj.text, meta_dict, chunk_obj.id)
            for t in trips:
                triplets.append((t.subject, t.predicate, t.object))
        from app.knowledge_base.graph_store import upsert_triplets
        graph_triplets = [
            type("Triplet", (), {
                "subject": s, "predicate": p, "object": o,
                "source_chunk_id": "", "source_document": filename,
                "section": None, "page": None, "evidence_text": "",
            })()
            for s, p, o in triplets
        ]
        upsert_triplets(graph_triplets)
    duration_ms = int((time.time() - t0) * 1000)
    return {
        "document_id": doc_id, "document_name": filename,
        "document_hash": doc_hash, "document_type": parsed.document_type,
        "total_pages": parsed.total_pages, "total_chars": parsed.total_chars,
        "chunks": len(chunks), "embeddings": len(embeddings),
        "triplets": len(triplets), "vector_count": len(ids),
        "source_type": source_type, "authority_level": authority_level,
        "status": "READY", "duration_ms": duration_ms,
        "pages": [{"page_number": p.page_number, "char_count": len(p.text)} for p in parsed.pages],
    }
