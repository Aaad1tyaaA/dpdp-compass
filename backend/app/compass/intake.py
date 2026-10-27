"""Reads what a business says about its data practices before a policy is drafted from it.

review() returns follow-up questions where an answer is missing or too vague to draft from (the draft would otherwise
have to invent facts), and recommendations prompted by what the answers do say (sensitive data, marketing, transfers
abroad, children, long retention). Each item names the provision it rests on. Rule-based: no model, no quota.
"""
from __future__ import annotations

import re

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?:\+91[\s-]?)?\b\d{10}\b|\+\d[\d\s-]{8,}")
_VAGUE_DATA = re.compile(r"^\s*(?:user|personal|customer|basic|some|necessary|required|relevant|all)?\s*(?:data|info|information|details)\s*\.?\s*$", re.I)
_VAGUE_PURPOSE = re.compile(r"^\s*(?:business|legitimate|general|various|internal|operational)?\s*(?:purposes?|use|uses|operations|needs)\s*\.?\s*$|"
                            r"^\s*(?:to )?improve (?:our )?services?\s*\.?\s*$", re.I)
_VAGUE_SHARING = re.compile(r"\b(?:third parties|partners|vendors|service providers|affiliates)\b", re.I)
_NONE = re.compile(r"^\s*(?:no|none|nobody|no one|not shared|we don'?t share|do not share)\b", re.I)
_FOREVER = re.compile(r"\b(?:forever|indefinitely|permanently|as long as (?:we|needed|necessary|required)|until deleted)\b", re.I)
_DURATION = re.compile(r"\b\d+\s*(?:days?|d|weeks?|wks?|months?|mos?|years?|yrs?|y)\b|\b(?:one|two|three|five|seven|ten)\s+(?:days?|months?|years?)\b", re.I)
_CHILD_YES = re.compile(r"\b(?:yes|students?|kids?|children|minors?|under ?18|school)\b", re.I)
_CHILD_NO = re.compile(r"\b(?:no|none|not|18\+|adults? only|over 18)\b", re.I)

_SENSITIVE = [
    (r"\baadha?a?r\b", "Aadhaar numbers", "Collect Aadhaar only where a law permits it, store it masked, and say so in the policy."),
    (r"\b(?:health|medical|diagnos|prescription)", "health data", "Health data calls for strong safeguards; list exactly what you hold and who sees it."),
    (r"\bbiometric|fingerprint|face ?(?:scan|id)", "biometric data", "Biometrics cannot be changed if leaked; justify the need and encrypt it."),
    (r"\b(?:bank|card|upi|account number|financial|salary|credit)", "financial data", "Name the payment processor and the law that sets its retention (RBI, PMLA)."),
    (r"\b(?:precise |gps |live )?location\b", "location", "Say whether location is precise or approximate and whether it is collected in the background."),
    (r"\bpan\b", "PAN", "Keep PAN only for the tax or KYC purpose it is collected for, and state the retention law."),
]
_ABROAD = re.compile(r"\b(?:us|usa|united states|europe|eu|singapore|global|overseas|outside india|abroad|aws (?:us|virginia|oregon)|gcp us)\b", re.I)
_MARKETING = re.compile(r"\b(?:marketing|advertis|promotion|newsletter|offers|personali[sz]ed ads?)\b", re.I)
_SALE = re.compile(r"\b(?:sell|sale of|monetis|monetiz|data broker)\b", re.I)
_LARGE_PLATFORM = {"E-commerce", "Edtech"}


# How each intake field is named in messages to the user (the form shows the same words).
LABELS = {"company": "your company name", "service": "what your service does", "website": "your website or app link", "data": "the personal data you collect",
          "purpose": "why you collect it", "sharing": "who you share it with", "retention": "how long you keep it", "children": "users under 18",
          "contact": "your privacy contact email", "dpo_name": "who answers privacy questions", "grievance_days": "your grievance response time",
          "security": "your security safeguards", "consent_method": "how people give consent", "withdraw_method": "how people withdraw consent",
          "rights_channel": "where people send rights requests"}


def _q(field: str, question: str, why: str, example: str = "") -> dict:
    return {"field": field, "question": question, "why": why, "example": example}


def _r(title: str, detail: str, basis: str) -> dict:
    return {"title": title, "detail": detail, "basis": basis}


def review(form: dict) -> dict:
    f = {k: (v or "").strip() for k, v in form.items() if isinstance(v, str) or v is None}
    sector = f.get("sector") or "Other"
    qs: list[dict] = []
    recs: list[dict] = []

    if not f.get("company"):
        qs.append(_q("company", "What is the company's registered legal name?", "The policy must name the Data Fiduciary.", "Acme Payments Pvt Ltd"))

    data = f.get("data", "")
    if len(data) < 10 or _VAGUE_DATA.match(data):
        qs.append(_q("data", "Which items of personal data do you collect? List each one.",
                     "Rule 3(b)(i) requires an itemised description of the personal data.", "Name, mobile number, email, delivery address, order history"))
    elif len(re.split(r",|;|\band\b", data)) < 2:
        qs.append(_q("data", "Is that everything? Include data you collect automatically (device ID, IP address, location, cookies).",
                     "Anything left out of the notice cannot rest on the consent it asks for (section 6(1)).", "Device ID, IP address, app usage"))
    for rx, label, advice in _SENSITIVE:
        if re.search(rx, data, re.I):
            recs.append(_r(f"You collect {label}", advice, "Section 8(5); Rule 6"))

    purpose = f.get("purpose", "")
    if len(purpose) < 10 or _VAGUE_PURPOSE.match(purpose):
        qs.append(_q("purpose", "For what specific purposes do you use each kind of data?",
                     "Consent is valid only for a specified purpose (section 6(1)); 'business purposes' is not one.", "Deliver orders, take payment, prevent fraud, answer support requests"))
    if _MARKETING.search(purpose) or _MARKETING.search(data):
        recs.append(_r("Ask for marketing consent separately", "Keep marketing off by default with its own tick box, and let people turn it off in one tap.",
                       "Sections 6(1), 6(4)"))

    sharing = f.get("sharing", "")
    if not sharing:
        qs.append(_q("sharing", "Who receives the data? If no one outside your company does, say 'not shared'.",
                     "The notice and the processor duties depend on it (section 8(2)).", "Razorpay (payments), AWS Mumbai (hosting)"))
    elif _VAGUE_SHARING.search(sharing) and not re.search(r"\b[A-Z][a-zA-Z]+\b.*\(", sharing) and len(sharing) < 60 and not _NONE.match(sharing):
        qs.append(_q("sharing", "Which kinds of companies receive the data, and for what? Name categories or the main providers.",
                     "'Third parties' alone does not tell people who processes their data; each processor needs a valid contract (section 8(2)).",
                     "Payment gateway (Razorpay), cloud hosting (AWS Mumbai), SMS provider"))
    if _SALE.search(sharing) or _SALE.search(purpose):
        recs.append(_r("Selling data needs its own consent", "If you sell or share data for others' own purposes, they become Data Fiduciaries and people must consent to it specifically.",
                       "Sections 6(1), 8(1)"))
    if _ABROAD.search(sharing):
        recs.append(_r("Data goes outside India", "Transfers are allowed unless the Government restricts a country; say where data is stored and check for any notified restriction.",
                       "Section 16; Rule 15"))
    elif sharing and not _NONE.match(sharing):
        recs.append(_r("Sign a data processing contract with each provider", "The contract should bind them to your instructions and to the security safeguards.",
                       "Section 8(2); Rule 6(1)(f)"))

    retention = f.get("retention", "")
    if not retention:
        qs.append(_q("retention", "How long do you keep each kind of data, and which law (if any) requires it?",
                     "Data must be erased once the purpose is served unless a law requires retention (section 8(7)).", "Orders 8 years (GST law), support chats 12 months"))
    elif _FOREVER.search(retention) or not _DURATION.search(retention):
        qs.append(_q("retention", "Can you give a period for each kind of data instead of 'as long as needed'?",
                     "A period people can check is what section 8(7) and Rule 8 expect; 'forever' conflicts with erasure once the purpose ends.",
                     "Account data until deletion plus 30 days; invoices 8 years"))
    if sector in _LARGE_PLATFORM:
        recs.append(_r("Check the Third Schedule", "Large e-commerce, online gaming and social media platforms must erase data after three years of inactivity, with 48 hours' notice.",
                       "Rule 8; Third Schedule"))

    children = f.get("children", "")
    if not children:
        qs.append(_q("children", "Can anyone under 18 use the service? If yes, how will you get a parent's consent?",
                     "Section 9 applies to any user under 18.", "No, users must be 18 or over and we check age at sign-up"))
    elif _CHILD_YES.search(children) and not _CHILD_NO.match(children):
        if not re.search(r"\b(?:parent|guardian|digilocker|token|verif)", children, re.I):
            qs.append(_q("children", "How will you verify that a parent or guardian consents, and that they are an adult?",
                         "Rule 10 requires verifiable consent with due diligence on the parent's identity.", "Parent signs in and confirms through DigiLocker"))
        recs.append(_r("No tracking or targeted ads for children", "Behavioural monitoring and targeted advertising directed at children are prohibited.", "Section 9(3)"))
    elif sector == "Edtech" and _CHILD_NO.search(children):
        recs.append(_r("Edtech users are often minors", "Confirm how you stop under-18s from signing up; if some do, section 9 applies.", "Section 9"))

    contact = f.get("contact", "")
    if not (_EMAIL.search(contact) or _PHONE.search(contact)):
        qs.append(_q("contact", "What email address or phone number should people use for privacy questions and grievances?",
                     "Rule 9 requires the contact details to be published prominently.", "privacy@acme.in, +91 80 1234 5678"))
    if not re.search(r"https?://|www\.|\.[a-z]{2,}(?:/|\b)|\bapp\b", f.get("website", ""), re.I):
        qs.append(_q("website", "What is the link to your website or app page where people manage consent and their rights?",
                     "Rule 3(c) requires the notice to give the communication link for the website or app.", "https://acme.in/privacy"))
    if len(f.get("service", "")) < 10:
        qs.append(_q("service", "What does your service do, in one sentence?",
                     "Rule 3(b)(ii) requires a specific description of the goods or services the processing enables.", "A mobile app for UPI payments and bill payments"))
    if not f.get("dpo_name"):
        qs.append(_q("dpo_name", "Who answers privacy questions and grievances? Give a name or designation.",
                     "The policy must name the Data Protection Officer or the person who answers questions (section 8(9); Rule 9).", "Priya Rao, Data Protection Officer"))
    days = re.findall(r"\d+", f.get("grievance_days", ""))
    if not days or not 1 <= int(days[0]) <= 90:
        qs.append(_q("grievance_days", "Within how many days will you respond to a grievance? It must be 90 or fewer.",
                     "Rule 14(3) caps the response time at ninety days, and the policy must state it.", "30"))
    if not re.search(r"encrypt|access control|mask|obfuscat|multi-factor|two-factor|\bmfa\b|\b2fa\b|firewall|\btls\b|\bssl\b|hash|penetration|vapt|backup", f.get("security", ""), re.I):
        qs.append(_q("security", "Which security safeguards protect the data? Name the actual measures.",
                     "Section 8(5) and Rule 6 expect concrete safeguards such as encryption and access control; 'we keep data safe' is not one.",
                     "AES-256 encryption at rest, TLS in transit, role-based access control, daily backups"))
    if len(f.get("consent_method", "")) < 8:
        qs.append(_q("consent_method", "How does a person give consent? Describe the screen and the action.",
                     "Consent must be a clear affirmative action (section 6(1)); pre-ticked boxes and 'by using this app you agree' do not count.",
                     "Ticking an unticked box on the sign-up screen after reading the notice"))
    if len(f.get("withdraw_method", "")) < 8:
        qs.append(_q("withdraw_method", "How can a person withdraw consent? Give the exact path or address.",
                     "Withdrawal must be as easy as giving consent, and the notice must say how (section 6(4); Rule 3).", "Settings > Privacy > Withdraw consent, or email privacy@acme.in"))
    rights = f.get("rights_channel", "")
    if rights and not (_EMAIL.search(rights) or re.search(r"\b(?:form|settings|portal|page|https?://|www\.|\.in\b|\.com\b)", rights, re.I)):
        qs.append(_q("rights_channel", "Where exactly do people send access, correction, erasure and nomination requests?",
                     "Rule 14 requires you to publish the means of making these requests.", "Email privacy@acme.in or use the form at acme.in/privacy"))
    recs.append(_r("Answer grievances within 90 days at most", "Publish the period you commit to; Rule 14(3) caps it at ninety days.", "Section 8(10); Rule 14(3)"))
    recs.append(_r("Plan for 13 May 2027", "Most Data Fiduciary duties take effect then; build the consent, notice and breach processes before that date.",
                   "G.S.R. 843(E)"))

    names = list(dict.fromkeys(LABELS.get(q["field"], q["field"]) for q in qs))
    listed = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1] if names else ""
    message = ("I have enough to draft the policy." if not qs else
               f"Before I draft this, I need a little more on {listed}. Without it the draft would have to guess, so those parts would be marked as placeholders.")
    return {"complete": not qs, "questions": qs, "recommendations": recs, "message": message}


if __name__ == "__main__":
    thin = review({"company": "Acme", "sector": "Fintech", "data": "user data", "purpose": "business purposes", "sharing": "third parties",
                   "retention": "as long as needed", "children": "yes", "contact": "our team"})
    assert {q["field"] for q in thin["questions"]} == {"data", "purpose", "sharing", "retention", "children", "contact", "dpo_name", "grievance_days",
                                                       "security", "consent_method", "withdraw_method", "website", "service"}, thin["questions"]
    good = review({"company": "Acme Payments Pvt Ltd", "sector": "Fintech", "data": "Name, mobile number, PAN, bank account number",
                   "purpose": "Process payments, verify identity (KYC), prevent fraud", "sharing": "Razorpay (payments), AWS Mumbai (hosting)",
                   "retention": "KYC records 5 years after account closure (PMLA); logs 12 months", "children": "No, 18+ only", "contact": "dpo@acme.in",
                   "dpo_name": "Priya Rao", "grievance_days": "30", "website": "https://acme.in/privacy", "service": "A mobile app for UPI payments", "security": "AES-256 encryption, access control",
                   "consent_method": "Ticking an unticked box at sign-up", "withdraw_method": "Settings > Privacy > Withdraw consent"})
    assert good["complete"], good["questions"]
    assert any("PAN" in r["title"] for r in good["recommendations"]) and any("financial" in r["title"] for r in good["recommendations"])
    print("ok")
