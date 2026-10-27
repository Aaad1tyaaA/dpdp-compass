"""Policy documents: private to their owner, versioned, and named by every audit that reads them."""
from tests.test_auth import PASSWORD, new_client, signup

POLICY = ("We collect your name, email address and phone number to deliver orders and for no other purpose. "
          "We inform the Data Protection Board and each affected user of any personal data breach.")


def test_documents_are_private_versioned_and_attributed():
    a, b = new_client(), new_client()
    signup(a), signup(b, "Ravi")
    up = a.post("/api/policies/upload", files={"file": ("policy.txt", POLICY.encode(), "text/plain")}).json()
    assert up["version"] == 1 and len(up["versions"][0]["sha256"]) == 64
    pid = up["id"]

    # another user can neither list, read nor audit it
    assert all(p["id"] != pid for p in b.get("/api/policies").json())
    assert b.get(f"/api/policies/{pid}").status_code == 404
    assert b.get(f"/api/policies/{pid}/versions/1").status_code == 404
    assert b.post("/api/compliance/analyze", json={"policy_id": pid}).status_code == 422

    # a new version; identical text does not make another
    v2 = a.post(f"/api/policies/{pid}/versions", json={"text": POLICY + " We keep data for one year.", "note": "retention"}).json()
    assert v2["n"] == 2
    assert a.post(f"/api/policies/{pid}/versions", json={"text": POLICY + " We keep data for one year."}).json()["n"] == 2
    assert a.get(f"/api/policies/{pid}/versions/1").json()["text"] == POLICY

    # an audit names the version it read
    r = a.post("/api/compliance/analyze", json={"policy_id": pid, "version": 1}).json()
    assert r["document"]["id"] == pid and r["document"]["version"] == 1 and r["document"]["sha256"] == up["versions"][0]["sha256"]
    assert a.post("/api/compliance/analyze", json={"policy_id": pid}).json()["document"]["version"] == 2

    # pasted text is saved once and matched on the next audit
    p1 = a.post("/api/compliance/analyze", json={"text": POLICY + " Pasted."}).json()["document"]
    p2 = a.post("/api/compliance/analyze", json={"text": POLICY + " Pasted."}).json()["document"]
    assert p1["id"] == p2["id"] and p1["source"] == "paste"

    # account deletion removes the documents
    from app.api.policies import DOCUMENTS
    owner = DOCUMENTS._db.execute("SELECT owner FROM documents WHERE id = ?", (pid,)).fetchone()[0]
    assert a.post("/api/auth/delete", json={"password": PASSWORD}).status_code == 200
    assert DOCUMENTS._db.execute("SELECT COUNT(*) FROM documents WHERE owner = ?", (owner,)).fetchone()[0] == 0
