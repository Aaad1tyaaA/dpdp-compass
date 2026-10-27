import pytest
from app.knowledge_base.builder import build_from_bytes
from app.retrieval.hybrid_retriever import hybrid_retrieve
from app.knowledge_base import vector_store, metadata_store, graph_store

@pytest.mark.asyncio
async def test_hybrid_retrieval_provenance():
    vector_store.reset_for_tests(); metadata_store.reset_for_tests(); graph_store.reset_for_tests()
    await build_from_bytes(b"Section 6 Notice: Data Fiduciary must provide clear notice before collection", "DPDP_Act.txt")
    hits = await hybrid_retrieve("notice before collection")
    assert len(hits)>=1
    h=hits[0]
    assert h.get("source_document")
    assert h.get("section")
    assert h.get("citation")
    assert h.get("chunk_id")
    assert "score" in h

@pytest.mark.asyncio
async def test_metadata_filter():
    vector_store.reset_for_tests(); metadata_store.reset_for_tests(); graph_store.reset_for_tests()
    await build_from_bytes(b"Section 8(5) security safeguards", "Act.txt")
    from app.retrieval.metadata_filter import retrieve as meta_retrieve
    hits = await meta_retrieve({"section": "Section 8"})
    # May be 0 or more depending on metadata extraction, but should not error
    assert isinstance(hits, list)

def test_vector_store_citation():
    vector_store.reset_for_tests()
    from app.knowledge_base.embedding_generator import generate_embeddings
    embs = generate_embeddings(["Data Fiduciary must protect"])
    vector_store.upsert(["id1"], ["Data Fiduciary must protect"], embs, [{"source_document":"Act.txt","section":"Section 8(5)","citation":"Act.txt Section 8(5) p.1","chunk_id":"id1"}])
    # Query
    qemb = generate_embeddings(["protect personal data"])[0]
    res = vector_store.query(qemb, top_k=2)
    assert res[0].get("citation") or res[0]["metadata"].get("citation")
