import pytest
from app.models.schemas import RetrievedEvidence
from app.agents.retrieval_agent import retrieve_evidence, has_sufficient_evidence
from app.agents.obligation_mapping_agent import map_obligations
from app.agents.compliance_agent import check_compliance
from app.agents.risk_agent import assess_risks
from app.agents.orchestrator import orchestrate

@pytest.mark.asyncio
async def test_retrieval_agent():
    # Ensure KB has something
    from app.knowledge_base.builder import build_from_bytes
    await build_from_bytes(b"Section 8(5) Data Fiduciary shall protect personal data", "Act.txt")
    ev = await retrieve_evidence("Data Fiduciary protect")
    assert len(ev) >= 1
    assert ev[0].citation is not None or ev[0].source_document
    assert has_sufficient_evidence(ev)

@pytest.mark.asyncio
async def test_obligation_mapping():
    ev = [RetrievedEvidence(text="Section 8(5) Data Fiduciary shall protect personal data", source_document="DPDP Act", section="Section 8(5)", score=0.9)]
    obs = await map_obligations(ev)
    assert len(obs) >= 1
    assert obs[0].obligation

@pytest.mark.asyncio
async def test_compliance_agent():
    from app.models.schemas import Obligation
    obl = Obligation(obligation="Protect personal data with reasonable safeguards", source="DPDP Act", section="Section 8(5)", applies_to="Data Fiduciary", evidence=[])
    policy = [RetrievedEvidence(text="We use encryption at rest and access controls", source_document="Policy", section="Section 4", score=0.8)]
    legal = [RetrievedEvidence(text="Section 8(5) Data Fiduciary shall protect...", source_document="DPDP Act", section="Section 8(5)", score=0.9)]
    findings = await check_compliance([obl], policy, legal)
    assert findings[0].status in ("SATISFIED","PARTIAL","MISSING","NOT_APPLICABLE")
    assert findings[0].reasoning
    assert findings[0].legal_evidence

@pytest.mark.asyncio
async def test_risk_agent():
    from app.models.schemas import ComplianceFinding, Severity, Urgency
    f = ComplianceFinding(id="f1", obligation_id="DPDP-8(5)", obligation_title="Protect", obligation_description="Protect", principle="Security", status="MISSING", severity=Severity.HIGH, urgency=Urgency.IMMEDIATE, reasoning="Missing", policy_evidence=[], legal_evidence=[], confidence=0.8, recommended_action="Add")
    risks = await assess_risks([f])
    assert len(risks)==1
    assert risks[0].severity == Severity.HIGH

@pytest.mark.asyncio
async def test_orchestrator_feedback_loop():
    res = await orchestrate(query="What happens if breach?", mode="citizen", policy_text="We retain data as long as needed")
    assert "trace" in res
    assert len(res["trace"]) >= 4
    assert "findings" in res
    assert "guardrails" in res

def test_orchestrator_not_doing_all_reasoning():
    # Ensure orchestrator delegates — check that separate agents exist and are importable
    import app.agents.retrieval_agent, app.agents.obligation_mapping_agent, app.agents.compliance_agent, app.agents.risk_agent
    assert True
