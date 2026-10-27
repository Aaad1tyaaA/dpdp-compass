"""Automatic Knowledge Base Indexer.

Indexes the official Gazette DPDP Act, 2023 PDF into `dpdp_legal_kb` (PRIMARY authority),
and indexes all tech company reference privacy policies into `company_policy_kb` (REFERENCE authority).
"""
import hashlib
import logging
import asyncio
from pathlib import Path
from app.config import settings
from app.ingestion.ingestion_service import ingest_document
from app.knowledge_base import vector_store

logger = logging.getLogger(__name__)

# Base paths for legal and reference corpora
def _resolve_data_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "data",
        Path(__file__).resolve().parent.parent.parent / "data",
        Path("../data"),
        Path("data"),
    ]
    for c in candidates:
        if c.exists() and (c / "legal").exists():
            return c
    return candidates[0]

DATA_DIR = _resolve_data_dir()
LEGAL_DIR = DATA_DIR / "legal"
REFERENCE_DIR = DATA_DIR / "company_policies" / "reference"


async def index_legal_corpus() -> dict:
    """Ingests the authentic DPDP Act 2023 PDF into the legal vector & graph knowledge base."""
    legal_files = []
    if LEGAL_DIR.exists():
        legal_files.extend(list(LEGAL_DIR.glob("*.pdf")) + list(LEGAL_DIR.glob("*.txt")))

    indexed = 0
    results = []
    seen_hashes: set[str] = set()
    # Prefer the human-named copy so citations read 'DPDP_Act_2023.pdf', not a hash filename.
    for f in sorted(legal_files, key=lambda f: not f.stem.lower().startswith("dpdp")):
        try:
            content = f.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if digest in seen_hashes:  # data/legal ships a byte-identical copy of the Act
                logger.info("skipping duplicate legal doc: %s", f.name)
                continue
            seen_hashes.add(digest)
            doc_id = f"legal_{f.stem.lower().replace(' ', '_')}"
            res = await ingest_document(
                content=content,
                filename=f.name,
                document_id=doc_id,
                source_type="LEGAL",
                authority_level="PRIMARY",
                source_document=f.name,
            )
            results.append(res)
            indexed += 1
            logger.info("indexed legal doc: %s -> %d chunks", f.name, res.get("chunks", 0))
        except Exception as e:
            logger.error("failed indexing legal doc %s: %s", f.name, e)
            results.append({"filename": f.name, "error": str(e)})

    return {"status": "SUCCESS", "indexed_docs": indexed, "details": results}


async def index_reference_company_policies() -> dict:
    """Ingests tech company reference privacy policies into the company policy knowledge base."""
    policy_files = []
    if REFERENCE_DIR.exists():
        policy_files.extend(list(REFERENCE_DIR.glob("*.txt")) + list(REFERENCE_DIR.glob("*.pdf")))

    indexed = 0
    results = []
    for f in policy_files:
        try:
            content = f.read_bytes()
            company_slug = f.stem.split("_")[0].lower()
            doc_id = f"ref_policy_{company_slug}"
            res = await ingest_document(
                content=content,
                filename=f.name,
                document_id=doc_id,
                company_id=company_slug,
                source_type="POLICY",
                authority_level="REFERENCE",
                source_document=f.name,
            )
            results.append(res)
            indexed += 1
            logger.info("indexed reference company policy: %s -> %d chunks", f.name, res.get("chunks", 0))
        except Exception as e:
            logger.error("failed indexing policy doc %s: %s", f.name, e)
            results.append({"filename": f.name, "error": str(e)})

    return {"status": "SUCCESS", "indexed_policies": indexed, "details": results}


async def initialize_default_knowledge_base(force_reindex: bool = False) -> dict:
    """Initializes and seeds the dual knowledge base if empty or forced."""
    legal_count = vector_store.count(settings.qdrant_legal_collection)
    company_count = vector_store.count(settings.qdrant_company_collection)

    legal_report = {"status": "SKIPPED", "existing_count": legal_count}
    company_report = {"status": "SKIPPED", "existing_count": company_count}

    if force_reindex or legal_count == 0:
        logger.info("Seeding DPDP Act 2023 legal knowledge base...")
        legal_report = await index_legal_corpus()

    if force_reindex or company_count == 0:
        logger.info("Seeding Tech Company reference policies...")
        company_report = await index_reference_company_policies()

    # Warm the cross-encoder now so the first user question doesn't pay its ~2.5s model load.
    try:
        from app.retrieval.reranker import _get_reranker
        from app.services.llm import get_llm
        _get_reranker()
        get_llm()  # build the cached HTTP client once, off the request path
    except Exception as e:
        logger.warning("reranker warm-up skipped: %s", e)

    return {
        "legal_kb": legal_report,
        "company_kb": company_report,
        "total_legal_records": vector_store.count(settings.qdrant_legal_collection),
        "total_company_records": vector_store.count(settings.qdrant_company_collection),
    }


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    res = asyncio.run(initialize_default_knowledge_base(force_reindex=True))
    print("Auto-Indexing Completed:")
    print("Legal Records:", res["total_legal_records"])
    print("Company Records:", res["total_company_records"])
