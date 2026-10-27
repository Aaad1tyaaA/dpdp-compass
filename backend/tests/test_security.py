from fastapi.testclient import TestClient
from app import main
from app.api.citizen import _extract_practices, _reference_policy_for

client = TestClient(main.app)


def test_ssrf_blocks_private_addresses():
    for url in ["http://169.254.169.254/latest/meta-data/", "http://127.0.0.1:8000/health", "http://10.0.0.1/"]:
        assert client.post("/api/documents/ingest-url", json={"url": url}).status_code == 400


def test_upload_rejects_disallowed_extension():
    r = client.post("/api/policies/upload", files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 415


def test_rate_limit_and_api_key(monkeypatch):
    monkeypatch.setattr(main, "_RATE_LIMIT_PER_MIN", 2)
    monkeypatch.setattr(main, "_hits", main.defaultdict(list))
    body = {"text": "We collect your email and encrypt it with TLS. Contact our grievance officer at dpo@x.com."}
    codes = [client.post("/api/citizen/compare-similarity", json=body).status_code for _ in range(3)]
    assert codes[-1] == 429 and 429 not in codes[:2]
    monkeypatch.setattr(main, "_hits", main.defaultdict(list))
    monkeypatch.setattr(main, "_API_KEY", "s3cret")
    assert client.post("/api/citizen/compare-similarity", json=body).status_code == 401
    assert client.post("/api/citizen/compare-similarity", json=body, headers={"x-api-key": "s3cret"}).status_code == 200


def test_citizen_practices_come_from_policy_text():
    p = _extract_practices("We collect your name and phone number. We share data with payment partners. We retain records for 7 years.")
    assert "name and phone" in p["data_collected"][0]
    assert "payment partners" in p["sharing"]
    assert "7 years" in p["retention"]
    assert _reference_policy_for("What does Zomato do with my data?")[0].lower().startswith("zomato")
    assert _reference_policy_for("Can they sell my phone number?") is None


def test_citizen_general_question_has_no_trust_score():
    j = client.post("/api/citizen/analyze", json={"text": "Can they sell my phone number?"}).json()
    assert j["trust_score"] is None and j["policy_analyzed"] is False


def test_too_short_text_is_client_error():
    assert client.post("/api/citizen/compare-similarity", json={"text": "hello"}).status_code == 422


def test_benchmark_scan_uses_real_reference_policy():
    r = client.post("/api/citizen/compare-similarity", json={"reference_company": "Zomato", "filename": "Zomato_Privacy_Policy.txt"})
    assert r.status_code == 200 and r.json()["total_characters"] > 500
    assert client.post("/api/citizen/compare-similarity", json={"reference_company": "Nope"}).status_code == 404


def test_reference_companies_and_sample_audit():
    names = client.get("/api/citizen/reference-companies").json()
    assert "Zomato" in names and len(names) >= 5
    a = client.post("/api/compliance/analyze", json={"reference_company": "Zomato"}).json()
    assert a["policy_name"].startswith("Zomato") and a["policy_id"] == "ref_zomato" and a["findings"]


def test_repeat_citizen_question_is_cached():
    from app.api import citizen
    citizen._ANSWER_CACHE.clear()
    body = {"text": "What   are my RIGHTS under DPDP?"}
    first = client.post("/api/citizen/analyze", json=body).json()
    again = client.post("/api/citizen/analyze", json={"text": "what are my rights under dpdp"}).json()
    assert not first.get("cached") and again.get("cached") and again["summary"] == first["summary"]
    other = client.post("/api/citizen/analyze", json={"text": "what are my rights under dpdp?", "policy_text": "We collect email for support purposes only."}).json()
    assert not other.get("cached")  # different policy -> different cache entry


def _sse(resp):
    import json
    return [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]


def test_citizen_stream_matches_analyze_and_caches():
    from app.api import citizen
    citizen._ANSWER_CACHE.clear()
    r = client.post("/api/citizen/analyze/stream", json={"text": "Can a company sell my phone number without consent?"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    ev = _sse(r)
    assert ev[0]["type"] == "status" and ev[-1]["type"] == "done"
    streamed = "".join(e["text"] for e in ev if e["type"] == "token")
    done = ev[-1]["data"]
    assert streamed and done["summary"] == streamed and "_answer_state" not in done
    assert done["citations"] and done["guardrails"] and done["trust_score"] is None
    again = _sse(client.post("/api/citizen/analyze/stream", json={"text": "can a company sell my phone number without consent"}))
    assert again[-1]["data"]["cached"] and again[-1]["data"]["summary"] == streamed
