"""Rights-request letters under the DPDP Act: one template per right, filled with the person's details, addressed to a
contact found in the company's own policy text. Nothing is sent; the person downloads and sends it themselves.

A contact is only ever one that appears in the policy text we hold, quoted with its context; otherwise the letter keeps
a [placeholder]. Templates are plain drafting, not legal advice, and have not been reviewed by a lawyer.
"""
from __future__ import annotations

import re
from datetime import date

from . import sources

TYPES = {
    "access": {
        "title": "Get a summary of my personal data", "provisions": ["11(1)", "R14"],
        "subject": "Request for a summary of my personal data under section 11 of the DPDP Act, 2023",
        "ask": ("Under section 11(1) of the Digital Personal Data Protection Act, 2023, please provide (a) a summary of the personal data "
                "about me that you process and the processing activities undertaken on it, (b) the identities of all other Data Fiduciaries "
                "and Data Processors with whom you have shared it, with a description of the data shared, and (c) any other information "
                "about my personal data and its processing that is prescribed."),
    },
    "correct": {
        "title": "Correct or update my personal data", "provisions": ["12(1)", "12(2)", "R14"],
        "subject": "Request to correct my personal data under section 12 of the DPDP Act, 2023",
        "ask": ("Under section 12(2) of the Digital Personal Data Protection Act, 2023, please correct the inaccurate or misleading personal "
                "data, complete the incomplete personal data, and update the personal data described below."),
    },
    "erase": {
        "title": "Erase my personal data", "provisions": ["12(3)", "8(7)", "R14"],
        "subject": "Request to erase my personal data under section 12(3) of the DPDP Act, 2023",
        "ask": ("Under section 12(3) of the Digital Personal Data Protection Act, 2023, please erase my personal data described below, "
                "and have any Data Processor holding it on your behalf erase it, unless retention is necessary for the specified purpose or "
                "for compliance with a law in force. If you retain any of it, please tell me which data and under which law."),
    },
    "withdraw": {
        "title": "Withdraw my consent", "provisions": ["6(4)", "6(6)"],
        "subject": "Withdrawal of consent under section 6(4) of the DPDP Act, 2023",
        "ask": ("Under section 6(4) of the Digital Personal Data Protection Act, 2023, I withdraw my consent to the processing of my personal "
                "data for the purposes described below. Under section 6(6), please cease, and cause your Data Processors to cease, processing "
                "my personal data for these purposes within a reasonable time."),
    },
    "grievance": {
        "title": "Raise a grievance", "provisions": ["13(1)", "13(2)", "13(3)", "R14"],
        "subject": "Grievance under section 13 of the DPDP Act, 2023",
        "ask": ("Under section 13 of the Digital Personal Data Protection Act, 2023, I raise the grievance described below about your "
                "performance of your obligations in relation to my personal data, and ask you to respond within the period you have "
                "published, which under Rule 14(3) of the DPDP Rules, 2025 must not exceed ninety days."),
    },
    "nominate": {
        "title": "Nominate someone to act for me", "provisions": ["14(1)", "R14"],
        "subject": "Nomination under section 14 of the DPDP Act, 2023",
        "ask": ("Under section 14(1) of the Digital Personal Data Protection Act, 2023, I nominate the individual named below to exercise "
                "my rights under the Act in the event of my death or incapacity. Please record this nomination and confirm it."),
    },
}
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_ROLE = re.compile(r"grievance|data protection officer|\bdpo\b|nodal|privacy|complaint", re.I)


def contact(policy: str) -> dict | None:
    """The first email in the policy whose surrounding text names a grievance, privacy or DPO role; quoted with its context."""
    for m in _EMAIL.finditer(policy or ""):
        start = max(0, m.start() - 160)
        context = policy[start:m.end() + 40]
        if _ROLE.search(context):
            context = re.sub(r"^\S*\s", "", context) if start else context  # begin at a whole word
            context = re.sub(r"\s\S*$", "", context) if m.end() + 40 < len(policy) else context
            return {"email": m.group(0).rstrip("."), "context": "…" * bool(start) + re.sub(r"\s+", " ", context).strip() + "…"}
    return None


def draft(kind: str, company: str, policy: str | None, person: dict, on: date | None = None) -> dict:
    t = TYPES[kind]
    on = on or date.today()
    found = contact(policy or "")
    to = found["email"] if found else "[the company's grievance officer or DPO email, from its privacy policy]"
    name = (person.get("name") or "").strip() or "[your full name]"
    lines = [
        f"To: {to}",
        f"Subject: {t['subject']}",
        "",
        f"Dear Grievance Officer / Data Protection Officer, {company or '[company]'},",
        "",
        t["ask"],
        "",
        "Details",
        f"- Name: {name}",
        f"- Email or phone registered with you: {(person.get('contact') or '').strip() or '[email or phone you use with the service]'}",
        f"- Account or customer identifier: {(person.get('account') or '').strip() or '[account ID, order number or registered mobile]'}",
    ]
    if (person.get("details") or "").strip():
        lines += [f"- {'Nominee and relationship' if kind == 'nominate' else 'What this concerns'}: {person['details'].strip()}"]
    lines += [
        "",
        "Please acknowledge this request and tell me how you will verify my identity, if you need to. If you need anything else "
        "from me, please say so in your reply.",
        "",
        "Yours sincerely,",
        name,
        on.strftime("%d %B %Y"),
    ]
    basis = [{"provision": p, "label": ("Rule " + p[1:]) if p.startswith("R") else "Section " + p, **sources.status(p, on)} for p in t["provisions"]]
    notes = []
    if any(b["status"] == "Not yet in force" for b in basis):
        first = min(b["in_force_from"] for b in basis if b["status"] == "Not yet in force")
        notes.append(f"Some of these provisions come into force on {first}. Until then the company may not be bound to answer under the Act, "
                     "although many already accept such requests.")
    if kind == "grievance":
        notes.append("Section 13(3): you must first use the company's grievance redressal before complaining to the Data Protection Board.")
    notes.append("Send this from the email or phone registered with the service, and keep a copy with the date you sent it.")
    notes.append("This is a template, not legal advice, and it has not been reviewed by a lawyer.")
    return {"type": kind, "title": t["title"], "subject": t["subject"], "to": to, "letter": "\n".join(lines),
            "contact": {**found, "source": f"{company} privacy policy text held by DPDP Compass; check it against the company's current policy"} if found else None,
            "basis": basis, "notes": notes}


if __name__ == "__main__":
    pol = "For complaints contact our Grievance Officer, Ms A, at grievance@shop.example. Marketing: hello@shop.example."
    assert contact(pol)["email"] == "grievance@shop.example" and contact("Write to hello@x.in.") is None
    d = draft("erase", "Shop", pol, {"name": "Asha"}, date(2027, 6, 1))
    assert d["to"] == "grievance@shop.example" and "section 12(3)" in d["letter"] and "Asha" in d["letter"]
    assert all(b["status"] == "In force" for b in d["basis"]) and draft("access", "X", None, {}, date(2026, 1, 1))["to"].startswith("[")
    print("ok")
