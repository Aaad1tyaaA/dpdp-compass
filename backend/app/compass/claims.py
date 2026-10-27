"""Claim support and contradiction checks, without a model.

check(answer, evidence): each sentence of an answer is a claim; it is compared with the evidence sentence that
shares most of its content words. Labels:
  supported     most of the claim's content words appear in one evidence sentence, with the same numbers and polarity
  contradicted  a closely matching evidence sentence has different numbers (72 vs 48 hours) or the opposite negation
  absent        nothing in the evidence says it
  uncertain     partial overlap; a person should read the source
A lexical check cannot read paraphrase or meaning: "supported" means "the source says these words", not "true".

conflicts(policy): pairs of clauses in one policy that say opposite things on the same topic (sharing, sale,
retention, consent, children), found by fixed patterns, with their character spans.
"""
from __future__ import annotations

import re

from .retrieval import stems

_NEG = re.compile(r"\b(not|no|never|cannot|can't|won't|without|neither|nor|none)\b|n't\b", re.I)
_NUM = re.compile(r"\b\d+(?:[.,]\d+)?\b|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|twelve|eighteen|"
                  r"twenty|thirty|forty|forty-eight|seventy-two|ninety|hundred|fifty|two hundred and fifty|two hundred)\b", re.I)
_WORDNUM = {"one": "1", "two": "2", "three": "3", "seven": "7", "ten": "10", "twelve": "12", "eighteen": "18", "thirty": "30",
            "forty-eight": "48", "seventy-two": "72", "ninety": "90", "fifty": "50", "two hundred and fifty": "250", "two hundred": "200"}
_CITE = re.compile(r"\[[^\]]{1,60}\]")


def sentences(text: str) -> list[str]:
    text = re.sub(r"^\s*[-*•]\s*", "", text, flags=re.M)
    parts = re.split(r"(?<=[.;!?])\s+|\n+", text)
    return [p.strip() for p in parts if len(stems(_CITE.sub("", p))) >= 3]


def _nums(text: str) -> set[str]:
    return {_WORDNUM.get(m.lower(), m.replace(",", "")) for m in _NUM.findall(text)}


def _label(claim: str, evidence_sentences: list[str]) -> dict:
    words = set(stems(_CITE.sub("", claim)))
    best, best_cov = "", 0.0
    for s in evidence_sentences:
        cov = len(words & set(stems(s))) / max(1, len(words))
        if cov > best_cov:
            best, best_cov = s, cov
    cn, en = _nums(_CITE.sub("", claim)), _nums(best)
    if best_cov >= 0.5 and cn and en and not cn & en:
        status, why = "contradicted", f"the source gives {', '.join(sorted(en))}, the answer {', '.join(sorted(cn))}"
    elif best_cov >= 0.5 and bool(_NEG.search(claim)) != bool(_NEG.search(best)):
        status, why = "contradicted", "the source states the opposite polarity (one says not, the other does not)"
    elif best_cov >= 0.6:
        status, why = "supported", "the source states this"
    elif best_cov >= 0.35:
        status, why = "uncertain", "the source says something related; read it"
    else:
        status, why = "absent", "the cited sources do not say this"
    return {"claim": claim, "status": status, "reason": why, "evidence": best[:400] if best_cov >= 0.35 else "", "overlap": round(best_cov, 2)}


def check(answer: str, evidence: list[str]) -> dict:
    ev = [s for t in evidence for s in sentences(t)]
    claims = [_label(c, ev) for c in sentences(answer)]
    counts = {k: sum(c["status"] == k for c in claims) for k in ("supported", "uncertain", "absent", "contradicted")}
    return {"claims": claims, "counts": counts, "method": "lexical overlap with the evidence; a heuristic, not a judgement of truth"}


# ── conflicting clauses inside one policy ───────────────────────────────────
_TOPICS = [
    ("sharing", "PROCESSOR", r"\b(?:do|will) not (?:share|disclose)\b[^.]{0,80}\b(?:third part|anyone|other)",
     r"\b(?:we )?(?:may |will |do )?(?:share|disclose)s? (?:your |personal )?(?:data|information)[^.]{0,60}\b(?:third part|partners?|advertis|affiliates)"),
    ("sale", "PROCESSOR", r"\b(?:do|will) not (?:sell|rent)\b", r"\b(?:we )?(?:may |will |can )(?:sell|rent)\b"),
    ("retention", "ERASURE", r"\b(?:delete|erase|remove)[^.]{0,60}\bwithin \w+ (?:days|months|hours)\b|\bno longer than\b",
     r"\b(?:retain|keep|store)[^.]{0,40}\b(?:indefinitely|forever|permanently|as long as we (?:like|wish|want))\b"),
    ("consent", "CONSENT", r"\b(?:ask|seek|obtain)[^.]{0,30}\b(?:explicit|express|your) consent\b|\bopt[- ]in\b",
     r"\bby (?:using|accessing|continuing)[^.]{0,60}\b(?:you )?(?:consent|agree)\b|\bdeemed (?:to have )?consent"),
    ("children", "CHILDREN", r"\bnot (?:intended|directed) (?:for|to|at) (?:children|minors|anyone under)\b|\bdo not knowingly collect\b",
     r"\b(?:children|kids|students|minors)(?:'s)? (?:accounts?|profiles?|can (?:sign up|register|use))\b"),
]


def conflicts(policy: str) -> list[dict]:
    out = []
    for topic, obligation, a, b in _TOPICS:
        ma = re.search(a, policy, re.I)
        # the opposing statement must be a different clause, and not itself negated ("we do not share ... third parties")
        mb = next((m for m in re.finditer(b, policy, re.I) if ma and _clause(policy, m.start()) != _clause(policy, ma.start())
                   and not _NEG.search(_clause(policy, m.start()))), None)
        if ma and mb:
            out.append({"topic": topic, "obligation_id": obligation,
                        "a": {"text": _clause(policy, ma.start()), "span": [ma.start(), ma.end()]},
                        "b": {"text": _clause(policy, mb.start()), "span": [mb.start(), mb.end()]}})
    return out


def _clause(text: str, at: int) -> str:
    start = max(text.rfind(".", 0, at), text.rfind("\n", 0, at)) + 1
    end = min([i for i in (text.find(".", at), text.find("\n", at)) if i != -1] or [len(text)])
    return text[start:end + 1].strip()[:400]


if __name__ == "__main__":
    src = ["The Data Fiduciary shall inform the Board within seventy-two hours of becoming aware of the breach."]
    r = check("The company must inform the Board within 72 hours of becoming aware of the breach.", src)["claims"][0]
    assert r["status"] == "supported", r
    assert check("The company must inform the Board within 48 hours of becoming aware of the breach.", src)["claims"][0]["status"] == "contradicted"
    assert check("The company need not inform the Board of becoming aware of the breach.", src)["claims"][0]["status"] == "contradicted"
    assert check("Children can open accounts with a teacher's approval only.", src)["claims"][0]["status"] == "absent"
    c = conflicts("We do not share your data with third parties. We may share your information with advertising partners.")
    assert [x["topic"] for x in c] == ["sharing"], c
    assert c[0]["a"]["text"] != c[0]["b"]["text"] and "advertising" in c[0]["b"]["text"], c
    assert conflicts("We do not share your data with third parties. We never share your data with partners.") == []
    print("ok")
