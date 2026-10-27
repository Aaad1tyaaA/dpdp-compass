"""Claim checks on answers and conflicting clauses in policies, through the API."""
from fastapi.testclient import TestClient

from app.compass import claims
from app.main import app

CONFLICTED = ("We collect your name and email to deliver orders. We do not share your data with third parties. "
              "We may share your information with advertising partners to show offers. By using the app you consent to this policy.")


def test_audit_reports_conflicting_clauses_on_the_finding():
    a = TestClient(app).post("/api/compliance/analyze", json={"text": CONFLICTED}).json()
    assert [c["topic"] for c in a["conflicts"]] == ["sharing"]
    proc = next(f for f in a["findings"] if f["obligation_id"] == "PROCESSOR")
    assert proc["support"] == "conflicting" and proc["conflicts"][0]["a"]["span"][0] == CONFLICTED.index("We do not share") + 3


def test_citizen_answer_carries_a_claim_check():
    r = TestClient(app).post("/api/citizen/analyze", json={"text": "How fast must a company report a data breach?"}).json()
    assert set(r["claim_check"]["counts"]) == {"supported", "uncertain", "absent", "contradicted"}


def test_unsupported_number_is_flagged():
    out = claims.check("Deleted data must be erased within 30 days.", ["Personal data shall be erased within 48 hours of notice."])
    assert out["claims"][0]["status"] in ("contradicted", "uncertain", "absent")


def test_rights_request_letter_uses_the_policy_contact():
    c = TestClient(app)
    assert [t["id"] for t in c.get("/api/citizen/requests/types").json()][:2] == ["access", "correct"]
    d = c.post("/api/citizen/requests/draft", json={"type": "erase", "company": "Zomato", "name": "Asha Rao", "details": "My old delivery addresses"}).json()
    assert d["to"] == "grievance.officer@zomato.com" and "Asha Rao" in d["letter"] and "section 12(3)" in d["letter"]
    assert d["contact"]["context"] and any("not legal advice" in n for n in d["notes"])
    other = c.post("/api/citizen/requests/draft", json={"type": "access", "company": "Some Unknown Shop"}).json()
    assert other["to"].startswith("[") and other["contact"] is None
    assert c.post("/api/citizen/requests/draft", json={"type": "sue", "company": "Zomato"}).status_code == 422


def test_policy_generator_asks_for_more_then_drafts_with_placeholders():
    c = TestClient(app)
    thin = {"company": "Acme", "sector": "Fintech", "data": "user data", "purpose": "business purposes", "sharing": "Razorpay (payments)",
            "retention": "7 years (RBI)", "children": "No, 18+ only", "contact": "dpo@acme.in", "dpo_name": "Priya Rao",
            "grievance_days": "30", "security": "AES-256 encryption, access control", "consent_method": "Ticking an unticked box at sign-up",
            "withdraw_method": "Settings > Privacy > Withdraw consent", "website": "https://acme.in/privacy", "service": "A mobile app for UPI payments"}
    r = c.post("/api/policies/generate", json=thin).json()
    assert r["needs_more"] and r["draft"] is None and {q["field"] for q in r["questions"]} == {"data", "purpose"}
    assert all(q["why"] for q in r["questions"]) and r["recommendations"]
    d = c.post("/api/policies/generate", json={**thin, "proceed": True}).json()
    assert d["draft"] and "[list each item of personal data you collect]" in d["placeholders"] and d["drafted_with_gaps"] == ["data", "purpose"]
    assert "user data" not in d["draft"] and "72 hours" in d["draft"] and "+91-80-XXXX" not in d["draft"]


def test_complete_generated_policy_passes_its_own_audit():
    from app.compass import adapter, workflow
    c = TestClient(app)
    facts = {"company": "Acme Payments Pvt Ltd", "sector": "Fintech", "data": "Name, mobile number, PAN, bank account number",
             "purpose": "Process payments, verify identity (KYC), prevent fraud", "sharing": "Razorpay (payments), AWS Mumbai (hosting)",
             "retention": "KYC records 5 years after account closure (PMLA); logs 12 months", "children": "No, users must be 18 or over",
             "contact": "dpo@acme.in", "dpo_name": "Priya Rao", "grievance_days": "30", "security": "AES-256 encryption, access control",
             "consent_method": "Ticking an unticked box at sign-up", "withdraw_method": "Settings > Privacy > Withdraw consent",
             "website": "https://acme.in/privacy", "service": "A mobile app for UPI payments and bill payments"}
    d = c.post("/api/policies/generate", json=facts).json()
    assert d["draft"] and not d["placeholders"] and all(r["met"] for r in d["rulebook"]) and d["policy_id"]
    report = workflow.run("", d["draft"], None)
    assert report["counts"]["Satisfied"] == 14 and not report["conflicts"], report["counts"]
    weak = adapter.findings(workflow.run("", "We collect your name for business purposes. By using our app you agree. " * 3, None), "weak")
    assert all(f["fixes"] and f["suggested_rewrite"] for f in weak if f["status"] != "SATISFIED")


def test_draft_with_placeholders_is_never_fully_satisfied():
    from app.api.policies import PLACEHOLDERS
    from app.compass import rulebook, workflow
    gaps = {**rulebook.FACTS_EXAMPLE, **{k: PLACEHOLDERS[k] for k in ("dpo_name", "grievance_days", "security")}}
    report = workflow.run("", rulebook.draft(gaps), None)
    flagged = {f["id"] for f in report["findings"] if f["status"] != "Satisfied"}
    assert {"CONTACT", "GRIEVANCE", "SECURITY"} <= flagged and report["score"] < 100
    assert all(f["quote"] for f in report["findings"] if f["status"] == "Satisfied")
