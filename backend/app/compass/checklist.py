"""The audit checklist: 14 obligations of a Data Fiduciary that a privacy policy can evidence.

Each entry names the sub-section of the Act it rests on, the tests for Satisfied and Partial (the same
tests go to the model and to human annotators), a retrieval query for finding the relevant policy
clauses, and keyword groups for the keyword-rule baseline.
"""
from __future__ import annotations

CHECKLIST = [
    {"id": "NOTICE", "title": "Notice of data and purpose", "provision": "5(1)",
     "satisfied": "States the personal data collected and the purpose of processing, and tells the user that a complaint can be made to the Data Protection Board.",
     "partial": "States the data and purposes but not how to complain to the Board, or lists data without purposes.",
     "query": "what personal data we collect and the purposes we use it for; complaint to the Data Protection Board",
     "keywords": [["collect"], ["purpose", "use them to", "use it to", "in order to"], ["data protection board"]]},
    {"id": "CONSENT", "title": "Free, specific and informed consent", "provision": "6(1)",
     "satisfied": "Says processing rests on consent given by a clear affirmative action, and that only the data necessary for the stated purpose is collected.",
     "partial": "Mentions consent to data processing but treats it as implied (for example by using the service) or does not limit collection to what is necessary.",
     "query": "consent to processing of personal data by clear affirmative action, only data necessary for the purpose",
     "keywords": [["consent"], ["agree", "tick", "opt in", "opt-in", "affirmative"], ["only the data", "necessary", "needed for"]]},
    {"id": "LANGUAGE", "title": "Plain language and choice of language", "provision": "6(3)",
     "satisfied": "Says consent requests are in clear, plain language and can be read in English or in the languages of the Eighth Schedule to the Constitution.",
     "partial": "Mentions plain or simple language, or another language, but not a choice among English and the scheduled languages for consent requests.",
     "query": "consent request in plain language available in English or other Indian languages Eighth Schedule",
     "keywords": [["plain language", "simple", "easy to read"], ["english"], ["eighth schedule", "hindi", "indian languages", "22 languages"]]},
    {"id": "WITHDRAWAL", "title": "Withdrawal of consent", "provision": "6(4)",
     "satisfied": "States that consent can be withdrawn at any time and describes a method that is as easy as giving consent.",
     "partial": "States that consent can be withdrawn but the method is burdensome or not described.",
     "query": "withdraw your consent at any time, how to withdraw consent",
     "keywords": [["withdraw", "revoke"], ["consent"], ["any time", "anytime"], ["settings", "single tap", "one tap", "same way"]]},
    {"id": "PROCESSOR", "title": "Data Processors under a valid contract", "provision": "8(2)",
     "satisfied": "Says service providers process personal data only on the company's behalf and under a contract.",
     "partial": "Says personal data is shared with service providers but does not mention a contract or processing only on the company's behalf.",
     "query": "sharing personal data with service providers or processors under contract on our behalf",
     "keywords": [["service provider", "processor", "partner", "third part", "vendor"], ["contract", "agreement"], ["on our behalf", "our instructions"]]},
    {"id": "ACCURACY", "title": "Accuracy of personal data", "provision": "8(3)",
     "satisfied": "Commits the company to keeping personal data complete, accurate and consistent.",
     "partial": "Only lets users edit their own details, with no commitment by the company.",
     "query": "keeping personal data accurate complete consistent and up to date",
     "keywords": [["accura", "up to date", "up-to-date"], ["complete", "consistent"], ["personal data", "your data", "your information"]]},
    {"id": "SECURITY", "title": "Reasonable security safeguards", "provision": "8(5)",
     "satisfied": "Names concrete technical or organisational safeguards that protect personal data.",
     "partial": "Makes a general statement about security without naming any safeguard.",
     "query": "security safeguards protecting personal data encryption access controls",
     "keywords": [["security", "secure", "protect"], ["encrypt", "access control", "audit", "firewall"], ["personal data", "your data", "your information"]]},
    {"id": "BREACH", "title": "Intimation of a personal data breach", "provision": "8(6)",
     "satisfied": "Commits to informing both the Data Protection Board and the affected users of a personal data breach.",
     "partial": "Commits to informing only users, or only unspecified authorities.",
     "query": "personal data breach notification to the Data Protection Board and affected users",
     "keywords": [["breach"], ["inform", "notify", "notif", "intimat"], ["data protection board"], ["affected", "you by", "every user", "users"]]},
    {"id": "ERASURE", "title": "Erasure and retention", "provision": "8(7)",
     "satisfied": "Says personal data is erased when consent is withdrawn or the purpose is no longer served, except where a law requires retention.",
     "partial": "Gives a retention period or says data is kept as long as necessary, without erasure on withdrawal of consent or end of purpose.",
     "query": "how long we retain personal data and when we erase or delete it",
     "keywords": [["retain", "keep", "retention"], ["erase", "delete"], ["withdraw", "no longer needed", "no longer served", "no longer necessary"]]},
    {"id": "CONTACT", "title": "Published contact for privacy questions", "provision": "8(9)",
     "satisfied": "Gives business contact details (email, phone or address) of a Data Protection Officer or a named person who answers questions about data processing.",
     "partial": "Points to a general support channel or a role without contact details for privacy questions.",
     "query": "contact details of data protection officer for questions about processing of personal data",
     "keywords": [["data protection officer", "dpo", "privacy officer", "privacy team"], ["@", "+91", "[email]", "[phone]"]]},
    {"id": "GRIEVANCE", "title": "Grievance redressal mechanism", "provision": "8(10)",
     "satisfied": "Describes how to raise a grievance about personal data, who handles it and the time for a response.",
     "partial": "Says complaints about privacy can be made but gives no process or timeline.",
     "query": "grievance officer how to raise a grievance or complaint about personal data and response time",
     "keywords": [["grievance", "complaint"], ["officer", "write to", "@"], ["within", "days", "hours"]]},
    {"id": "CHILDREN", "title": "Children's personal data", "provision": "9(1)",
     "satisfied": "Says personal data of persons under 18 is processed only with verifiable consent of a parent or lawful guardian.",
     "partial": "Says the service is not intended for children or asks for age, without verifiable parental consent.",
     "query": "children under 18 verifiable consent of parent or guardian",
     "keywords": [["child", "under 18", "minor"], ["parent", "guardian"], ["verifiable", "consent"]]},
    {"id": "ACCESS", "title": "Access to and correction of personal data", "provision": "11(1)",
     "satisfied": "Explains that users can obtain a summary of their personal data and who it was shared with, can have it corrected or erased, and how to ask.",
     "partial": "Offers only one of access or correction, or gives no way to ask.",
     "query": "right to access a summary of your personal data and to correct update or erase it",
     "keywords": [["summary", "access", "copy of"], ["correct", "update", "erase"], ["personal data", "your data"], ["shared it with", "shared with"]]},
    {"id": "NOMINATION", "title": "Right to nominate", "provision": "14(1)",
     "satisfied": "Explains that the user can nominate another individual to exercise her data rights on death or incapacity, and how.",
     "partial": "Refers to legal heirs or a nominee vaguely, without a way to nominate.",
     "query": "nominate another individual to exercise data rights in the event of death or incapacity",
     "keywords": [["nominat"], ["death", "die", "incapacit"], ["rights"]]},
]
BY_ID = {o["id"]: o for o in CHECKLIST}
STATUSES = ["Satisfied", "Partial", "Missing"]


# One result model for every view (business audit, citizen check, PDF scanner). A finding's status says what the
# policy evidences; whether the obligation is in force on the assessment date is a separate field (sources.status),
# so "not yet in force" never changes the coverage score.
STATUS_CODES = {"Satisfied": "SATISFIED", "Partial": "PARTIAL", "Missing": "MISSING", "Not applicable": "NOT_APPLICABLE"}
WEIGHTS = {"SATISFIED": 1.0, "PARTIAL": 0.5, "MISSING": 0.0}
METHOD = {"id": "dpdp-coverage", "version": "1.0",
          "score": "100 x (satisfied + 0.5 x partial) / obligations that apply; Not applicable is excluded",
          "trust": "58 + (score - 50) / 2, kept within 30-92; an indicator of policy coverage, not a probability"}


def code(status: str) -> str:
    """'Satisfied' or 'SATISFIED' -> 'SATISFIED'."""
    return STATUS_CODES.get(status, status.upper().replace(" ", "_"))


def score(statuses: list[str]) -> float:
    """Compliance score S = 100 (n_sat + 0.5 n_part) / n_applicable, for statuses in either spelling."""
    applicable = [code(s) for s in statuses if code(s) != "NOT_APPLICABLE"]
    return round(100 * sum(WEIGHTS.get(s, 0.0) for s in applicable) / len(applicable), 1) if applicable else 0.0


def trust(coverage: float) -> int:
    """The citizen-facing trust indicator, derived from the coverage score alone (METHOD["trust"])."""
    return int(max(30, min(92, 58 + (coverage - 50) // 2)))

# The DPDP Rules, 2025 that give each obligation its detail (G.S.R. 846(E)); summaries, not the text.
RULES = {
    "NOTICE": [("R3", "Notice stands alone, itemises the personal data and each purpose, and links to withdraw consent, exercise rights and complain to the Board.")],
    "CONSENT": [("R3", "Consent rests on a notice that meets rule 3.")],
    "LANGUAGE": [("R3", "Notice is in clear and plain language.")],
    "WITHDRAWAL": [("R3", "Notice gives a link or means to withdraw consent as easily as it was given.")],
    "PROCESSOR": [("R6", "Contract with the Data Processor requires reasonable security safeguards (rule 6(1)(f)).")],
    "SECURITY": [("R6", "Minimum safeguards: encryption, obfuscation or masking; access control; logs and monitoring; backups; one-year log retention; processor contracts; technical and organisational measures.")],
    "BREACH": [("R7", "Inform each affected Data Principal without delay; inform the Board without delay and send a detailed report within 72 hours.")],
    "ERASURE": [("R8", "Classes in the Third Schedule erase data after the set period, with 48 hours' notice; logs kept at least one year."), ("Sch3", "Retention periods for e-commerce, online gaming and social media intermediaries.")],
    "CONTACT": [("R9", "Publish the DPO's or contact person's business contact details prominently on the website or app and in every response to a rights request.")],
    "GRIEVANCE": [("R14", "Publish how to make a request and respond to grievances within a reasonable period not exceeding 90 days.")],
    "CHILDREN": [("R10", "Verifiable consent of the parent, with due diligence that the parent is an identifiable adult (for example a virtual token or DigiLocker)."), ("R12", "Fourth Schedule classes and purposes are exempt from parts of section 9.")],
    "ACCESS": [("R14", "Publish the means and the particulars needed to identify the Data Principal for access, correction and erasure requests.")],
    "NOMINATION": [("R14", "Publish how to nominate one or more individuals under section 14.")],
}
