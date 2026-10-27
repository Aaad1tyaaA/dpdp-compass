from app.guardrails.engine import run_guardrails

def test_citation_guardrail_blocks_unsupported():
    findings=[{"id":"f1","status":"PARTIAL","policy_evidence":[],"legal_evidence":[]}]
    results=run_guardrails(findings)
    assert any(not r["passed"] for r in results)

def test_missing_no_citation_allowed():
    findings=[{"id":"f2","status":"MISSING","policy_evidence":[],"legal_evidence":[{"citation":{"id":"c1"}}]}]
    results=run_guardrails(findings)
    # MISSING may have no policy evidence but must have legal
    assert any(r["passed"] for r in results)

def test_high_risk_insufficient_evidence():
    findings=[{"id":"f2","status":"MISSING","policy_evidence":[],"legal_evidence":[{"relevance_score":0.5}]}]
    results=run_guardrails(findings)
    assert len(results)>0
