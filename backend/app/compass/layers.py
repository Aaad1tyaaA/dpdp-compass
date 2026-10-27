"""The three-layer knowledge structure and the knowledge graph, built from the parsed statute.

Layer 1  facts:        clause chunks and the terms defined in section 2
Layer 2  obligations:  normative statements whose grammatical subject is a legal actor
                       (shall -> duty, shall not -> prohibition, shall have the right -> right, may -> power)
Layer 3  principles:   each obligation mapped, by provision, to a data-protection principle

Every graph edge carries the provision, page and sentence that states it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .statute import Statute, Unit, norm

ACTORS = ["Significant Data Fiduciary", "Data Fiduciary", "Data Principal", "Data Processor", "Consent Manager",
          "Appellate Tribunal", "Central Government", "Chairperson", "Board", "intermediary"]
_ACTOR = "(?:" + "|".join(ACTORS) + ")"
# The actor must open the clause (optionally after an introductory phrase ending in a comma), so that
# actors inside prepositional or relative phrases ("a notice given by the Data Fiduciary") are not subjects.
_DEONTIC = re.compile(
    rf"(?:^|(?<=[.;:,—])\s+|\band\s+)(?:\([0-9a-z]+\)\s+)?(?:(?:the|a|an|every|such|any|that)\s+)?(?:said\s+)?"
    rf"(?P<actor>{_ACTOR})(?:\s+or\s+(?:its\s+)?(?:{_ACTOR}|officers))?(?:\s+and\s+(?:other\s+|any\s+other\s+)?Members?)?"
    rf"(?:\s+[a-z]+ing(?:\s+[a-z]+){{0,3}})?(?:,[^,;.]{{0,160}},)?\s+(?P<modal>shall not|shall have the right|shall|may)\b(?!\s*,?\s*by notification, appoint)",
    re.I)
_DEFINITIONAL = re.compile(r"^\s*(?:mean|be construed|have the same meaning|have the meanings|be deemed|be considered)\b", re.I)
MODAL = {"shall not": ("MUST_NOT", "prohibition"), "shall have the right": ("HAS_RIGHT", "right"), "shall": ("MUST", "duty"), "may": ("MAY", "power")}

# Layer 3: provision prefix -> principle (first match wins, most specific first).
PRINCIPLES = [
    ("8(5)", "security safeguards"), ("8(6)", "security safeguards"), ("8(3)", "accuracy"),
    ("8(7)", "storage limitation"), ("8(8)", "storage limitation"), ("12(3)", "storage limitation"),
    ("8(9)", "notice and transparency"), ("8(10)", "grievance redressal"), ("13", "grievance redressal"),
    ("8", "accountability"), ("10", "accountability"), ("4", "lawfulness and purpose limitation"), ("7", "lawfulness and purpose limitation"),
    ("5", "notice and transparency"), ("6", "consent"), ("9", "children's data"), ("11", "data principal rights"),
    ("12", "data principal rights"), ("14", "data principal rights"), ("15", "data principal duties"), ("16", "cross-border transfer"),
] + [(str(n), "oversight and enforcement") for n in range(17, 44)]


def principle_of(provision: str) -> str | None:
    for prefix, name in PRINCIPLES:
        if provision == prefix or provision.startswith(prefix + "("):
            return name
    return None


@dataclass
class Edge:
    src: str
    pred: str
    dst: str
    provision: str
    page: int
    sentence: str


@dataclass
class KnowledgeBase:
    definitions: dict[str, str] = field(default_factory=dict)   # term -> provision
    obligations: list[dict] = field(default_factory=list)       # Layer 2 records
    edges: list[Edge] = field(default_factory=list)

    @property
    def nodes(self) -> set[str]:
        return {e.src for e in self.edges} | {e.dst for e in self.edges}

    def counts(self) -> dict:
        by = {}
        for e in self.edges:
            by[e.pred] = by.get(e.pred, 0) + 1
        kinds = {}
        for o in self.obligations:
            kinds[o["kind"]] = kinds.get(o["kind"], 0) + 1
        return {"definitions": len(self.definitions), "obligations": len(self.obligations), "obligation_kinds": kinds,
                "principles": len({o["principle"] for o in self.obligations if o["principle"]}), "nodes": len(self.nodes),
                "relationships": len(self.edges), "by_predicate": by}


def _sentences(text: str) -> list[str]:
    text = re.split(r"\bIllustrations?\.", text)[0]  # illustrations use placeholder parties (X, Y), not legal actors
    return [s.strip() for s in re.split(r"(?<=[.;])\s+(?=[A-Z(“])", text) if s.strip()]


_ASIDE = re.compile(r"^(?:by|with|within|after|before|if|on|upon|for|as far as|unless|in|subject to|having regard|irrespective|where|while|"
                    r"at any|during|notwithstanding|except|an opportunity|and subject)\b", re.I)


def split_asides(action: str) -> tuple[str, str]:
    """Separate leading conditions ("by notification, ...", "within a reasonable time, ...") from the action itself."""
    asides = []
    for _ in range(4):
        if not (_ASIDE.match(action) and "," in action[:240]):
            break
        head, rest = action.split(",", 1)
        if len(head.split()) > 14:  # too long to be a simple leading condition: leave the text as it stands
            break
        action = rest
        asides.append(head.strip())
        action = re.sub(r"^[\s—–-]*(?:\([a-z]\)\s*)?(?:and\s+)?", "", action)
    return action.strip(), "; ".join(asides)


def extract_obligations(units: list[Unit]) -> list[dict]:
    out = []
    for u in units:
        text = (u.lead + " " + u.text).strip() if u.clause else u.text
        for sent in _sentences(text):
            for m in _DEONTIC.finditer(sent):
                rest = sent[m.end():]
                if _DEFINITIONAL.match(rest):
                    continue
                pred, kind = MODAL[m["modal"].lower()]
                action, condition = split_asides(re.sub(r"\s+", " ", rest).strip(" ,—-:;."))
                action = action[:220]
                if len(action) < 4:
                    continue
                actor = next(a for a in ACTORS if a.lower() == m["actor"].lower())
                out.append({"id": f"O{len(out) + 1}", "actor": actor, "predicate": pred, "kind": kind, "action": action,
                            "condition": condition, "provision": u.provision, "page": u.page, "sentence": sent[:400], "principle": principle_of(u.provision)})
    return out


_OTHER_ACT = r"(?:\s+and\s+section\s+\d+\w*)*\s+of\s+the\s+[A-Z][A-Za-z ,]*?(?:Act|Code)\b"
_REFS = [
    (re.compile(r"sub-clause \([ivx]+\) of clause \(([a-z]+)\) of sub-section \((\d+)\) of section (\d+)"), lambda m, s: [f"{m[3]}({m[2]})"]),
    (re.compile(r"clause \(([a-z]+)\) of sub-section \((\d+)\) of section (\d+)(?!" + _OTHER_ACT + ")"), lambda m, s: [f"{m[3]}({m[2]})"]),
    (re.compile(r"sub-sections? \((\d+)\)(?:(?:,| and| or) \((\d+)\))? of section (\d+)(?!" + _OTHER_ACT + ")"), lambda m, s: [f"{m[3]}({k})" for k in (m[1], m[2]) if k]),
    (re.compile(r"clause \(([a-z]+)\) of section (\d+)(?!" + _OTHER_ACT + ")"), lambda m, s: [f"{m[2]}({m[1]})"]),
    (re.compile(r"\bsections (\d+)((?:(?:,| and| or) \d+)+)(?!\w)(?!" + _OTHER_ACT + ")"), lambda m, s: [m[1], *re.findall(r"\d+", m[2])]),
    (re.compile(r"\bsection (\d+)(?!\w)(?!" + _OTHER_ACT + ")"), lambda m, s: [m[1]]),
    (re.compile(r"sub-sections? \((\d+)\)(?:(?:,| and| or) (?:sub-section )?\((\d+)\))?(?! of section)"), lambda m, s: [f"{s}({k})" for k in (m[1], m[2]) if k]),
]


def references(text: str, section: int) -> list[str]:
    """Provisions of this Act that a passage refers to (references to other Acts are skipped)."""
    found, taken = [], []
    for rx, make in _REFS:
        for m in rx.finditer(text):
            if any(a < m.end() and m.start() < b for a, b in taken):
                continue
            taken.append(m.span())
            found += make(m, section)
    return list(dict.fromkeys(found))


def build(st: Statute) -> KnowledgeBase:
    kb = KnowledgeBase()
    fine = st.units(1)  # finest granularity: every lettered clause is its own unit
    valid = {u.provision for u in fine} | {f"{u.section}({u.sub})" for u in fine if u.sub} | {str(s.n) for s in st.sections}
    for u in fine:
        if u.section == 2 and u.clause:
            m = re.search(r"“([^”]+)”", u.text)
            if m:
                kb.definitions[m[1]] = u.provision
                kb.edges.append(Edge(f"term:{m[1]}", "DEFINED_IN", f"prov:{u.provision}", u.provision, u.page, u.text[:300]))
    kb.obligations = extract_obligations(st.units(10 ** 9))
    for o in kb.obligations:
        kb.edges.append(Edge(f"actor:{o['actor']}", o["predicate"], f"obl:{o['id']}", o["provision"], o["page"], o["sentence"]))
        if o["principle"]:
            kb.edges.append(Edge(f"obl:{o['id']}", "SERVES_PRINCIPLE", f"principle:{o['principle']}", o["provision"], o["page"], o["sentence"]))
    seen = set()
    for u in st.units(10 ** 9):
        body = re.split(r"\bIllustrations?\.", u.text)[0]
        for ref in references(body, u.section):
            if ref in valid and ref != u.provision and not u.provision.startswith(ref + "(") and (u.provision, ref) not in seen:
                seen.add((u.provision, ref))
                sent = next((s for s in _sentences(body) if "section" in s), body)[:300]
                kb.edges.append(Edge(f"prov:{u.provision}", "REFERS_TO", f"prov:{ref}", u.provision, u.page, sent))
    for i, row in enumerate(st.schedule_rows, 1):
        refs = references(row.split("Penalty:")[0], 0)
        kb.edges.append(Edge(f"penalty:{i}", "PENALTY", f"prov:{refs[0]}" if refs else "prov:any other provision", "Schedule", st.schedule_page, row))
    return kb


def penalty_ceiling(kb: KnowledgeBase, provision: str) -> str:
    """Penalty text the Schedule attaches to a provision (falls back to the residual row)."""
    rows = [e for e in kb.edges if e.pred == "PENALTY"]
    for e in rows:
        target = e.dst.removeprefix("prov:")
        if provision == target or provision.startswith(target + "("):
            return e.sentence.split("Penalty:")[1].strip()
    return next((e.sentence.split("Penalty:")[1].strip() for e in rows if e.dst.endswith("any other provision")), "")


class GraphRetriever:
    """Provisions connected to what the query mentions, plus provisions cross-referenced by seed provisions."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.terms = {norm(t): p for t, p in kb.definitions.items() if len(t) > 5}
        self.refers = {}
        for e in kb.edges:
            if e.pred == "REFERS_TO":
                self.refers.setdefault(e.src[5:], []).append(e.dst[5:])

    def provisions(self, query: str, seeds: list[str]) -> dict[str, float]:
        q, score = norm(query), {}
        for term, prov in self.terms.items():
            if term in q:
                score[prov] = score.get(prov, 0) + 2.0
        for o in self.kb.obligations:
            if o["actor"].lower() in q:
                overlap = len(set(re.findall(r"[a-z]{5,}", o["action"].lower())) & set(re.findall(r"[a-z]{5,}", q)))
                if overlap:
                    score[o["provision"]] = score.get(o["provision"], 0) + overlap
            if o["principle"] and o["principle"].split()[0] in q:
                score[o["provision"]] = score.get(o["provision"], 0) + 1.0
        if re.search(r"penalt|fine\b|crore", q):
            score["Schedule"] = score.get("Schedule", 0) + 2.0
        for seed in seeds:
            for ref in self.refers.get(seed, []):
                score[ref] = score.get(ref, 0) + 0.5
        return score
