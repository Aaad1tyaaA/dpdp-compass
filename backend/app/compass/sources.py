"""Versioned legal sources: what each document is, when each provision takes effect, and the Rules text.

REGISTRY        the four official documents, with Gazette number, date, file and sha256.
effective(p)    the date a provision of the Act ("8(6)", "27(1)(d)") or of the Rules ("R7(2)", "Sch3") comes into force,
                from G.S.R. 843(E) (Act) and rule 1 of G.S.R. 846(E) (Rules).
status(p, on)   "In force" or "Not yet in force" on an assessment date.
rules()         the English text of the DPDP Rules, 2025 as rules and schedules, with the G.S.R. 892(E) corrigendum applied.
rules_chunks()  retrieval chunks of the Rules in the same shape as statute.chunk_clause_aware().
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

LEGAL = Path(__file__).resolve().parents[3] / "data" / "legal"
OFFICIAL = LEGAL / "official"

ENACTED = date(2023, 8, 11)        # assent; s1(1) and the power in s1(2) run from here
PUBLISHED = date(2025, 11, 13)     # G.S.R. 843(E) and 846(E)
ONE_YEAR = date(2026, 11, 13)
EIGHTEEN_MONTHS = date(2027, 5, 13)

REGISTRY = [
    {"id": "dpdp-act-2023", "title": "Digital Personal Data Protection Act, 2023 (22 of 2023)", "gazette": "Act 22 of 2023",
     "published": "2023-08-11", "file": "DPDP_Act_2023.pdf", "kind": "act"},
    {"id": "dpdp-commencement-2025", "title": "Commencement notification under section 1(2)", "gazette": "G.S.R. 843(E)",
     "published": "2025-11-13", "file": "official/DPDP_Commencement_Notification_2025.pdf", "kind": "notification"},
    {"id": "dpdp-rules-2025", "title": "Digital Personal Data Protection Rules, 2025", "gazette": "G.S.R. 846(E)",
     "published": "2025-11-13", "file": "official/DPDP_Rules_2025.pdf", "kind": "rules"},
    {"id": "dpdp-rules-2025-corrigendum", "title": "Corrigenda to the DPDP Rules, 2025", "gazette": "G.S.R. 892(E)",
     "published": "2025-12-10", "file": "official/DPDP_Rules_2025_Corrigendum.pdf", "kind": "corrigendum", "amends": "dpdp-rules-2025"},
]

# G.S.R. 843(E): (a) on publication, (b) one year, (c) eighteen months. Sub-provisions are listed before their section.
_ACT_DATES: list[tuple[str, date]] = [
    ("1(1)", ENACTED), ("6(9)", ONE_YEAR), ("27(1)(d)", ONE_YEAR), ("44(1)", PUBLISHED), ("44(3)", PUBLISHED),
    ("44(2)", EIGHTEEN_MONTHS), ("Schedule", EIGHTEEN_MONTHS),
    *[(str(n), PUBLISHED) for n in (1, 2, *range(18, 27), 35, *range(38, 44))],
    *[(str(n), EIGHTEEN_MONTHS) for n in (*range(3, 18), *range(27, 35), 36, 37)],
]
# Rule 1(2)-(4). Schedules follow the rule they serve ("[See rule ...]").
_RULE_DATES = {**{n: PUBLISHED for n in (1, 2, 17, 18, 19, 20, 21)}, 4: ONE_YEAR,
               **{n: EIGHTEEN_MONTHS for n in (3, *range(5, 17), 22, 23)}}
_SCHED_RULE = {1: 4, 2: 5, 3: 8, 4: 12, 5: 18, 6: 21, 7: 23}
ORDINALS = ["FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "SIXTH", "SEVENTH"]

# G.S.R. 892(E), item by item, as exact replacements on the printed Gazette page of G.S.R. 846(E).
CORRIGENDUM = [
    ("(i)(a),(b)", 24, "of this Gazette", "in the Official Gazette", 2),
    ("(ii)", 29, "Department of the Central", "Departments of the Central", 1),
    ("(iii)", 32, "given in such.", "given in such order.", 1),
    ("(iv)(a)", 34, "everybody corporate", "every body corporate", 1),
    ("(iv)(b)", 34, "(18 or 2013)", "(18 of 2013)", 1),
    ("(v)(a)", 38, "(35 of 2019).", "(35 of 2019);", 1),
    *[("(v)(b)", 38, f"({a}) “{w}", f"({b}) “{w}", 1) for a, b, w in
      [("f", "g", "mental"), ("e", "f", "health services"), ("d", "e", "healthcare"), ("c", "d", "educational"),
       ("b", "c", "clinical"), ("a", "b", "allied")]],
]


def page_of(provision: str) -> int | None:
    """Gazette page on which a rule or schedule of the Rules starts ("R7", "R7(2)", "Sch3")."""
    head = re.match(r"(R\d+|Sch\d)", provision)
    return next((r.page for r in rules() if head and r.provision == head[1]), None)


def file_url(doc_id: str, page: int | None = None) -> str:
    return f"/api/compass/sources/{doc_id}/file" + (f"#page={page}" if page else "")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def registry() -> list[dict]:
    out = []
    for d in REGISTRY:
        p = LEGAL / d["file"]
        out.append({**d, "available": p.exists(), "sha256": sha256(p) if p.exists() else None,
                    **({"corrections": applied_corrections()} if d["kind"] == "corrigendum" and p.exists() else {})})
    return out


# ── effective dates ─────────────────────────────────────────────────────────
def effective(provision: str) -> date | None:
    """Commencement date of an Act provision ("8(6)") or a Rules provision ("R7(2)", "Sch3")."""
    p = provision.strip()
    if m := re.fullmatch(r"Sch(\d)", p):
        return _RULE_DATES[_SCHED_RULE[int(m[1])]]
    if m := re.match(r"R(\d+)", p):
        return _RULE_DATES.get(int(m[1]))
    for prefix, d in _ACT_DATES:
        if p == prefix or p.startswith(prefix + "("):
            return d
    return None


def status(provision: str, on: date | None = None) -> dict:
    d = effective(provision)
    on = on or date.today()
    return {"provision": provision, "in_force_from": d.isoformat() if d else None,
            "status": "Unknown" if d is None else ("In force" if on >= d else "Not yet in force")}


def annotate(findings: list[dict], on: date | None = None) -> None:
    """Each finding gets the Rules that detail it and whether its obligation is in force on the assessment date."""
    from .checklist import RULES
    from .qa import label
    on = on or date.today()
    for f in findings:
        st = status(f["provision"], on)
        f["in_force_from"], f["legal_status"], f["assessed_on"] = st["in_force_from"], st["status"], on.isoformat()
        f["rules"] = [{"provision": p, "label": label(p), "requirement": req, **status(p, on)} for p, req in RULES.get(f["id"], [])]


# ── the Rules text ──────────────────────────────────────────────────────────
@dataclass
class Rule:
    n: int | str           # rule number, or "Sch1".."Sch7"
    title: str
    text: str
    page: int

    @property
    def provision(self) -> str:
        return f"R{self.n}" if isinstance(self.n, int) else str(self.n)


_PAGE_NOISE = re.compile(r"^(THE GAZETTE OF INDIA.*|\[PART II.*|\[भाग.*|भारत का.*|\d{1,3})$")
_RULE = re.compile(r"^(\d{1,2})\.\s*([A-Z].*)$")
_HEAD = re.compile(r"^(.{3,240}?)\.\s*[—–]+\s*")
_SCHEDULE = re.compile(r"^(" + "|".join(ORDINALS) + r") SCHEDULE$")


def _pages(path: Path) -> list[tuple[int, str]]:
    import pymupdf
    with pymupdf.open(path) as doc:
        return [(i + 1, page.get_text()) for i, page in enumerate(doc)]


def _correct(pages: list[tuple[int, str]]) -> tuple[list[tuple[int, str]], list[dict]]:
    """Whitespace on each page is normalised to single spaces so a correction can span a printed line break."""
    text = {n: re.sub(r"[ \t]*\n[ \t]*", "\n", t) for n, t in pages}
    log = []
    for item, page, old, new, count in CORRIGENDUM:
        flat = re.sub(r"\s+", " ", text[page])
        ok = flat.count(old) == count
        if ok:
            pattern = r"\s+".join(map(re.escape, old.split(" ")))
            text[page] = re.sub(pattern, new, text[page])
        log.append({"item": item, "page": page, "for": old, "read": new, "applied": ok})
    return [(n, text[n]) for n, _ in pages], log


@lru_cache(maxsize=1)
def _parsed() -> tuple[list[Rule], list[dict]]:
    path = OFFICIAL / "DPDP_Rules_2025.pdf"
    pages, log = _correct(_pages(path))
    lines: list[tuple[int, str]] = []
    started = False
    for n, t in pages:
        for raw in t.split("\n"):
            line = raw.strip()
            started = started or line.startswith("G.S.R. 846(E)")
            if started and line and not _PAGE_NOISE.match(line):
                lines.append((n, line))
    out: list[Rule] = []
    cur: Rule | None = None
    in_schedules = False
    for page, line in lines:
        if line.startswith("[F. No."):
            break
        sm = _SCHEDULE.match(line)
        rm = None if in_schedules else _RULE.match(line)
        if sm:
            in_schedules = True
            cur = Rule(f"Sch{ORDINALS.index(sm[1]) + 1}", f"{sm[1].title()} Schedule", "", page)
            out.append(cur)
        elif rm and int(rm[1]) == (out[-1].n + 1 if out else 1):   # sequential numbering, as for the Act
            cur = Rule(int(rm[1]), "", rm[2], page)
            out.append(cur)
        elif cur is not None:
            cur.text += ("" if cur.text.endswith("-") else " ") + line if cur.text else line
    for r in out:
        r.text = re.sub(r"\s+", " ", r.text).strip()
        if isinstance(r.n, int) and (h := _HEAD.match(r.text)):   # the marginal title can wrap onto the next line
            r.title, r.text = h[1].strip(), r.text[h.end():]
    return out, log


def rules() -> list[Rule]:
    return _parsed()[0]


def applied_corrections() -> list[dict]:
    return _parsed()[1]


def _subs(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"(?:^|[.;:—–]\s)\((\d+)\)\s", text)))


def rules_chunks(limit: int = 1200) -> list[dict]:
    """Rule-sized chunks; a long rule or schedule is cut at sentence ends. Provisions are "R7", "R7(2)", "Sch3"."""
    from .statute import _chunk, _split_sentences
    chunks = []
    for r in rules():
        label = f"Rule {r.n}" if isinstance(r.n, int) else r.title
        head = f"DPDP Rules, 2025. {label}. {r.title}. " if isinstance(r.n, int) else f"DPDP Rules, 2025. {r.title}. "
        for i, piece in enumerate(_split_sentences(r.text, limit - len(head)), 1):
            provs = [r.provision] + [f"{r.provision}({s})" for s in _subs(piece)] * isinstance(r.n, int)
            chunks.append(_chunk(f"rules-{r.provision.lower()}-{i}", head + piece, section=0, title=r.title, chapter="DPDP Rules, 2025",
                                 page=r.page, provisions=provs, source="dpdp-rules-2025", in_force_from=effective(r.provision).isoformat()))
    return chunks


if __name__ == "__main__":
    rs = rules()
    assert [r.n for r in rs] == [*range(1, 24), *[f"Sch{i}" for i in range(1, 8)]], [r.n for r in rs]
    assert all(c["applied"] for c in applied_corrections()), [c for c in applied_corrections() if not c["applied"]]
    assert "within seventy-two hours" in next(r for r in rs if r.n == 7).text
    assert effective("6(9)") == ONE_YEAR and effective("8(6)") == EIGHTEEN_MONTHS and effective("27(1)(d)") == ONE_YEAR
    assert effective("27(2)") == EIGHTEEN_MONTHS and effective("44(3)") == PUBLISHED and effective("R4") == ONE_YEAR
    print(len(rs), "rules/schedules,", len(rules_chunks()), "chunks")
