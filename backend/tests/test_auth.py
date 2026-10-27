"""Accounts: sign-up, sign-in, sessions, saved state, and isolation between users."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

PASSWORD = "test-only-" + uuid.uuid4().hex[:12]  # generated per run; never a real credential
ORIGIN = {"origin": "http://localhost:3001"}
POLICY = "We encrypt personal data and inform the Data Protection Board of India and every affected user of a breach."


def new_client() -> TestClient:
    return TestClient(app)


def signup(client: TestClient, name: str = "Asha") -> dict:
    email = f"{uuid.uuid4().hex[:10]}@example.test"
    r = client.post("/api/auth/signup", json={"email": email.upper(), "password": PASSWORD, "name": name})
    assert r.status_code == 200, r.text
    return {"email": email, **r.json()}


def test_signup_signs_in_and_sets_an_http_only_cookie():
    c = new_client()
    user = signup(c)
    assert user["email"].islower() and user["name"] == "Asha"
    cookie = c.cookies.get("compass_session")
    assert cookie and len(cookie) > 30
    assert c.get("/api/auth/me").json()["user"]["email"] == user["email"]
    r = new_client().post("/api/auth/login", json={"email": user["email"], "password": PASSWORD})
    assert "httponly" in r.headers["set-cookie"].lower() and "samesite=lax" in r.headers["set-cookie"].lower()


def test_bad_input_is_rejected():
    c = new_client()
    assert c.post("/api/auth/signup", json={"email": "not-an-email", "password": PASSWORD}).status_code == 422
    assert c.post("/api/auth/signup", json={"email": "a@example.test", "password": "short"}).status_code == 422
    user = signup(c)
    assert new_client().post("/api/auth/signup", json={"email": user["email"], "password": PASSWORD}).status_code == 409


def test_wrong_password_and_unknown_email_give_the_same_answer():
    user = signup(new_client())
    c = new_client()
    wrong = c.post("/api/auth/login", json={"email": user["email"], "password": PASSWORD + "x"})
    unknown = c.post("/api/auth/login", json={"email": "nobody@example.test", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401 and wrong.json() == unknown.json()
    assert c.get("/api/auth/me").json()["user"] is None


def test_repeated_failures_are_throttled():
    user = signup(new_client())
    c = new_client()
    for _ in range(5):
        assert c.post("/api/auth/login", json={"email": user["email"], "password": "wrong-password"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": user["email"], "password": PASSWORD}).status_code == 429


def test_logout_ends_the_session():
    c = new_client()
    signup(c)
    token = c.cookies.get("compass_session")
    assert c.post("/api/auth/logout").status_code == 200
    stale = new_client()
    stale.cookies.set("compass_session", token)
    assert stale.get("/api/auth/me").json()["user"] is None  # the token is gone from the server, not only the browser


def test_saved_state_round_trips_and_is_private_to_the_user():
    a, b = new_client(), new_client()
    signup(a), signup(b)
    assert a.put("/api/me/state/cit.messages", json={"value": [{"role": "user", "text": "नमस्ते"}]}).status_code == 200
    assert a.get("/api/me/state").json() == {"cit.messages": [{"role": "user", "text": "नमस्ते"}]}
    assert b.get("/api/me/state").json() == {}
    assert a.put("/api/me/state/bad key!", json={"value": 1}).status_code == 422
    assert a.put("/api/me/state/big", json={"value": "x" * 1_100_000}).status_code == 413
    assert new_client().get("/api/me/state").status_code == 401


def test_audits_belong_to_the_user_who_ran_them():
    a, b = new_client(), new_client()
    signup(a), signup(b)
    aid = a.post("/api/compliance/analyze", json={"policy_id": "p", "text": POLICY}).json()["id"]
    assert [x["id"] for x in a.get("/api/compliance").json()] == [aid]
    assert b.get("/api/compliance").json() == [] and b.get(f"/api/compliance/{aid}").status_code == 404
    assert a.get(f"/api/compliance/{aid}").status_code == 200


def test_changing_the_password_signs_out_other_sessions():
    first = new_client()
    user = signup(first)
    second = new_client()
    second.post("/api/auth/login", json={"email": user["email"], "password": PASSWORD})
    new_password = PASSWORD + "-changed"
    assert first.post("/api/auth/password", json={"current_password": "wrong", "new_password": new_password}).status_code == 401
    assert first.post("/api/auth/password", json={"current_password": PASSWORD, "new_password": new_password}).status_code == 200
    assert second.get("/api/auth/me").json()["user"] is None and first.get("/api/auth/me").json()["user"]
    assert new_client().post("/api/auth/login", json={"email": user["email"], "password": new_password}).status_code == 200


def test_deleting_the_account_removes_its_data():
    c = new_client()
    user = signup(c)
    c.put("/api/me/state/k", json={"value": 1})
    aid = c.post("/api/compliance/analyze", json={"policy_id": "p", "text": POLICY}).json()["id"]
    assert c.post("/api/auth/delete", json={"password": "wrong"}).status_code == 401
    assert c.post("/api/auth/delete", json={"password": PASSWORD}).status_code == 200
    assert new_client().post("/api/auth/login", json={"email": user["email"], "password": PASSWORD}).status_code == 401
    assert new_client().get(f"/api/compliance/{aid}").status_code == 404


def test_api_requires_sign_in_when_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    anon = new_client()
    assert anon.get("/api/compliance").status_code == 401
    assert anon.post("/api/compass/ask", json={"question": "Who is a child?"}).status_code == 401
    assert anon.get("/health").status_code == 200 and anon.get("/api/auth/me").status_code == 200  # sign-in itself stays open
    c = new_client()
    signup(c)
    assert c.get("/api/compliance").status_code == 200


def test_cross_site_requests_with_a_session_are_refused():
    c = new_client()
    signup(c)
    assert c.put("/api/me/state/k", json={"value": 1}, headers={"origin": "https://evil.example"}).status_code == 403
    assert c.put("/api/me/state/k", json={"value": 1}, headers=ORIGIN).status_code == 200
