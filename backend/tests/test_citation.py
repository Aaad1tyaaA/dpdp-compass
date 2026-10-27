import pytest
from app.guardrails.engine import run_guardrails
from app.models.schemas import ComplianceFinding, Severity, Urgency

def make_finding(status="SATISFIED", has_legal=True, has_policy=True, confidence=0.8):
    leg = [{"citation":{"id":"c1","source_document":"DPDP Act, 2023","section":"Section 8(5)","text":"protect","type":"LEGAL"},"excerpt":"protect","relevance_score":0.9}] if has_legal else []
    pol = [{"citation":{"id":"c2","source_document":"Policy","section":"Sec 2","text":"we protect","type":"POLICY"},"excerpt":"we protect","relevance_score":0.8}] if has_policy else []
    return {"id":"f1","obligation_title":"Protect","status":status,"legal_evidence":leg,"policy_evidence":pol,"confidence":confidence,"severity":"HIGH","reasoning":"test"}

def test_citation_provenance():
    # Every finding must retain source/section/chunk
    f = make_finding()
    guard = run_guardrails([f])
    # Should pass citation exists
    assert any(g["rule"]=="Citation must exist" and g["passed"] for g in guard)

def test_insufficient_evidence_explicit():
    f = make_finding(status="PARTIAL", has_legal=False, has_policy=False)
    guard = run_guardrails([f])
    # Should flag unsupported or citation
    assert any(not g["passed"] for g in guard)

def test_hallucinated_citation():
    f = make_finding()
    f["legal_evidence"][0]["citation"]["source_document"] = "Fake Act 9999"
    guard = run_guardrails([f])
    assert any(g["rule"]=="Hallucinated citation" and not g["passed"] for g in guard)

def test_confidence_range():
    f = make_finding(confidence=1.5)
    guard = run_guardrails([f])
    assert any(g["rule"]=="Confidence 0-1" and not g["passed"] for g in guard)

def test_malformed_output():
    f = {"id":"f1", "status":"SATISFIED"}  # missing required fields
    guard = run_guardrails([f])
    assert any(g["rule"]=="Malformed structured output" and not g["passed"] for g in guard)
