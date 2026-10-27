"""Seed the DPDP Act into dpdp_legal_kb collection."""
import asyncio
import hashlib
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.ingestion.ingestion_service import ingest_document


async def seed_dpdp_act(pdf_path: str | None = None):
    from app.knowledge_base import vector_store
    vector_store.reset_for_tests()

    if pdf_path is None:
        pdf_path = r"C:\Users\Admin\Downloads\2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf"
    p = Path(pdf_path)
    if not p.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        return

    content = p.read_bytes()
    print(f"Read {len(content)} bytes from {p.name}")

    result = await ingest_document(
        content=content,
        filename=p.name,
        document_id="dpdp_act_2023",
        source_type="LEGAL",
        authority_level="PRIMARY",
        source_document="DPDP Act, 2023",
    )

    print("\n=== SEED RESULT ===")
    for k, v in result.items():
        if k == "pages":
            print(f"  {k}: {len(v)} pages")
        else:
            print(f"  {k}: {v}")

    legal_count = vector_store.count(settings.qdrant_legal_collection)
    print(f"\nCollection '{settings.qdrant_legal_collection}': {legal_count} vectors")

    return result


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(seed_dpdp_act(path))
