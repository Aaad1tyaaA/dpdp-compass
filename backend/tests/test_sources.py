"""Legal source registry: Rules parsing, corrigendum, commencement dates, and Rules retrieval kept out of evaluation."""
from datetime import date

from fastapi.testclient import TestClient

from app.compass import audit as A, qa, sources as S
from app.main import app


def test_rules_parse_all_rules_and_schedules():
    assert [r.n for r in S.rules()] == [*range(1, 24), *[f"Sch{i}" for i in range(1, 8)]]
    r7 = next(r for r in S.rules() if r.n == 7)
    assert r7.title == "Intimation of personal data breach" and "seventy-two hours" in r7.text


def test_corrigendum_applied():
    assert all(c["applied"] for c in S.applied_corrections())
    sch4 = next(r for r in S.rules() if r.n == "Sch4").text
    assert "(g) “mental health establishment”" in sch4 and "(18 of 2013)" in next(r for r in S.rules() if r.n == "Sch1").text


def test_commencement_dates():
    assert S.effective("2(t)") == S.PUBLISHED and S.effective("44(3)") == S.PUBLISHED
    assert S.effective("6(9)") == S.ONE_YEAR and S.effective("27(1)(d)") == S.ONE_YEAR and S.effective("R4") == S.ONE_YEAR
    assert S.effective("8(6)") == S.EIGHTEEN_MONTHS and S.effective("27(1)(a)") == S.EIGHTEEN_MONTHS and S.effective("Sch3") == S.EIGHTEEN_MONTHS
    assert S.status("8(6)", date(2027, 5, 12))["status"] == "Not yet in force"
    assert S.status("8(6)", date(2027, 5, 13))["status"] == "In force"


def test_rules_only_in_live_engine():
    assert not A.get_engine().has_rules and A.get_engine(rules=True).has_rules
    hits, _ = A.get_engine(rules=True).index.search("What does rule 10 require for parental consent?", k=3)
    assert hits[0]["provisions"][0] == "R10"
    assert qa.cited_provisions("see [Rule 7(2)]") == [] and qa.cited_provisions("see [Rule 7(2)]", True) == ["R7(2)"]


def test_sources_endpoint_and_audit_date():
    c = TestClient(app)
    body = c.get("/api/compass/sources", params={"on": "2027-06-01"}).json()
    assert {d["id"] for d in body["documents"]} >= {"dpdp-rules-2025", "dpdp-rules-2025-corrigendum"}
    assert all(o["status"] == "In force" for o in body["obligations"])
    policy = "We collect your name and email address to provide our service and for no other purpose. " * 3
    r = c.post("/api/compass/audit", json={"policy_text": policy, "as_of": "2026-01-01"}).json()
    assert r["assessed_on"] == "2026-01-01" and {f["legal_status"] for f in r["findings"]} == {"Not yet in force"}
