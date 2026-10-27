"""The rule book: what a privacy policy must say for each checklist obligation, applied the same way to a policy we
draft and to a policy we audit.

The rules live in rulebook.json (requirement, legal basis, fix, and the tests), so a rule can be added or tightened
without touching code; run `python -m app.compass.rulebook` after an edit. A policy meets an obligation when one of its
sections passes every requirement. draft() writes one section per obligation from the business's answers, so a complete
draft passes check() by construction; the generator refuses any AI rewrite that does not, and the audit counts an
obligation as Satisfied when the rule book finds it met. Rule-based: no model.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from .intake import _DURATION, _EMAIL, _NONE, _PHONE
from .redline import MODEL_CLAUSES

PLACEHOLDER = re.compile(r"\[[^\]\n]{3,120}\](?!\()")  # [fill me], not a markdown link


def _max_90_days(sec: str) -> bool:
    days = re.findall(r"within\s+(?:[a-z-]+\s+)?\(?(\d{1,4})\)?\s+(?:calendar\s+|working\s+|business\s+)?days", sec, re.I)
    return bool(days) and all(int(d) <= 90 for d in days)


# Named tests a JSON rule can use with "check" (anything a regex cannot say).
CHECKS = {"max_90_days": _max_90_days, "email_or_phone": lambda s: bool(_EMAIL.search(s) or _PHONE.search(s)),
          "retention_period": lambda s: bool(_DURATION.search(s))}


def _compile(r: dict):
    match = re.compile(r["match"], re.I) if "match" in r else None
    absent = re.compile(r["absent"], re.I) if "absent" in r else None
    named = CHECKS[r["check"]] if "check" in r else None
    whole = r.get("scope") == "policy"

    def test(sec: str, doc: str) -> bool:
        target = doc if whole else sec
        return ((match is None or bool(match.search(target))) and (absent is None or not absent.search(target))
                and (named is None or named(target)))
    return test


def load(path: Path = Path(__file__).with_name("rulebook.json")) -> dict[str, list[tuple]]:
    """id -> [(requirement, test(section, policy), fix, basis)]"""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {oid: [(r["rule"], _compile(r), r["fix"], r["basis"]) for r in reqs] for oid, reqs in raw.items() if not oid.startswith("_")}


def _hard(path: Path = Path(__file__).with_name("rulebook.json")) -> set[str]:
    """Requirements whose failure is a definite flaw, not a wording gap: every 'absent' rule, and any marked "hard": true."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {r["rule"] for k, reqs in raw.items() if not k.startswith("_") for r in reqs if "absent" in r or r.get("hard")}


RULES = load()
NO_PLACEHOLDER = ("No unfilled [placeholders]", lambda sec, doc: not PLACEHOLDER.search(sec), "Replace each [bracketed] item with your actual details before publishing.", "")
HARD = _hard() | {NO_PLACEHOLDER[0]}


def sections(text: str) -> list[str]:
    """Markdown sections when the policy has headings; otherwise each run of three paragraphs."""
    parts = [p.strip() for p in re.split(r"\n(?=\s{0,3}#{1,6}\s)", text) if p.strip()]
    if len(parts) >= 4:
        return parts
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    # ponytail: fixed 3-paragraph windows stand in for heading detection in plain-text policies
    return ["\n\n".join(paras[i:i + 3]) for i in range(max(1, len(paras) - 2))] or [text]


def _sentence(sec: str, test) -> str:
    """The first full sentence (not a heading) that passes the test, as the quote shown with the finding."""
    hits = [s for s in (p.strip().strip("#-* ").strip() for p in re.split(r"(?<=[.!?])\s+|\n+", sec)) if len(s) > 12 and test(s, s)]
    return next((s for s in hits if len(s.split()) >= 6), hits[0] if hits else "")


def _best(secs: list[str], reqs: list[tuple], text: str) -> str:
    """The section that says most of what the obligation needs; the no-flaw (hard) rules only break ties."""
    return max(secs, key=lambda s: (sum(r[1](s, text) for r in reqs if r[0] not in HARD),
                                    sum(r[1](s, text) for r in reqs if r[0] in HARD), -len(s)))


def best_sections(text: str) -> dict[str, str]:
    """For every obligation, the policy section that meets most of its requirements (retrieval hint for the judge)."""
    secs = sections(text)
    return {oid: _best(secs, reqs, text) for oid, reqs in RULES.items()}


def check(text: str) -> dict[str, dict]:
    """For every obligation: met or not, each requirement with its basis and fix, a quote from the section that meets it, and model wording."""
    secs, out = sections(text), {}
    for oid, reqs in RULES.items():
        reqs = reqs + [NO_PLACEHOLDER]
        best = _best(secs, reqs, text)
        checks = [{"rule": r, "passed": t(best, text), "fix": fix, "basis": basis, "hard": r in HARD} for r, t, fix, basis in reqs]
        met = all(c["passed"] for c in checks)
        out[oid] = {"met": met, "checks": checks, "quote": _sentence(best, reqs[0][1]) if met else "", "example": MODEL_CLAUSES[oid]}
    return out


def reconcile(findings: list[dict], policy: str) -> None:
    """Audit side: attach the rule-book checks and fixes. An obligation the rule book finds met is Satisfied, quoted from the
    policy; one with a hard flaw (an unfilled placeholder, or wording a rule forbids) cannot stay Satisfied."""
    book = check(policy)
    for f in findings:
        r = book[f["id"]]
        f["rule_checks"], f["fixes"], f["example"] = r["checks"], [c["fix"] for c in r["checks"] if not c["passed"]], r["example"]
        if any(c["hard"] and not c["passed"] for c in r["checks"]):
            if f["status"] == "Satisfied":
                f.update(status="Partial", decided_by="rulebook")
            continue
        if r["met"] and r["quote"] and f["status"] != "Satisfied":
            f.update(status="Satisfied", quote=r["quote"], quote_verified=True, confidence=max(float(f.get("confidence") or 0), 0.9), decided_by="rulebook")
        elif r["met"] and r["quote"] and not f.get("quote"):  # Satisfied without evidence (keyword judge): quote the sentence that meets the rules
            f.update(quote=r["quote"], quote_verified=True, confidence=max(float(f.get("confidence") or 0), 0.9))


# ── drafting ─────────────────────────────────────────────────────────────────
def draft(v: dict) -> str:
    """One section per obligation, written to pass check(). v holds the intake answers (or [placeholders])."""
    company, contact, dpo, site = v["company"], v["contact"], v["dpo_name"], v["website"]
    address = f", {v['address']}" if v.get("address") else ""
    auto = f" We also collect automatically: {v['data_auto'].rstrip('.')}." if v.get("data_auto") else ""
    langs = f" Versions available now: {v['languages'].rstrip('.')}." if v.get("languages") else " Ask us at the contact below for another language."
    stored = f" Personal data is stored in {v['storage_location'].rstrip('.')}." if v.get("storage_location") else ""
    rights = v.get("rights_channel") or f"write to {contact}"
    if _NONE.match(v["sharing"]):
        sharing = (f"We do not currently share personal data with anyone outside {company}. If we engage a service provider (a Data Processor), "
                   "it will process personal data only on our behalf and under our instructions, under a written contract that requires it to keep the data secure.")
    else:
        sharing = ("We share personal data only with service providers (Data Processors) that process it on our behalf and under our instructions, "
                   f"under a written contract that requires them to keep it secure. They are: {v['sharing'].rstrip('.')}.")
    return f"""# Privacy Policy — {company}

**Data Fiduciary:** {company}{address} · **Website / app:** {site} · **Effective date:** {datetime.now().strftime('%d %B %Y')}

This notice explains how {company} processes personal data under the Digital Personal Data Protection Act, 2023 (the Act) and the Digital Personal Data Protection Rules, 2025. It stands on its own: you do not need to read any other document to understand it.

## 1. Personal data we collect and why (Section 5; Rule 3)
We provide this service: {v['service'].rstrip('.')}. To provide it, we collect the following personal data: {v['data'].rstrip('.')}.{auto} We use it for these purposes: {v['purpose'].rstrip('.')}. We do not use it for any other purpose without asking for your consent again. At {site} you can withdraw consent, exercise your rights, or learn how to complain to the Data Protection Board of India; sections 4, 10 and 12 explain how.

## 2. Consent (Section 6(1))
We process your personal data only with your consent, given by a clear affirmative action: {v['consent_method'].rstrip('.')}. We ask for consent separately for each purpose and never bundle it with our terms of service. We do not use pre-ticked boxes, and simply using our service is never taken as consent. We collect only the personal data that is necessary for the purposes stated in section 1.

## 3. Language of this notice (Section 6(3))
This notice and our consent requests are written in clear and plain language. You can read them in English or in any language listed in the Eighth Schedule to the Constitution of India.{langs}

## 4. Withdrawing consent (Section 6(4))
You can withdraw your consent at any time, as easily as you gave it, here: {v['withdraw_method'].rstrip('.')}. After you withdraw, we and our Data Processors stop processing your personal data for that purpose within a reasonable time, unless a law requires us to keep it. Withdrawal does not affect processing done before it.

## 5. Who we share personal data with (Section 8(2))
{sharing}{stored}

## 6. Keeping your data accurate (Section 8(3))
We take reasonable steps to keep your personal data complete, accurate and consistent, especially where it is used to make a decision that affects you or is shared with another Data Fiduciary. You can ask us to correct it at any time (section 10).

## 7. How we protect your data (Section 8(5); Rule 6)
We protect personal data with reasonable security safeguards, including: {v['security'].rstrip('.')}. We control access to the systems that hold personal data, keep logs of that access and monitor and review them to detect unauthorised access, keep those logs for at least one year, and keep backups so that processing can continue if data is lost or compromised.

## 8. Personal data breaches (Section 8(6); Rule 7)
If a personal data breach occurs, we will inform you and every other affected person without delay, through your account or the email or phone number you registered with us. We will describe the breach and when it happened, its likely consequences for you, what we are doing about it, what you can do to protect yourself, and whom to contact. We will also inform the Data Protection Board of India without delay and send it a detailed report within 72 hours.

## 9. How long we keep your data (Section 8(7); Rule 8)
Retention periods: {v['retention'].rstrip('.')}. We erase your personal data, and have our Data Processors erase it, when you withdraw consent or when it is no longer needed for the purpose it was collected for, unless a law requires us to keep it. As Rule 8(3) requires, we keep personal data, traffic data and logs of processing for at least one year from the processing, and then erase them.

## 10. Access, correction and erasure (Sections 11 and 12; Rule 14)
You can ask us for a summary of the personal data we hold about you and the processing we do on it, and for the identities of everyone we have shared it with. You can also ask us to correct, complete, update or erase it. To make a request, {rights.rstrip('.')}. Include the email address or mobile number registered with us, so we can identify you.

## 11. Nominating someone (Section 14)
You can nominate one or more individuals to exercise your rights if you die or become unable to exercise them because of incapacity. To nominate someone, {rights.rstrip('.')}.

## 12. Grievances (Sections 8(10) and 13; Rule 14(3))
To raise a grievance about your personal data, write to our Grievance Officer, {dpo}, at {contact}. We will respond within {v['grievance_days']} days. If you are not satisfied with our response, you can complain to the Data Protection Board of India.

## 13. Contact for privacy questions (Section 8(9); Rule 9)
For any question about how we process your personal data, contact our Data Protection Officer, {dpo}, at {contact}{address}.

## 14. Children (Section 9; Rule 10)
Who can use our service: {v['children'].rstrip('.')}. We process personal data of anyone under 18 only with the verifiable consent of their parent or lawful guardian. Before we do, we check that the parent or guardian is an identifiable adult, using reliable identity and age details we already hold or details they provide, including through a virtual token such as DigiLocker. We do not track or monitor the behaviour of children or direct targeted advertising at them.

---
*Drafted with DPDP Compass against its rule book of the Act and the Rules. Have counsel review it before publishing.*"""


FACTS_EXAMPLE = {"company": "Acme Payments Pvt Ltd", "address": "12 MG Road, Bengaluru", "website": "https://acme.in/privacy",
                 "service": "a mobile app for UPI payments and bill payments", "data": "Name, mobile number, PAN, bank account number",
                 "data_auto": "device ID, IP address", "purpose": "Process payments, verify identity (KYC), prevent fraud",
                 "consent_method": "ticking an unticked box on the sign-up screen", "languages": "English, Hindi", "withdraw_method": "Settings > Privacy > Withdraw consent",
                 "sharing": "Razorpay (payments), AWS Mumbai (hosting)", "storage_location": "India (AWS Mumbai)", "security": "AES-256 encryption at rest, TLS 1.3, role-based access control",
                 "retention": "KYC records 5 years after account closure (PMLA); logs 12 months", "children": "No, users must be 18 or over",
                 "dpo_name": "Priya Rao", "contact": "dpo@acme.in, +91 80 1234 5678", "grievance_days": "30", "rights_channel": "email dpo@acme.in or use acme.in/privacy"}


if __name__ == "__main__":
    from .audit import judge_rules
    text = draft(FACTS_EXAMPLE)
    book = check(text)
    assert all(r["met"] for r in book.values()), {k: [c["rule"] for c in r["checks"] if not c["passed"]] for k, r in book.items() if not r["met"]}
    assert all(r["quote"] in text for r in book.values())
    assert all(v["status"] == "Satisfied" for v in judge_rules(text).values()), judge_rules(text)
    assert check(draft({**FACTS_EXAMPLE, "sharing": "not shared"}))["PROCESSOR"]["met"]
    bad = check(text.replace("30 days", "120 days") + "\n\nBy using this app you agree to this policy.")
    assert not bad["GRIEVANCE"]["met"] and not bad["CONSENT"]["met"]
    assert not check(text.replace("Priya Rao", "[DPO name]"))["CONTACT"]["met"]
    # Suggested wording shown in audits must meet its own rules once the [blanks] are filled.
    fill = lambda t: re.sub(r"\[N\]", "30", re.sub(r"\[(?!N\])[^\]]+\]", "help@acme.in https://acme.in 5 years", t))  # noqa: E731
    for oid, clause in MODEL_CLAUSES.items():
        assert all(t(fill(clause), fill(clause)) for _, t, _, _ in RULES[oid]), oid
    print("ok:", sum(len(r) for r in RULES.values()), "rules")
