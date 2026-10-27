"""Clause-aware chunking of a statute from its Gazette PDF (or plain text).

parse()  -> Statute: long title, sections -> sub-sections -> lettered clauses, the Schedule.
chunk_clause_aware(): consecutive sub-sections packed up to a character limit without cutting one;
an over-long sub-section is cut at its lettered clauses. Each chunk is prefixed with its section
number and marginal title and carries section, provisions, chapter and starting page.
chunk_sections() and chunk_fixed() give the baselines for the chunking ablation over the same
cleaned text.

Numbering must be sequential ("7." starts section 7 only right after section 6); that single rule
rejects years, list items and cross-references that begin a line.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .pdfio import Line, read_lines

_NOISE = re.compile(r"^(THE GAZETTE OF INDIA.*|\[PART II.*|SEC\. \d+\]|\d{1,3}|\d+ of \d{4}\.)$")
_SIDE_REF = re.compile(r"^\d+ of \d{4}\.$")
_CHAPTER = re.compile(r"^CHAPTER [IVXLC]+$")
_SEC = re.compile(r"^(\d+)\.\s+(.*)$")
_SUB = re.compile(r"^\((\d+)\)\s+(?=[A-Z“\"‘'])")
_CLAUSE = re.compile(r"^\(([a-z]{1,2})\)\s+(?!(?:of|and|or|to)\b)")
_SCHED = re.compile(r"^(THE\s+)?([A-Z]+\s+)?SCHEDULE\b")
_END = re.compile(r"^[—_\-]{3,}$")
_TITLE = re.compile(r"^THE .* ACT, \d{4}$")


def norm(text: str) -> str:
    """Comparison form: lower case, plain quotes and dashes, single spaces."""
    text = text.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "—": "-", "–": "-", " ": " "}))
    return re.sub(r"\s+", " ", text).strip().lower()


@dataclass
class Unit:
    """Smallest citable piece: a sub-section, or one lettered clause of an over-long one."""
    section: int
    sub: int | None
    clause: str | None
    lead: str  # text before the clause list, repeated when clauses are separated
    text: str
    page: int

    @property
    def provision(self) -> str:
        return str(self.section) + (f"({self.sub})" if self.sub else "") + (f"({self.clause})" if self.clause else "")


@dataclass
class Section:
    n: int
    title: str
    chapter: str
    page: int
    y: float
    lead: list[str] = field(default_factory=list)
    subs: list[dict] = field(default_factory=list)
    clauses: list[dict] = field(default_factory=list)


@dataclass
class Statute:
    name: str
    long_title: str
    sections: list[Section]
    schedule: str
    schedule_rows: list[str]
    schedule_page: int

    def units(self, limit: int = 1200) -> list[Unit]:
        out: list[Unit] = []
        for s in self.sections:
            groups = [(x["n"], x["lead"], x["clauses"]) for x in s.subs] or [(None, s.lead, s.clauses)]
            if s.subs and s.lead:
                groups[0] = (groups[0][0], s.lead + groups[0][1], groups[0][2])
            for n, lead, clauses in groups:
                whole = _join(lead + [t for c in clauses for t in c["lines"]])
                if clauses and len(whole) > limit:
                    out += [Unit(s.n, n, c["l"], _join(lead), _join(c["lines"]), s.page) for c in clauses]
                else:
                    out.append(Unit(s.n, n, None, "", whole, s.page))
        return out

    def section_text(self, s: Section) -> str:
        return " ".join(u.lead + " " + u.text if u.clause == "a" else u.text for u in self.units(10 ** 9) if u.section == s.n)

    def clean_text(self) -> str:
        """The statute as running text: what the fixed-window baseline chunks."""
        parts = [self.long_title] + [f"Section {s.n}. {s.title}. {self.section_text(s)}" for s in self.sections] + [self.schedule]
        return "\n".join(re.sub(r"\s+", " ", p).strip() for p in parts if p)


def _join(lines: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def _next_clause(c: str) -> str:
    return "za" if c == "z" else c[:-1] + chr(ord(c[-1]) + 1)


def _is_pdf(lines: list[Line]) -> bool:
    return any(l.size for l in lines)


def _schedule(lines: list[Line]) -> tuple[str, list[str]]:
    """Rebuild a three-column schedule (Sl. No. | breach | penalty) into one row per breach."""
    marks = [l for l in lines if re.fullmatch(r"\d+\.", l.text)]
    head = next((l for l in lines if l.text == "Penalty"), None)
    if not marks or head is None or not _is_pdf(lines):
        text = _join([l.text for l in lines])
        return text, [text]
    split, rows = head.x - 30, []
    for i, m in enumerate(marks):
        end = marks[i + 1].y if i + 1 < len(marks) else float("inf")
        cell = [l for l in lines if l.page == m.page and m.y - 2 <= l.y < end - 2 and l is not m]
        rows.append(f"{m.text} {_join([l.text for l in cell if l.x < split])} Penalty: {_join([l.text for l in cell if l.x >= split])}")
    intro = _join([l.text for l in lines if (l.page, l.y) < (marks[0].page, marks[0].y - 2) and not re.fullmatch(r"\(\d+\)|Sl\. No\.|Penalty", l.text)])
    return "The Schedule. " + intro + " " + " ".join(rows), rows


def parse(path) -> Statute:
    lines = read_lines(path)
    pdf = _is_pdf(lines)
    body = [l for l in lines if not _NOISE.match(l.text) and (not pdf or (l.size >= 9.4 and l.font.startswith("Times")))]
    sections: list[Section] = []
    preamble: list[str] = []
    sched: list[Line] | None = None
    name, chapter, sec, sub, target, expect = "", "", None, None, None, "a"

    i = 0
    while i < len(body):
        ln, t = body[i], body[i].text
        i += 1
        if sections and _SCHED.match(t):
            sched = []
            continue
        if sched is not None:
            if _END.match(t):
                break
            sched.append(ln)
            continue
        if _CHAPTER.match(t):
            chapter = t
            if i < len(body) and body[i].text.isupper():
                chapter += " – " + body[i].text
                i += 1
            continue
        m = _SEC.match(t)
        if m and int(m[1]) == len(sections) + 1:
            sec = Section(int(m[1]), "", chapter, ln.page + 1, ln.y)
            sections.append(sec)
            sub, target, expect, t = None, sec.lead, "a", m[2]
        if sec is None:
            if _TITLE.match(t):
                name, preamble = t.title().replace(" Act,", " Act,"), []
            elif name:
                preamble.append(t)
            continue
        m = _SUB.match(t)
        if m and int(m[1]) == len(sec.subs) + 1:
            sub = {"n": int(m[1]), "lead": [], "clauses": []}
            sec.subs.append(sub)
            target, expect = sub["lead"], "a"
        m = _CLAUSE.match(t)
        if m and m[1] == expect:
            clause = {"l": expect, "lines": []}
            (sub["clauses"] if sub else sec.clauses).append(clause)
            target, expect = clause["lines"], _next_clause(expect)
        if t:
            target.append(t)

    # Marginal notes (8pt, in the page margins) are the section titles; match each to the section beside it.
    buf: list[Line] = []
    for l in lines:
        if not (7.4 <= l.size <= 8.6 and l.font.startswith("Times") and (l.x < 100 or l.x > 470)) or _SIDE_REF.match(l.text):
            continue
        buf.append(l)
        if l.text.endswith("."):
            near = [s for s in sections if s.page == buf[0].page + 1 and abs(s.y - buf[0].y) <= 15]
            if near:
                min(near, key=lambda s: abs(s.y - buf[0].y)).title = _join([b.text for b in buf]).rstrip(".")
            buf = []

    schedule, rows = _schedule(sched) if sched else ("", [])
    long_title = _join([p for p in preamble if not re.match(r"^\(NO\.|^\[\d", p) and not p.startswith("BE it enacted") and p != "follows:––"])
    return Statute(name or "Statute", f"{name}. Long title. {long_title}" if long_title else "", sections, schedule, rows,
                   (sched[0].page + 1) if sched else 0)


# ── chunkers ─────────────────────────────────────────────────────────────────
def _chunk(cid: str, text: str, **meta) -> dict:
    return {"id": cid, "text": re.sub(r"\s+", " ", text).strip(), **meta}


def _extras(st: Statute) -> list[dict]:
    out = []
    if st.long_title:
        out.append(_chunk("long-title", st.long_title, section=0, title="Long title", chapter="", page=1, provisions=["long title"]))
    if st.schedule:
        out.append(_chunk("schedule", st.schedule, section=0, title="Schedule", chapter="", page=st.schedule_page, provisions=["Schedule"]))
    return out


def _split_sentences(text: str, limit: int) -> list[str]:
    parts, cur = [], ""
    for sent in re.split(r"(?<=[.;:])\s+", text):
        if cur and len(cur) + len(sent) + 1 > limit:
            parts.append(cur)
            cur = ""
        cur = (cur + " " + sent).strip()
    return parts + ([cur] if cur else [])


def _assemble(pack: list[Unit]) -> str:
    """Text of consecutive units; the lead-in of a clause list is written once per parent sub-section."""
    body, parent = [], object()
    for u in pack:
        if u.clause and u.sub != parent:
            body.append(u.lead)
        parent = u.sub if u.clause else object()
        body.append(u.text)
    return " ".join(body)


def chunk_clause_aware(st: Statute, limit: int = 1200) -> list[dict]:
    chunks: list[dict] = []
    by_n = {s.n: s for s in st.sections}
    for n, sec in by_n.items():
        head = f"Section {n}. {sec.title}. "
        budget = limit - len(head)
        packs: list[list[Unit]] = []
        for u in [x for x in st.units(budget) if x.section == n]:
            if packs and len(_assemble(packs[-1] + [u])) <= budget:
                packs[-1].append(u)
            else:
                packs.append([u])
        for pack in packs:
            text = _assemble(pack)
            pieces = [text] if len(text) <= budget or len(pack) > 1 else _split_sentences(text, budget)
            for piece in pieces:
                chunks.append(_chunk(f"s{n}-{len([c for c in chunks if c['section'] == n]) + 1}", head + piece, section=n, title=sec.title,
                                     chapter=sec.chapter, page=sec.page, provisions=[u.provision for u in pack]))
    lt = _extras(st)
    return lt[:1] * bool(st.long_title) + chunks + [c for c in lt if c["id"] == "schedule"]


def chunk_sections(st: Statute) -> list[dict]:
    """Baseline: one chunk per whole section."""
    chunks = [_chunk(f"s{s.n}", f"Section {s.n}. {s.title}. {st.section_text(s)}", section=s.n, title=s.title, chapter=s.chapter, page=s.page,
                     provisions=[str(s.n)]) for s in st.sections]
    lt = _extras(st)
    return lt[:1] * bool(st.long_title) + chunks + [c for c in lt if c["id"] == "schedule"]


def chunk_fixed(st: Statute, size: int, overlap: float = 0.15) -> list[dict]:
    """Baseline: fixed character windows with overlap over the same cleaned text, cut at word boundaries."""
    text = st.clean_text().replace("\n", " ")
    step, chunks, start = int(size * (1 - overlap)), [], 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            end = text.rfind(" ", start, end) if text.rfind(" ", start, end) > start else end
        chunks.append(_chunk(f"w{len(chunks) + 1}", text[start:end], section=0, title="", chapter="", page=0, provisions=[]))
        if end >= len(text):
            break
        start = max(start + 1, text.rfind(" ", 0, start + step) + 1 if start + step < len(text) else start + step)
    return chunks
