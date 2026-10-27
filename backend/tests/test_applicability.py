"""Applicability answers narrow the checklist only on facts the Act makes conditional; notified exemptions are never granted."""
from fastapi.testclient import TestClient

from app.main import app

POLICY = ("We collect your name, email address and delivery address to deliver orders. We share data with delivery partners "
          "under contract. We inform the Data Protection Board and affected users of any breach.")


def _audit(answers: dict) -> dict:
    return TestClient(app).post("/api/compliance/analyze", json={"text": POLICY, "applicability": answers}).json()


def test_answers_mark_obligations_not_applicable_and_score_excludes_them():
    base = _audit({})
    r = _audit({"children": "no", "grounds": "legitimate_use"})
    na = {f["obligation_id"] for f in r["findings"] if f["status"] == "NOT_APPLICABLE"}
    assert na == {"CHILDREN", "NOTICE", "CONSENT", "LANGUAGE", "WITHDRAWAL"}
    assert all(f["reasoning"].startswith("Not applicable to you") and not f["applies"] for f in r["findings"] if f["status"] == "NOT_APPLICABLE")
    assert r["status_counts"]["NOT_APPLICABLE"] == 5 and r["applicability"]["answers"]["children"] == "no"
    assert r["overall_score"] != base["overall_score"] or all(f["status"] != "NOT_APPLICABLE" for f in base["findings"])


def test_notified_exemption_is_a_note_not_an_exemption():
    r = _audit({"notified": "startup"})
    assert all(f["status"] != "NOT_APPLICABLE" for f in r["findings"])
    assert any("17(3)" in n for n in r["applicability"]["notes"])


def test_questions_endpoint():
    qs = TestClient(app).get("/api/compass/applicability").json()
    assert [q["id"] for q in qs] == ["role", "grounds", "children", "notified"] and all(q["options"] for q in qs)
