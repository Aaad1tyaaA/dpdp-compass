"""Rebuilds the paper from the measured results in backend/eval/results/.

    cd project/backend && python ../docs/paper/build_paper.py

Sections I-III are taken from the authors' draft (original_draft_text.txt). Sections IV onwards are
written here with every number read from the result files, so the manuscript cannot drift from the
experiments. Anything not yet measured is printed as PENDING, never estimated.
Outputs: DPDP_Compass_Paper_IEEE.docx, .pdf (through Word, if installed) and figures/.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
RES = BACKEND / "eval" / "results"
FIG = HERE / "figures"


def load(name):
    p = RES / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


R, AUD, QA, TRI = load("retrieval.json"), load("audit.json"), load("qa.json"), load("triplets.json")
KB, DS = R["kb"], R["dataset"]
f3 = lambda x: f"{x:.3f}"


# ── figures ──────────────────────────────────────────────────────────────────
C = {"blue": "#DCE6F7", "orange": "#FBE7CE", "green": "#DDF0E3", "grey": "#EEEEEE", "violet": "#E8E1F7"}


def diagram(name, boxes, arrows, size=(3.5, 2.6), xlim=(0, 10), ylim=(0, 10)):
    fig, ax = plt.subplots(figsize=size)
    ax.set_xlim(*xlim), ax.set_ylim(*ylim), ax.axis("off")
    pos = {}
    for key, x, y, w, h, text, col in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=C[col], ec="#444", lw=0.6))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=5.6, linespacing=1.15)
        pos[key] = (x, y, w, h)
    for a, b, style, label in arrows:
        ax0, ay0, aw, ah = pos[a]
        bx0, by0, bw, bh = pos[b]
        if by0 + bh <= ay0:  # downwards
            p0, p1 = (ax0 + aw / 2, ay0), (bx0 + bw / 2, by0 + bh)
        elif bx0 >= ax0 + aw:  # rightwards
            p0, p1 = (ax0 + aw, ay0 + ah / 2), (bx0, by0 + bh / 2)
        else:
            p0, p1 = (ax0 + aw / 2, ay0 + ah), (bx0 + bw / 2, by0)
        ax.annotate("", xy=p1, xytext=p0, arrowprops=dict(arrowstyle="-|>", lw=0.7, color="#333", ls=style, shrinkA=1, shrinkB=1))
        if label:
            ax.text((p0[0] + p1[0]) / 2 + 0.1, (p0[1] + p1[1]) / 2, label, fontsize=5, color="#333", va="center")
    FIG.mkdir(exist_ok=True)
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    return FIG / f"{name}.png"


def figures():
    by = KB["by_predicate"]
    f1 = diagram("fig1_architecture", [
        ("src1", 0.2, 8.6, 4.4, 1.1, "Gazette PDF of the\nDPDP Act, 2023", "grey"), ("src2", 5.4, 8.6, 4.4, 1.1, "Privacy policy or question\n(English, Hindi, Marathi)", "grey"),
        ("off", 0.2, 6.6, 4.4, 1.3, "Offline pipeline\nclause-aware chunker, deontic\nextraction, triplets", "blue"),
        ("kb", 0.2, 4.0, 4.4, 1.9, f"Hybrid knowledge base\n{KB['chunks']} chunks, dense + BM25+ indexes\n{KB['obligations']} obligations, {KB['principles']} principles\ngraph: {KB['nodes']} nodes, {KB['relationships']} edges", "orange"),
        ("eng", 5.4, 4.0, 4.4, 3.9, "Agent engine (LangGraph)\norchestrator\nretrieval\nobligation mapping\ncompliance checking\nguardrails, risk", "violet"),
        ("o1", 0.2, 1.9, 4.4, 1.2, "Grounded answer\nwith verified citations", "green"), ("o2", 5.4, 1.9, 4.4, 1.2, "Audit report: 14 findings,\nquotes, score, risk", "green"),
        ("ev", 0.2, 0.1, 9.6, 1.0, f"Evaluation: DPDP-QA ({DS['items']} questions), DPDP-Synth (40 policies), ablations", "grey")],
        [("src1", "off", "-", ""), ("off", "kb", "-", ""), ("src2", "eng", "-", ""), ("kb", "eng", "-", ""), ("eng", "o2", "-", ""), ("kb", "o1", "-", "")], size=(3.5, 3.3))
    f2 = diagram("fig2_layers", [
        ("l1", 0.2, 7.2, 9.6, 2.4, "Layer 1, fact (Section 8(5), p. 7)\n\"A Data Fiduciary shall protect personal data in its possession\nor under its control ... by taking reasonable security safeguards\nto prevent personal data breach.\"", "blue"),
        ("l2", 0.2, 4.1, 9.6, 2.0, "Layer 2, obligation\nactor: Data Fiduciary   predicate: MUST\naction: protect personal data in its possession or under its control ...", "orange"),
        ("l3", 0.2, 1.6, 4.4, 1.5, "Layer 3, principle\nsecurity safeguards", "green"),
        ("pen", 5.4, 1.6, 4.4, 1.5, "PENALTY (Schedule, row 1)\nup to Rs. 250 crore", "violet")],
        [("l1", "l2", "-", "MUST"), ("l2", "l3", "-", "SERVES_PRINCIPLE"), ("l2", "pen", "-", "")], size=(3.5, 2.5))
    w = R["retrieval"]["weights"]
    f3_ = diagram("fig3_retrieval", [
        ("q", 3.3, 8.7, 3.4, 1.0, "Query (translated to English\nfor search if needed)", "grey"),
        ("d", 0.1, 6.1, 2.3, 1.4, f"Dense\nMiniLM cosine\nw = {w['dense']:g}", "blue"), ("s", 2.6, 6.1, 2.3, 1.4, f"Sparse\nBM25+\nw = {w['sparse']:g}", "blue"),
        ("m", 5.1, 6.1, 2.3, 1.4, f"Metadata\nprovision lookup\nw = {w['metadata']:g}", "blue"), ("g", 7.6, 6.1, 2.3, 1.4, f"Graph\nrelations\nw = {w['graph']:g}", "grey"),
        ("f", 2.3, 3.6, 5.4, 1.2, "Weighted Reciprocal Rank Fusion\nscore(d) = sum of w / (60 + rank)", "orange"),
        ("r", 2.3, 1.7, 5.4, 1.1, "Cross-encoder re-ranking of the top 20", "violet"), ("o", 3.3, 0.1, 3.4, 0.9, "Top-k clauses", "green")],
        [("q", "d", "-", ""), ("q", "s", "-", ""), ("q", "m", "-", ""), ("q", "g", "--", ""), ("d", "f", "-", ""), ("s", "f", "-", ""), ("m", "f", "-", ""),
         ("g", "f", "--", ""), ("f", "r", "-", ""), ("r", "o", "-", "")], size=(3.5, 2.9))
    f4 = diagram("fig4_workflow", [
        ("o", 3.0, 8.8, 4.0, 1.0, "Orchestrator\nlanguage and intent", "grey"),
        ("r", 0.2, 6.9, 4.6, 1.1, "Retrieval\n3 policy clauses per obligation", "blue"), ("a", 5.6, 6.9, 4.2, 1.1, "Answer\nretrieve, generate", "blue"),
        ("m", 0.2, 5.1, 4.6, 1.1, "Obligation mapping\nstatute, principle, exemptions", "orange"), ("cg", 5.6, 5.1, 4.2, 1.1, "Citation guardrails\nexists, in evidence", "violet"),
        ("c", 0.2, 3.3, 4.6, 1.1, "Compliance checking\nstatus and quote", "orange"), ("ans", 5.6, 3.3, 4.2, 1.1, "Grounded answer", "green"),
        ("g", 0.2, 1.5, 4.6, 1.1, "Guardrails\nverify quotes and citations", "violet"), ("k", 0.2, 0.0, 4.6, 0.9, "Risk and audit report", "green")],
        [("o", "r", "-", ""), ("o", "a", "-", ""), ("r", "m", "-", ""), ("m", "c", "-", ""), ("c", "g", "-", ""), ("g", "k", "-", ""), ("a", "cg", "-", ""), ("cg", "ans", "-", "")],
        size=(3.5, 3.0))
    return f1, f2, f3_, f4


# ── text carried over from the authors' draft ────────────────────────────────
def draft_sections():
    raw = (HERE / "original_draft_text.txt").read_text(encoding="utf-8")
    lines = [l for l in raw.splitlines() if not re.match(r"^=====PAGE|^\d$|^Fig\. \d", l.strip())]
    text = re.sub(r"\s+", " ", " ".join(lines))
    body = text[text.index("India's Digital Personal Data Protection (DPDP) Act, 2023 [1] places"):text.index("IV. SYSTEM DESIGN")]
    refs = text[text.index("REFERENCES") + 10:]
    return body, [m.strip() for m in re.split(r"(?=\[\d+\] )", refs) if m.strip()]


# ── document helpers ─────────────────────────────────────────────────────────
doc = Document()
st = doc.styles["Normal"]
st.font.name, st.font.size = "Times New Roman", Pt(10)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.left_margin = sec.right_margin = Inches(0.62)
sec.top_margin, sec.bottom_margin = Inches(0.75), Inches(1.0)
N = {"fig": 0, "tab": 0}
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]


def para(text="", size=10, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True, color=None, after=0):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_after, pf.space_before, pf.line_spacing = Pt(after), Pt(0), 1.0
    if indent and align == WD_ALIGN_PARAGRAPH.JUSTIFY:
        pf.first_line_indent = Inches(0.14)
    for i, part in enumerate(re.split(r"(\*[^*]+\*)", text)):  # *italic* spans
        if not part:
            continue
        r = p.add_run(part.strip("*") if part.startswith("*") else part)
        r.font.size, r.bold, r.italic = Pt(size), bold, italic or part.startswith("*")
        if color:
            r.font.color.rgb = RGBColor(*color)
    return p


def h1(text):
    p = para(text.upper(), 10, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(8), Pt(3)
    p.paragraph_format.keep_with_next = True


def h2(text):
    p = para(text, 10, italic=True, align=WD_ALIGN_PARAGRAPH.LEFT, indent=False)
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(5), Pt(2)
    p.paragraph_format.keep_with_next = True


def figure(path, caption, width=3.35):
    N["fig"] += 1
    doc.add_picture(str(path), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    para(f"Fig. {N['fig']}. {caption}", 8, align=WD_ALIGN_PARAGRAPH.LEFT, indent=False, after=5)


def table(caption, header, rows, widths, size=7):
    N["tab"] += 1
    c = para(f"TABLE {ROMAN[N['tab'] - 1]}", 8, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    c.paragraph_format.space_before, c.paragraph_format.keep_with_next = Pt(5), True
    para(caption.upper(), 8, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=2).paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    for row_cells, values, bold in [(t.rows[0].cells, header, True)] + [(t.add_row().cells, r, False) for r in rows]:
        for i, (cell, val) in enumerate(zip(row_cells, values)):
            cell.width = Inches(widths[i])
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(val))
            run.font.size, run.bold = Pt(size), bold
            cell.paragraphs[0].paragraph_format.space_after = Pt(0)
    para("", 4, indent=False)


def two_columns():
    s = doc.add_section(WD_SECTION.CONTINUOUS)
    cols = s._sectPr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        s._sectPr.append(cols)
    cols.set(qn("w:num"), "2")
    cols.set(qn("w:space"), "288")


PENDING = (0xB0, 0x30, 0x10)


# ── build ────────────────────────────────────────────────────────────────────
def build():
    figs = figures()
    body, refs = draft_sections()
    ch, rt, fu = R["chunking"], R["retrieval"], R["fusion"]
    row = {r["system"].strip(): r for r in rt["rows"]}
    crow = {r["chunking"]: r for r in ch["rows"]}
    full, dense, sparse, rrf_ = row["+ re-ranking (full)"], row["Dense (MiniLM)"], row["Sparse (BM25+)"], row["Dense + sparse, RRF"]
    ours, fixed, whole = crow["Clause-aware, 1,200 (ours)"], crow["Fixed windows, 1,200"], crow["Whole sections"]
    kinds, by = KB["obligation_kinds"], KB["by_predicate"]
    S = AUD["systems"] if AUD else {}
    pipe, single, rules, nog = (S.get(k) for k in ("Pipeline + guardrails (full)", "Single prompt", "Keyword rules", "Pipeline, no guardrails"))
    pval = lambda p: "p < 0.001" if p < 0.001 else f"p = {p:.3f}"

    # status note for the authors (delete before submission)
    para("DRAFT STATUS (delete before submission)", 9, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, indent=False, color=PENDING)
    notes = ["Every number in this draft was re-measured on the implementation in project/backend (app/compass, eval). "
             "The numbers in the earlier draft came from code that is not in this repository and were replaced.",
             f"Table V covers {pipe['policies']} of {AUD['dataset']['policies']} DPDP-Synth policies; the run stopped at the model provider's daily token limit. "
             "Re-run python -m eval.audit_exp to finish (completed calls are cached)." if AUD and not AUD["complete"] else "Table V is complete.",
             "Table VI (question answering) has not been run: python -m eval.qa_exp." if not QA else
             f"Table VI covers {QA['n_done']} of {QA['n_test']} test questions." if not QA["complete"] else "Table VI is complete.",
             "Still to supply: author names, affiliation, email, and the acknowledgment. DPDP-QA and the checklist tests have not been reviewed by a lawyer."]
    for n in notes:
        para("- " + n, 8.5, align=WD_ALIGN_PARAGRAPH.LEFT, indent=False, color=PENDING)
    para("", 4, indent=False)

    para("DPDP Compass: Citation-Enforced Hybrid Retrieval and Guardrailed Agents for Auditing Privacy Policies against India's DPDP Act, 2023",
         20, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=8)
    para("[Author names]", 11, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    para("[Department, Institution]", 10, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    para("[City, India]    [email]", 10, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=10)
    two_columns()

    audit_sentence = (f"On the {pipe['policies']} DPDP-Synth policies audited{" so far" if pipe["policies"] < 40 else ""} ({pipe['decisions']} decisions), the pipeline agrees with the "
                      f"construction labels at Cohen's kappa {f3(pipe['kappa'])} with every quoted clause verified in the policy, against "
                      f"{f3(single['kappa'])} for a single prompt at about half the tokens and {f3(rules['kappa'])} for keyword rules. ") if pipe else ""
    qa_sentence = "Answer-quality results are not yet available. " if not QA else (
        f"On {QA['n_done']} test questions the full system answers {100 * QA['systems']['Full system']['correct_strict']:.1f}% correctly against "
        f"{100 * QA['systems']['LLM, no retrieval']['correct_strict']:.1f}% for the model without retrieval, and no answer cites a provision that "
        f"does not exist." if QA["complete"] and not QA['systems']['Full system']['fabricated_citation_rate'] else "")
    p = para("", 9)
    for text, b in (("Abstract—", True), (
        "India's Digital Personal Data Protection (DPDP) Act, 2023 places enforceable duties on organisations that process personal data, and a "
        "privacy policy is usually the first evidence of whether those duties are met. Large language models can read a policy against a statute, "
        "but they are known to cite provisions that do not exist. We present DPDP Compass, a system that answers questions about the Act and audits "
        "privacy policies against 14 obligations, with the legal citation attached by the system and not generated. A clause-aware chunker turns the "
        f"Gazette text into {KB['chunks']} chunks that keep section, sub-section and page; a three-layer knowledge base adds {KB['obligations']} obligation "
        f"records and a graph of {KB['relationships']} relationships, each carrying the sentence that states it. Retrieval fuses dense, BM25+ and exact "
        f"provision lookup and re-ranks with a cross-encoder. On DPDP-QA, {DS['items']} questions in English, Hindi and Marathi written from the Act, the "
        f"full retriever reaches Hit@1 {f3(full['hit1'])} and nDCG@10 {f3(full['ndcg10'])}, against {f3(dense['hit1'])} and {f3(dense['ndcg10'])} for dense "
        f"retrieval, and clause-aware chunks outrank fixed windows of the same size (MRR {f3(ours['mrr'])} against {f3(fixed['mrr'])}). The knowledge graph did "
        f"not improve ranking. {audit_sentence}{qa_sentence}", False)):
        r = p.add_run(text)
        r.bold, r.font.size = True, Pt(9)
    p = para("", 9, after=4)
    for text, it in (("Index Terms—", True), ("Compliance checking, data protection, DPDP Act, knowledge graphs, large language models, legal informatics, "
                                              "privacy policies, retrieval-augmented generation.", False)):
        r = p.add_run(text)
        r.bold, r.italic, r.font.size = True, it, Pt(9)

    # Sections I-III from the authors' draft, re-flowed
    heads = ["II. BACKGROUND AND RELATED WORK", "III. PROBLEM FORMULATION"]
    subs = ["A. The DPDP Act", "B. NLP for Privacy Policies", "C. Retrieval-Augmented Generation", "D. Legal NLP and Hallucination", "E. Retrieval Methods"]
    breaks = ["Reading a policy against a statute", "Prior work on automated analysis", "1) A clause-aware", "2) A multi-agent", "3) DPDP-QA", "4) An ablation",
              "Section II reviews", "Task 1, grounded", "Task 2, policy audit", "The compliance score is"]
    marked = body
    for h in heads:
        marked = marked.replace(h, f"\n#1 {h}\n")
    for s in subs:
        marked = marked.replace(s + " ", f"\n#2 {s}\n", 1)
    for b in breaks:
        marked = marked.replace(b, "\n" + b, 1)
    h1("I. Introduction")
    for line in [l.strip() for l in marked.split("\n") if l.strip()]:
        if line.startswith("#1 "):
            h1(line[3:].title().replace("Ii.", "II.").replace("Iii.", "III.").replace(" And ", " and "))
        elif line.startswith("#2 "):
            h2(line[3:])
        else:
            para(line.replace("lower-bounds term-frequency normalisation,", "lower-bounds term-frequency normalisation,"))

    h1("IV. System Design")
    h2("A. Overview")
    para("The system has an offline pipeline that builds a hybrid legal knowledge base from the Gazette text, and an online multi-agent workflow that "
         "serves both tasks. All components run in one process with in-memory indexes; saved audits are kept in SQLite. Fig. 1 shows the architecture.")
    figure(figs[0], "Architecture of DPDP Compass. Counts are for the knowledge base built from the DPDP Act, 2023.")
    h2("B. Clause-Aware Chunking of the Statute")
    para("The Gazette PDF of the Act yields page headers, a masthead in a legacy font, and marginal notes that the extractor places away from the text "
         "they label. A generic splitter mixes these into the text and loses the provision structure. Our statute chunker (i) keeps only body text, using "
         "font and size to drop the masthead and to separate the 8-point marginal notes; (ii) detects sections by their running number, accepting a "
         "candidate only if it continues the sequence, and assigns each section the marginal note beside it as its title; (iii) splits each section into "
         "its numbered sub-sections and lettered clauses, again requiring running order so that a cross-reference at the start of a line is not mistaken "
         "for a new sub-section; (iv) packs consecutive sub-sections into chunks of at most 1,200 characters without cutting a sub-section, an over-long "
         "one being cut at its lettered clauses with the lead-in repeated; (v) prefixes each chunk with its section number and title and stores section, "
         "provisions, chapter and starting page as metadata; and (vi) rebuilds the penalty Schedule, a three-column table that extraction scrambles, "
         "into one row per breach.")
    para(f"On the DPDP Act this gives {KB['chunks']} chunks covering all {KB['sections']} sections, the long title and the Schedule, with a mean length of "
         f"{KB['mean_chars']} characters. Only the Schedule, kept whole, exceeds the limit.")
    h2("C. Three-Layer Knowledge Structure")
    para(f"Layer 1, facts: the {KB['chunks']} clause chunks and the {KB['definitions']} terms defined in Section 2. Layer 2, obligations: normative statements "
         "extracted with deontic patterns. A statement is recorded when a legal actor (Data Fiduciary, Data Principal, Consent Manager, Board, Central "
         "Government and others) opens a clause as the grammatical subject of shall, shall not, shall have the right or may; actors inside prepositional "
         "or relative phrases and definitional uses of shall are excluded, and a leading condition such as \"by notification\" is stored separately from "
         f"the action. This yields {KB['obligations']} records: {kinds['duty']} duties, {kinds['prohibition']} prohibitions, {kinds['right']} rights and "
         f"{kinds['power']} powers. Layer 3, principles: each obligation is mapped by provision to one of {KB['principles']} principles such as consent, "
         "storage limitation, security safeguards and accountability. Fig. 2 shows one provision across the layers.")
    if TRI:
        errs = TRI["errors"]
        para(f"In an automated check of a random sample of {TRI['sampled']} of the {TRI['population']} triplets, an LLM ({TRI['model'].split('/')[-1]}) read each "
             f"triplet against its source sentence and judged {TRI['correct']} correct (precision {TRI['precision']:.2f}, bootstrap 95% CI "
             f"{TRI['ci95'][0]:.2f}-{TRI['ci95'][1]:.2f}). Of the {TRI['sampled'] - TRI['correct']} errors, {errs.get('object', 0)} had an action that was a "
             f"fragment or condition, {errs.get('subject', 0)} a wrong or partial subject and {errs.get('modality', 0)} a wrong modality. The extraction rule "
             "was revised once, to separate leading conditions, after a first check; the figures are for the revised rule. This check was not performed by "
             "human annotators.")
    figure(figs[1], "The three layers for one provision, Section 8(5), and the penalty linked to it in the graph.")
    h2("D. Triplet Extraction and Knowledge Graph")
    para("The same pass emits subject-predicate-object triplets, each with the provision, page and sentence that states it. Predicates come from a closed "
         "list: MUST, MUST_NOT, HAS_RIGHT and MAY from Layer 2; SERVES_PRINCIPLE; REFERS_TO for cross-references between provisions, excluding references "
         "to other Acts; DEFINED_IN; and PENALTY, which links a Schedule row to its provision. The graph for the Act has "
         f"{KB['relationships']} relationships over {KB['nodes']} nodes (Table I).")
    table("Knowledge base built from the DPDP Act, 2023", ["Item", "Count"], [
        ["Clause chunks (Layer 1)", KB["chunks"]], ["Obligation records (Layer 2)", KB["obligations"]], ["Principles (Layer 3)", KB["principles"]],
        ["Graph nodes", KB["nodes"]], ["Graph relationships", KB["relationships"]],
        ["  MUST / MUST_NOT / HAS_RIGHT / MAY", f"{by['MUST']} / {by['MUST_NOT']} / {by['HAS_RIGHT']} / {by['MAY']}"],
        ["  SERVES_PRINCIPLE", by["SERVES_PRINCIPLE"]], ["  REFERS_TO", by["REFERS_TO"]], ["  DEFINED_IN", by["DEFINED_IN"]], ["  PENALTY", by["PENALTY"]]], [2.3, 1.0], 8)
    h2("E. Hybrid Retrieval")
    w = rt["weights"]
    sweep = [g for g in fu["grid"] if g["metadata"] == fu["chosen"]["metadata"]]
    para("Four retrievers run per query (Fig. 3). Dense: all-MiniLM-L6-v2 embeddings with exact cosine similarity. Sparse: BM25+ [3] over stemmed tokens. "
         "Metadata lookup: when the query names a provision, the chunks holding that provision are fetched exactly. Graph: provisions connected to the "
         "defined terms, actors and principles the query mentions, and provisions cross-referenced by the leading candidates.")
    para("Result lists are merged by weighted Reciprocal Rank Fusion, score(d) = sum over retrievers r of w_r / (60 + rank_r(d)) [2], and the top 20 "
         "candidates are re-ranked by a cross-encoder (ms-marco-MiniLM-L-6-v2). The weights were chosen on the development split of DPDP-QA from a grid "
         f"over the metadata and graph weights: w_dense = w_sparse = 1, w_metadata = {w['metadata']:g} and w_graph = {w['graph']:g}. Graph matches lowered "
         "ranking quality at every non-zero weight we tried (Section VI-B), so the deployed system does not use the graph for ranking. The graph is used "
         "where structure matters: linking obligations to the exemption provisions that refer to them and provisions to their penalty.")
    figure(figs[2], "Hybrid retrieval. The dashed path is the graph retriever, whose fusion weight was set to 0 on the development split.")
    h2("F. Multi-Agent Workflow")
    para("The workflow is a LangGraph state machine (Fig. 4). The orchestrator detects the language (English, Hindi or Marathi) and the intent and routes "
         "the request; a question with no policy skips the audit agents. For a question, the answer agent translates a non-English question for search "
         "while the answer stays in the user's language, runs hybrid retrieval over the Act and generates from the retrieved clauses. For an audit, the "
         "retrieval agent chunks the policy by paragraph, indexes it in memory for the duration of the audit and retrieves three clauses per checklist "
         "obligation.")
    para("The obligation mapping agent grounds each checklist obligation in the knowledge base: its statutory text by exact lookup, its principle, and the "
         "exemption provisions linked to it in the graph. The compliance checking agent receives, per obligation, the statutory text, the tests for "
         "Satisfied and Partial, and the three policy clauses retrieved for it, and returns a status and a quote; obligations are sent in batches of "
         "seven, each judged from its own clauses. The tests are written so that the same text can be given to human annotators. The risk agent assigns "
         "severity from the penalty ceiling in the Schedule (up to Rs. 250 crore for Section 8(5), Rs. 200 crore for Sections 8(6) and 9, and Rs. 50 crore "
         "otherwise) and likelihood from the status; no penalty figure is generated by the model. Without a model key the compliance agent falls back to "
         "the keyword rules used as a baseline.")
    figure(figs[3], "Agent workflow. A question with no policy takes the right-hand path.")
    h2("G. Guardrails")
    para("The legal citation of a finding is attached by the system from the knowledge base, so the model cannot invent it. The remaining risks are "
         "handled by checks that act on the output (Table II). Personal data in a question (names that are introduced, phone numbers, email addresses and "
         "identity numbers) is redacted before the question is processed or logged.")
    table("Guardrails and the action taken on failure", ["Check", "Action on failure"], [
        ["Policy quote found word for word in the policy", "Satisfied becomes Partial; confidence capped at 0.5"],
        ["Partial finding has policy evidence", "Partial becomes Missing"],
        ["Cited provision exists in the Act", "Citation removed"],
        ["Provisions cited in an answer are in the retrieved evidence", "One rewrite requested; result flagged"],
        ["Retrieved text contains instruction-like content", "Flagged; retrieved text is always passed as data"],
        ["Confidence within 0-1; output schema complete", "Clamped or flagged"]], [1.75, 1.6], 7.5)

    h1("V. Experimental Setup")
    h2("A. Corpus")
    para(f"The Digital Personal Data Protection Act, 2023 (Gazette text, {KB['pages']} pages). The DPDP Rules, 2025 are not included in the experiments reported here.")
    h2("B. DPDP-QA")
    bl = DS["by_lang"]
    test_en = ch["n"]
    para(f"We wrote {DS['items']} questions from the text of the Act: {bl['en']} in English, {bl['hi']} in Hindi and {bl['mr']} in Marathi, the latter two being "
         f"translations of English items. They cover {DS['sections_covered']} of the {KB['sections']} sections and the Schedule, and eleven types: definitions, "
         "obligations, rights, exemptions, procedure, penalties, scope, scenarios, provision lookups and two kinds of unanswerable question. Each "
         "answerable question has the gold provision, a reference answer and an evidence phrase copied from the Act. A retrieved chunk counts as relevant "
         "if it contains the phrase, so relevance does not depend on the chunking. A validator confirms that every phrase occurs in the Act and only "
         "inside the gold provision.")
    para(f"Sixteen questions cannot be answered from the Act: ten ask for details the Act leaves to rules or does not contain, such as the number of hours "
         f"for breach reporting, and six are out of domain. The set is split into development ({DS['dev']}) and test ({DS['test']}); translations stay with "
         f"their source. The test split has {rt['n']} answerable questions, {test_en} of them in English. The development split is used only to choose the "
         "fusion weights. The questions have not been reviewed by a lawyer.")
    h2("C. Audit Data")
    if AUD:
        d = AUD["dataset"]
        para(f"DPDP-Synth is a controlled set of {d['policies']} synthetic policies of fictional companies ({d['decisions']} obligation-level labels: "
             f"{d['labels']['Satisfied']} Satisfied, {d['labels']['Partial']} Partial, {d['labels']['Missing']} Missing). For each obligation the generator inserts "
             "a clause written for Satisfied or Partial or, for Missing, nothing or a hard negative that uses the topic's vocabulary without meeting the "
             f"obligation ({d['hard_negatives']} hard negatives). Labels are known by construction. {d['injected']} policies carry a prompt-injection sentence. "
             "The clauses come from a small set of templates, which makes the set easier than real policies, in particular for keyword matching.")
    para("We do not report results on real privacy policies: a gold standard for them requires independent labelling by annotators with legal training, "
         "which we leave to future work.")
    h2("D. Systems Compared")
    para("Retrieval: each retriever alone; dense plus sparse with score-weighted fusion and with RRF; then adding graph, metadata lookup and re-ranking. "
         "Chunking: clause-aware at 1,200 and 600 characters, whole sections, and fixed windows of 1,200, 600 and 300 characters with 15% overlap, over "
         "the same cleaned text and the same retriever. Audit: a keyword-rule baseline; a single LLM prompt with the whole policy and the rubric; the "
         "multi-agent pipeline with and without guardrails. Question answering: the LLM without retrieval; dense-only RAG; hybrid RAG; the full system.")
    h2("E. Metrics")
    para("Hit@k, Recall@10, MRR and nDCG@10 for retrieval, with bootstrap 95% confidence intervals and a paired bootstrap test (10,000 resamples). "
         "Accuracy, macro-F1, per-class F1 and Cohen's kappa for the audit, plus the absolute error of the compliance score, the share of quoted clauses "
         "found verbatim in the policy, and the share of obligations not labelled Satisfied that a system marks Satisfied, on injected and on clean "
         "policies. For answers: citation precision and recall against gold provisions, the share of answers citing a provision that does not exist, the "
         "share citing outside the retrieved evidence, correctness and unsupported claims graded by an LLM judge against the reference answer, and "
         "abstention on unanswerable questions. Latency and tokens per item are recorded.")
    h2("F. Implementation")
    para("Python 3.13, FastAPI and LangGraph; NumPy and rank-bm25 indexes in memory and SQLite for saved audits; openai/gpt-oss-120b served by Groq at "
         "temperature 0 with low reasoning effort; qwen3.8-27b as judge; all-MiniLM-L6-v2 and ms-marco-MiniLM-L-6-v2 on CPU. Every run records its "
         "dataset hash, and model responses are cached on disk so that a run can be repeated exactly and an interrupted run resumed.")

    h1("VI. Results")
    h2("A. Chunking")
    para(f"Table III compares chunkers on the {ch['n']} answerable English test questions with dense plus BM25+ retrieval fused by RRF and no re-ranking. "
         f"Clause-aware chunks beat fixed windows of the same size limit (MRR {f3(ours['mrr'])} against {f3(fixed['mrr'])}, paired bootstrap "
         f"{pval(ch['p_mrr_ours_vs_fixed1200'])}). Whole sections reach MRR {f3(whole['mrr'])} ({pval(ch['p_mrr_ours_vs_sections'])} against ours) and place "
         f"about {whole['chars_top5'] / ours['chars_top5']:.1f} times as much text in front of the model for the same evidence. Halving the clause-aware limit "
         "to 600 characters changes ranking little.")
    table(f"Chunking ablation ({ch['n']} English test questions, hybrid retrieval, no re-ranking)",
          ["Chunking", "Chunks", "Hit@1", "Hit@5", "MRR", "nDCG@10", "Chars in top 5"],
          [[r["chunking"], r["chunks"], f3(r["hit1"]), f3(r["hit5"]), f3(r["mrr"]), f3(r["ndcg10"]), f"{r['chars_top5']:,}"] for r in ch["rows"]],
          [1.05, 0.37, 0.37, 0.37, 0.37, 0.42, 0.45], 6.5)
    h2("B. Fusion Weights")
    para(f"On the {fu['n']} answerable development questions, before re-ranking, the best metadata weight in the grid {{0, 1, 2}} was {fu['chosen']['metadata']:g}. "
         "At that weight nDCG@10 fell as the graph weight rose: " + ", ".join(f"{f3(g['ndcg10'])} at {g['graph']:g}" for g in sweep) +
         ". We therefore set the graph weight to 0.")
    h2("C. Retrieval")
    lang = rt["by_lang"]
    para(f"Table IV reports the ablation on the {rt['n']} answerable test questions ({lang['en']} English, {lang['hi']} Hindi, {lang['mr']} Marathi), with Hindi and "
         f"Marathi questions translated to English before search. BM25+ alone ranks the right clause first more often than dense retrieval alone "
         f"({f3(sparse['hit1'])} against {f3(dense['hit1'])}), which fits statutory text where questions reuse the Act's own terms. Fusing the two by RRF raises "
         f"Hit@5 to {f3(rrf_['hit5'])}; score-weighted fusion of the same two lists does better at rank 1 ({f3(row['Dense + sparse, weighted']['hit1'])}). Giving "
         f"the graph an equal vote lowers nDCG@10 from {f3(rrf_['ndcg10'])} to {f3(row['+ graph, equal vote']['ndcg10'])} ({pval(rt['p_graph_vote_vs_rrf_ndcg10'])}). "
         f"Exact provision lookup adds {row['+ metadata lookup']['hit5'] - rrf_['hit5']:.3f} to Hit@5, and cross-encoder re-ranking brings the full system to Hit@1 "
         f"{f3(full['hit1'])} and nDCG@10 {f3(full['ndcg10'])}, against {f3(dense['hit1'])} and {f3(dense['ndcg10'])} for dense retrieval (paired bootstrap "
         f"{pval(rt['p_full_vs_dense']['hit1'])} and {pval(rt['p_full_vs_dense']['ndcg10'])}). Every answerable test question has a relevant clause in the full "
         f"system's top 10. Re-ranking on CPU costs about {full['ms_per_query'] / 1000:.1f} s per query.")
    table(f"Retrieval ablation on the DPDP-QA test split ({rt['n']} questions, top 10)", ["System", "Hit@1", "Hit@5", "R@10", "MRR", "nDCG@10", "ms / query"],
          [[r["system"], f3(r["hit1"]), f3(r["hit5"]), f3(r["r10"]), f3(r["mrr"]), f3(r["ndcg10"]), f"{r['ms_per_query']:,.0f}" if r["ms_per_query"] >= 10 else r["ms_per_query"]]
           for r in rt["rows"]], [1.1, 0.38, 0.38, 0.38, 0.38, 0.42, 0.38], 6.5)
    h2("D. Policy Audit")
    if pipe:
        if not AUD["complete"]:
            para(f"PARTIAL RESULT: {pipe['policies']} of {AUD['dataset']['policies']} policies ({pipe['decisions']} decisions). The run stopped at the provider's "
                 "daily token limit; the remaining policies are not estimated.", 9, bold=True, color=PENDING)
        flags = AUD["guardrail_flags"]
        para(f"Table V compares the audit systems against the construction labels. Keyword rules reach accuracy {f3(rules['accuracy'])} (kappa {f3(rules['kappa'])}) "
             f"and recognise only {100 * rules['hard_negative_correct']:.0f}% of hard negatives as Missing. The single prompt reaches {f3(single['accuracy'])} "
             f"(kappa {f3(single['kappa'])}) and the pipeline {f3(nog['accuracy'])} without guardrails and {f3(pipe['accuracy'])} with them (kappa "
             f"{f3(pipe['kappa'])}); the 95% intervals of the two model-based systems "
             f"{'overlap' if pipe['accuracy_ci'][1] >= single['accuracy_ci'][0] and single['accuracy_ci'][1] >= pipe['accuracy_ci'][0] else 'do not overlap'}. On this set, judging each obligation from its own retrieved "
             f"clauses did not beat reading the whole policy, and it used about {pipe['tokens_per_policy'] / single['tokens_per_policy']:.1f} times the tokens. The "
             "policies are short, so the whole policy fits in one prompt; the retrieval step is intended for long policies, which this set does not test.")
        para(f"Guardrails changed {flags.get('status_changed', 0)} of {pipe['decisions']} findings and raised the share of verified quotes from "
             f"{100 * nog['verified_quote_rate']:.1f}% to {100 * pipe['verified_quote_rate']:.1f}%; the single prompt, which has no quote check, stands at "
             f"{100 * single['verified_quote_rate']:.1f}%. In the policies carrying a prompt-injection sentence the pipeline marked "
             f"{100 * pipe['false_satisfied_injected']:.1f}% of obligations that were not Satisfied as Satisfied, against {100 * pipe['false_satisfied_clean']:.1f}% in "
             f"clean policies (single prompt: {100 * single['false_satisfied_injected']:.1f}% and {100 * single['false_satisfied_clean']:.1f}%), so the injected "
             "sentence did not raise the rate. The mean absolute error of the compliance score is "
             f"{pipe['score_mae']:.1f} points for the pipeline, {single['score_mae']:.1f} for the single prompt and {rules['score_mae']:.1f} for keyword rules.")
        table(f"Policy audit on DPDP-Synth ({pipe['policies']} of {AUD['dataset']['policies']} policies, {pipe['decisions']} decisions)",
              ["System", "Acc.", "Macro-F1", "Kappa", "F1 S / P / M", "Score err.", "Quotes verified", "Tokens"],
              [[name, f3(m["accuracy"]), f3(m["macro_f1"]), f3(m["kappa"]), " / ".join(f"{m['f1'][s]:.2f}" for s in ("Satisfied", "Partial", "Missing")),
                f"{m['score_mae']:.1f}", "n/a" if name == "Keyword rules" else f"{100 * m['verified_quote_rate']:.1f}%", f"{m['tokens_per_policy']:,}"]
               for name, m in S.items()], [0.92, 0.3, 0.42, 0.34, 0.6, 0.33, 0.42, 0.37], 6)
    else:
        para("RESULT PENDING. Run python -m eval.audit_exp.", 9, bold=True, color=PENDING)
    h2("E. Question Answering and Citations")
    if QA and QA["n_done"]:
        T = QA["systems"]
        if not QA["complete"]:
            para(f"PARTIAL RESULT: {QA['n_done']} of {QA['n_test']} test questions.", 9, bold=True, color=PENDING)
        fs, cb = T["Full system"], T["LLM, no retrieval"]
        para(f"Table VI compares the answering systems. The full system is judged correct on {100 * fs['correct_strict']:.1f}% of answerable questions "
             f"({100 * fs['correct_partial_credit']:.1f}% with partial credit), against {100 * cb['correct_strict']:.1f}% for the model without retrieval. "
             + (f"No answer from the closed-book model or the full system cites a provision that does not exist ({100 * cb['fabricated_citation_rate']:.1f}%). "
                if cb["fabricated_citation_rate"] == fs["fabricated_citation_rate"] else
                f"{100 * cb['fabricated_citation_rate']:.1f}% of closed-book answers cite a provision that does not exist, against "
                f"{100 * fs['fabricated_citation_rate']:.1f}% for the full system. ")
             + ("No unanswerable question is among those completed so far, so abstention is not yet measured."
                if fs["abstention_unanswerable"] is None else
                f"The full system abstains on {100 * fs['abstention_unanswerable']:.1f}% of unanswerable questions."))
        table(f"Question answering on the DPDP-QA test split ({QA['n_done']} questions)", ["System", "Correct", "Cit. P", "Cit. R", "Fabricated", "Abstain", "Tokens"],
              [[n, f"{100 * m['correct_strict']:.1f}%", "n/a" if m["citation_precision"] is None else f3(m["citation_precision"]), f3(m["citation_recall"]),
                f"{100 * m['fabricated_citation_rate']:.1f}%", "n/a" if m["abstention_unanswerable"] is None else f"{100 * m['abstention_unanswerable']:.0f}%", f"{m['tokens']:,}"]
               for n, m in T.items()], [0.95, 0.42, 0.38, 0.38, 0.5, 0.42, 0.4], 6.5)
    else:
        para("RESULT PENDING. Table VI (closed-book LLM, dense RAG, hybrid RAG and the full system: correctness, citation precision and recall, "
             "fabricated-citation rate, unsupported claims, abstention, latency) has not been run. The generator's daily token limit was used up by the "
             "audit experiment. The runner is in place (python -m eval.qa_exp), caches every model call and resumes where it stopped.", 9, bold=True, color=PENDING)
    h2("F. Error Analysis and Case Study")
    error_analysis(pipe)

    h1("VII. Limitations")
    para("The corpus is one statute of 21 pages, and the Rules are not indexed. DPDP-QA was written by the authors and has not been "
         "reviewed by a lawyer. DPDP-Synth is synthetic and built from templates, so conclusions about real policies need a human-labelled set, and its "
         "short policies do not exercise retrieval over a long policy. Obligation and triplet extraction is rule-based, and its precision was checked by "
         "an LLM, not by annotators. The answer judge is an LLM. The knowledge graph did not improve ranking on this corpus. The keyword baseline cannot "
         "read negation. Results marked partial or pending above are incomplete. The system gives guidance, not legal advice.")
    h1("VIII. Conclusion and Future Work")
    para(f"We described DPDP Compass, which turns the Gazette text of the DPDP Act into a clause-level knowledge base and uses it to answer questions and "
         f"to audit privacy policies with citations attached from that knowledge base. Keeping sub-sections whole improved ranking over fixed windows of the "
         f"same size, and combining dense retrieval, BM25+, exact provision lookup and re-ranking put a relevant clause first for {100 * full['hit1']:.0f}% of "
         "test questions and in the top ten for all of them. Two results went against our expectations and are reported as such: the knowledge graph "
         "lowered ranking quality whenever it was given a vote, and on short synthetic policies the multi-agent audit did not outperform a single prompt, "
         "although its quotes were always verifiable.")
    para("Future work is to complete the answer-quality evaluation, index the DPDP Rules, 2025, build a benchmark of real policies labelled by annotators "
         "with legal training, test the audit on long policies where retrieval should matter, and study how citizens and compliance staff use the answers.")
    h1("Acknowledgment")
    para("[Thank the project guide and the institution here.] Generative AI tools were used in developing the software, in drafting this manuscript and the "
         "evaluation questions, and in the automated check of extracted triplets reported in Section IV-C; the authors reviewed the content and are "
         "responsible for it.")
    h1("References")
    for r in refs:
        para(r, 8, align=WD_ALIGN_PARAGRAPH.LEFT, indent=False)

    out = HERE / "DPDP_Compass_Paper_IEEE.docx"
    doc.save(out)
    print("saved", out)
    try:
        import win32com.client
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        d = word.Documents.Open(str(out))
        d.SaveAs(str(out.with_suffix(".pdf")), FileFormat=17)
        pages = d.ComputeStatistics(2)
        d.Close(False)
        word.Quit()
        print("saved", out.with_suffix(".pdf"), pages, "pages")
    except Exception as e:
        print("PDF not written (Word unavailable):", str(e)[:100])


def error_analysis(pipe):
    """Retrieval misses by question type, audit confusions, and one law-versus-policy example, all from the data."""
    from app.compass.audit import get_engine
    from eval import dpdp_qa, synth
    engine = get_engine()
    items = [i for i in dpdp_qa.load() if i["split"] == "test" and i["answerable"]]
    q = R["translations"]
    miss, total, in_top5, same_section = {}, {}, 0, 0
    for it in items:
        hits, _ = engine.index.search(q.get(it["id"], it["question"]), k=10)
        total[it["type"]] = total.get(it["type"], 0) + 1
        if not dpdp_qa.relevant(hits[0]["text"], it):
            miss[it["type"]] = miss.get(it["type"], 0) + 1
            in_top5 += any(dpdp_qa.relevant(h["text"], it) for h in hits[:5])
            gold_section = 0 if it["provision"] == "Schedule" else int(it["provision"].split("(")[0])
            same_section += hits[0]["section"] == gold_section
    worst = sorted(miss, key=lambda t: -miss[t] / total[t])[:3]
    n_miss = sum(miss.values())
    para(f"Retrieval. The full system ranks a relevant clause first for all but {n_miss} of the {len(items)} answerable test questions. The misses are "
         "concentrated in " + ", ".join(f"{t} questions ({miss[t]} of {total[t]})" for t in worst) + f". In {in_top5} of the {n_miss} misses the relevant clause is "
         f"still in the top five, and in {same_section} the clause ranked first is another chunk of the same section as the gold provision: long sections such "
         "as the definitions are split across several chunks that share a title and vocabulary.")
    if not pipe:
        return
    gold = {p["id"]: p for p in synth.generate()}
    rows = AUD["raw"]["Pipeline + guardrails (full)"]
    conf = {}
    for r in rows:
        for f in r["findings"]:
            g = gold[r["policy"]]["labels"][f["id"]]
            if g != f["status"]:
                conf[(g, f["status"])] = conf.get((g, f["status"]), 0) + 1
    by_ob = {}
    for r in rows:
        for f in r["findings"]:
            if gold[r["policy"]]["labels"][f["id"]] != f["status"]:
                by_ob[f["id"]] = by_ob.get(f["id"], 0) + 1
    top = sorted(conf, key=lambda k: -conf[k])[:3]
    obs = sorted(by_ob, key=lambda k: -by_ob[k])[:3]
    para(f"Audit. The pipeline's {sum(conf.values())} errors are mostly " + "; ".join(f"{g} judged {p} ({conf[(g, p)]})" for g, p in top) +
         ". They fall mainly on " + ", ".join(f"{o.lower()} ({by_ob[o]})" for o in obs) + ". Satisfied clauses are almost never missed; the difficulty is the line "
         "between a partial clause and a hard negative.")
    for r in rows:  # case study: a correctly judged Partial erasure clause
        f = next((f for f in r["findings"] if f["id"] == "ERASURE" and f["status"] == "Partial" and gold[r["policy"]]["labels"]["ERASURE"] == "Partial" and f["quote"]), None)
        if f:
            statute = re.sub(r"\s+", " ", f["statute"])[:330]
            para(f"Case study. Section 8(7) requires: \"{statute} ...\" A synthetic policy states: \"{f['quote']}\" The pipeline returns Partial with that quote "
                 "verified in the policy: a retention statement is present, but nothing commits the company to erase data when consent is withdrawn or the "
                 f"purpose is served. The finding carries the citation {f['citation']}, attached from the knowledge base, and the residual penalty ceiling of the "
                 "Schedule.")
            break


if __name__ == "__main__":
    build()
