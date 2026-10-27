"""Applicability questionnaire: which of the 14 obligations apply to this organisation, and why.

Answers narrow the checklist only where the Act itself makes an obligation conditional on a fact the
organisation knows (its role, its grounds of processing, whether it processes children's data). Exemptions
that depend on a government notification (section 17(2)(a), 17(3), Significant Data Fiduciary status) are
never granted from an answer: they are reported as notes to verify, and the obligations stay in the audit.
An answer that the policy text contradicts (says "no children" but the policy speaks of minors) is not applied.
"""
from __future__ import annotations

import re

QUESTIONS = [
    {"id": "role", "text": "In this processing, who decides why and how personal data is processed?",
     "options": {"fiduciary": "We do (Data Fiduciary)", "processor": "Another company; we process only on its behalf (Data Processor)"},
     "default": "fiduciary"},
    {"id": "grounds", "text": "On what ground is personal data processed?",
     "options": {"consent": "Consent", "both": "Consent and legitimate uses (section 7)", "legitimate_use": "Only legitimate uses under section 7, never consent"},
     "default": "consent"},
    {"id": "children", "text": "Do you knowingly process personal data of anyone under 18?",
     "options": {"yes": "Yes", "unsure": "Not sure", "no": "No"}, "default": "unsure"},
    {"id": "notified", "text": "Has the Central Government notified you under the Act?",
     "options": {"none": "No", "sdf": "As a Significant Data Fiduciary (section 10)", "startup": "As a class exempted under section 17(3)",
                 "state": "As a State instrumentality under section 17(2)(a)"}, "default": "none"},
]
DEFAULTS = {q["id"]: q["default"] for q in QUESTIONS}
_CONSENT_ONLY = ("NOTICE", "CONSENT", "LANGUAGE", "WITHDRAWAL")
_MINORS = re.compile(r"\b(child|children|minor|minors|under 18|under the age of 18|parent|guardian|kid|kids|student)\b", re.I)


def assess(answers: dict | None, policy: str = "") -> dict:
    """{"applies": {obligation_id: (bool, reason)}, "notes": [str], "answers": {...}}."""
    a = {**DEFAULTS, **{k: v for k, v in (answers or {}).items() if k in DEFAULTS and v in dict(next(q for q in QUESTIONS if q["id"] == k)["options"])}}
    applies: dict[str, tuple[bool, str]] = {}
    notes: list[str] = []
    if a["role"] == "processor":
        reason = "You process only on behalf of a Data Fiduciary; this duty rests on the Data Fiduciary (section 8(1)), which must bind you by contract."
        for ob in ("NOTICE", "CONSENT", "LANGUAGE", "WITHDRAWAL", "ACCURACY", "BREACH", "ERASURE", "CONTACT", "GRIEVANCE", "CHILDREN", "ACCESS", "NOMINATION"):
            applies[ob] = (False, reason)
        notes.append("As a Data Processor you still need the safeguards your contract requires (Rule 6(1)(f)); the audit keeps security and processor clauses.")
    if a["grounds"] == "legitimate_use":
        for ob in _CONSENT_ONLY:
            applies.setdefault(ob, (False, "Processing rests only on a legitimate use under section 7, so the consent and notice duties in sections 5 and 6 do not arise."))
    if a["children"] == "no":
        if _MINORS.search(policy):
            notes.append("You answered that you do not process children's data, but the policy mentions children, minors or parents, so the children's obligation stays in the audit.")
        else:
            applies.setdefault("CHILDREN", (False, "You do not knowingly process personal data of anyone under 18 (section 9 applies only to a child's data)."))
    if a["notified"] == "sdf":
        notes.append("Significant Data Fiduciaries have further duties outside this checklist: a Data Protection Officer in India, an independent data auditor, "
                     "periodic Data Protection Impact Assessments (section 10), and the annual DPIA, audit and algorithmic checks in Rule 13.")
    elif a["notified"] in ("startup", "state"):
        notes.append(f"An exemption under section {'17(3)' if a['notified'] == 'startup' else '17(2)(a)'} depends on a government notification naming you or your class. "
                     "It is not applied here from an answer: check the notification, and keep the obligations until it is confirmed.")
    return {"answers": a, "applies": applies, "notes": notes}


def apply(findings: list[dict], result: dict) -> None:
    """Mark findings that do not apply. The model's verdict is kept in model_status; the coverage score excludes them."""
    for f in findings:
        ok, reason = result["applies"].get(f["id"], (True, ""))
        f["applies"], f["applicability_reason"] = ok, reason
        if not ok:
            f.setdefault("model_status", f["status"])
            f["status"] = "Not applicable"


if __name__ == "__main__":
    r = assess({"children": "no", "grounds": "legitimate_use"}, "We sell groceries.")
    assert not r["applies"]["CHILDREN"][0] and not r["applies"]["CONSENT"][0] and "ACCESS" not in r["applies"]
    assert "CHILDREN" not in assess({"children": "no"}, "Parents must approve accounts for minors.")["applies"]
    assert assess({"notified": "startup"})["applies"] == {} and assess({"role": "bogus"})["answers"]["role"] == "fiduciary"
    print("ok")
