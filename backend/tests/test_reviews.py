"""Reviewer decisions sit beside the model's findings: append-only, attributed, and guarded against concurrent edits."""
from fastapi.testclient import TestClient

from app.main import app

POLICY = "We collect your name and email to deliver orders. We inform the Data Protection Board and affected users of a breach."


def test_review_trail_override_and_conflict():
    c = TestClient(app)
    a = c.post("/api/compliance/analyze", json={"text": POLICY}).json()
    assert a["review_rev"] == 0 and a["reviewed_score"] is None
    f1, f2 = a["findings"][0]["id"], a["findings"][1]["id"]
    url = f"/api/compliance/{a['id']}/findings"

    assert c.post(f"{url}/{f1}/review", json={"decision": "override", "status": "SATISFIED", "rev": 0}).status_code == 422  # needs a reason
    r = c.post(f"{url}/{f1}/review", json={"decision": "override", "status": "SATISFIED", "note": "Clause 4 covers it.", "rev": 0}).json()
    assert r["review_rev"] == 1 and r["findings"][0]["review"]["status"] == "SATISFIED" and r["reviewed_count"] == 1
    assert r["findings"][0]["status"] == a["findings"][0]["status"]  # the model's verdict is kept

    stale = c.post(f"{url}/{f2}/review", json={"decision": "accept", "rev": 0})
    assert stale.status_code == 409
    r = c.post(f"{url}/{f2}/review", json={"decision": "accept", "rev": 1}).json()
    r = c.post(f"{url}/{f1}/review", json={"decision": "clear", "rev": 2}).json()
    assert r["findings"][0]["review"] is None and r["reviewed_count"] == 1 and len(r["activity"]) == 3
    assert c.get(f"/api/compliance/{a['id']}").json()["review_rev"] == 3
