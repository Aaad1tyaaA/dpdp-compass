from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_health(): assert client.get("/health").status_code==200
def test_policies(): assert client.get("/api/policies").status_code==200
def test_compliance_analyze():
    assert client.post("/api/compliance/analyze", json={"policy_id":"pol_none"}).status_code==422  # nothing to audit
    r=client.post("/api/compliance/analyze", json={"policy_id":"pol_1","text":"We encrypt personal data and inform the Data Protection Board of India and every affected user of a breach."})
    body=r.json()
    assert r.status_code==200 and len(body["findings"])==14  # one finding per checklist obligation
    assert all(f["legal_evidence"][0]["citation"]["section"].startswith("Section ") for f in body["findings"])
def test_citizen(): assert client.post("/api/citizen/analyze", json={}).status_code==200
def test_metrics():
    assert client.get("/api/evaluation/ana_missing/metrics").status_code==404
    aid = client.post("/api/compliance/analyze", json={"policy_id":"pol_1","text":"We encrypt data and notify breaches within 72 hours."}).json()["id"]
    r = client.get(f"/api/evaluation/{aid}/metrics")
    assert r.status_code==200 and r.json()


def test_score_ignores_not_applicable():
    from app.api.compliance import _score
    assert _score([{"status": "SATISFIED"}, {"status": "NOT_APPLICABLE"}, {"status": "NOT_APPLICABLE"}]) == 100
