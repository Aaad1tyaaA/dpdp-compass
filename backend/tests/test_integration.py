"""End-to-end business + citizen workflows, missing evidence, malformed LLM."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.knowledge_base import vector_store, graph_store, metadata_store

client = TestClient(app)

def test_health_and_version():
    assert client.get("/health").status_code == 200
    assert client.get("/api/version").status_code == 200
    assert client.get("/health").json()["status"] == "ok"

def test_citizen_workflow_e2e():
    # Complete citizen QA — no upload
    r = client.post("/api/citizen/analyze", json={"text": "What does Zomato do with my data?"})
    assert r.status_code == 200
    j=r.json()
    assert "summary" in j
    assert "citations" in j
    assert "trust_score" in j
    assert len(j["citations"]) >=1
    # Check GET policy/{id} still works
    assert client.get("/api/citizen/policy/test123").status_code == 404
    pid = client.post("/api/policies/upload", files={"file": ("acme.txt", b"We collect your email. You can withdraw consent in Settings. Contact dpo@acme.in.", "text/plain")}).json()["id"]
    r2 = client.get(f"/api/citizen/policy/{pid}")
    assert r2.status_code == 200
    assert "summary" in r2.json()

def test_business_workflow_e2e():
    r = client.post("/api/compliance/analyze", json={"policy_id":"pol_1", "text":"We retain data as long as needed. We will notify breach within 72h."})
    assert r.status_code == 200
    j=r.json()
    assert "findings" in j
    assert "agent_trace" in j
    assert "guardrail_results" in j
    assert j["overall_score"] >=0

def test_missing_evidence_explicit():
    # Query with nonsense — retrieval insufficient, orchestrator should flag
    from app.agents.orchestrator import orchestrate
    import asyncio
    vector_store.reset_for_tests(); graph_store.reset_for_tests(); metadata_store.reset_for_tests()
    # Empty KB → insufficient
    res = asyncio.run(orchestrate(query="nonexistent obligation xyz123", mode="citizen", policy_text=""))
    # Should still return but with trace indicating insufficient or findings fallback
    assert "findings" in res
    # Guardrails should have at least one check
    assert len(res["guardrails"]) >= 1

def test_malformed_llm_output_handling(monkeypatch):
    # Simulate LLM returning bad JSON — agent should fallback to heuristic
    from app.agents import obligation_mapping_agent
    import app.services.llm as llm_mod
    class BadLLM:
        async def complete(self, prompt, system=None): return "THIS IS NOT JSON [["
    monkeypatch.setattr(llm_mod, "get_llm", lambda: BadLLM())
    # Force non-mock
    from app.config import settings
    orig_mock = settings.mock_llm
    orig_key = settings.llm_api_key
    settings.mock_llm = False
    from pydantic import SecretStr
    settings.llm_api_key = SecretStr("dummy")
    try:
        from app.models.schemas import RetrievedEvidence
        import asyncio
        ev = [RetrievedEvidence(text="Section 8(5) protect", source_document="DPDP Act", section="Section 8(5)", score=0.9)]
        res = asyncio.run(obligation_mapping_agent.map_obligations(ev))
        assert len(res) >= 1
    finally:
        settings.mock_llm = orig_mock
        settings.llm_api_key = orig_key

def test_ingestion_pipeline():
    # Offline builder
    import asyncio
    from app.knowledge_base.builder import build_from_bytes
    vector_store.reset_for_tests(); graph_store.reset_for_tests(); metadata_store.reset_for_tests()
    res = asyncio.run(build_from_bytes(b"Section 8(5) Data Fiduciary shall protect personal data\nSection 8(6) breach notice", "DPDP_test.txt"))
    assert res["chunks"] == 2
    assert res["triplets"] >= 1
    assert res["vector_count"] >= 2

def test_api_integration_policies_generate_missing_fields():
    r = client.post("/api/policies/generate", json={"company":""})
    assert r.status_code == 200
    assert "missing_fields" in r.json()
    r2 = client.post("/api/policies/generate", json={"company":"TestPay","data":"name, phone, email, PAN of users","purpose":"payments and fraud checks","sharing":"Razorpay, AWS Mumbai","retention":"payments 7y","children":"no child users","contact":"dpo@testpay.com",
        "dpo_name":"A. Shah","grievance_days":"30","security":"encryption at rest, access control","consent_method":"Ticking an unticked box at sign-up",
        "withdraw_method":"Settings > Privacy > Withdraw consent","website":"https://testpay.com/privacy","service":"A payments app for small shops"})
    assert r2.status_code == 200
    assert r2.json().get("draft") is not None
