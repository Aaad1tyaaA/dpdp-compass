"""Redline -> new version -> re-audit on the same terms -> comparison of findings and text."""
from fastapi.testclient import TestClient

from app.main import app

POLICY = ("We collect your name, phone number and delivery address to deliver groceries. "
          "We protect data with encryption and access controls. Contact us at help@kirana.example.")


def test_redline_accept_creates_version_reaudits_and_compares():
    c = TestClient(app)
    a = c.post("/api/compliance/analyze", json={"text": POLICY, "applicability": {"children": "no"}}).json()
    breach = next(f for f in a["findings"] if f["obligation_id"] == "BREACH")
    assert breach["status"] != "SATISFIED"

    p = c.post(f"/api/compliance/{a['id']}/findings/{breach['id']}/redline").json()
    assert p["mode"] == "insert" and "72 hours" in p["proposed"] and p["document"]["version"] == 1

    r = c.post(f"/api/compliance/{a['id']}/findings/{breach['id']}/redline/accept", json=p).json()
    new, cmp = r["analysis"], r["comparison"]
    assert new["document"]["version"] == 2 and new["applicability"]["answers"]["children"] == "no"
    assert cmp["comparable"] and any(t["op"] == "added" and "72 hours" in t["b"] for t in cmp["text_changes"])
    assert any(ch["obligation_id"] == "BREACH" and ch["change"] == "improved" for ch in cmp["changes"])

    # the old audit's span is stale once version 2 exists
    assert c.post(f"/api/compliance/{a['id']}/findings/{breach['id']}/redline/accept", json=p).status_code == 409
    v = c.get(f"/api/policies/{new['document']['id']}/compare/1/2").json()
    assert v["changes"][0]["op"] == "added"
    assert c.get(f"/api/compliance/{a['id']}").json()["activity"][0]["decision"] == "redline_accepted"


def test_reference_policy_cannot_be_redlined():
    c = TestClient(app)
    a = c.post("/api/compliance/analyze", json={"reference_company": "Zomato"}).json()
    assert c.post(f"/api/compliance/{a['id']}/findings/{a['findings'][0]['id']}/redline").status_code == 422
