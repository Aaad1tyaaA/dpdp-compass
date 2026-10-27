"""Draws every diagram of the DPDP Compass project report with matplotlib (no Graphviz on this machine)."""
import math, pathlib, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Ellipse, Rectangle, Circle, Polygon

OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams["font.family"] = "Times New Roman"
INK, BLUE, PALE, GREY, LAW, OK, WARN = "#1b1b1b", "#1F3B73", "#E7EEF9", "#F1F1F1", "#FFF4DD", "#E6F4EA", "#FDECEA"


class B:
    def __init__(s, ax, cx, cy, w, h, text, fc=PALE, ec=BLUE, fs=10, bold=False, round_=True, lw=1.3, ls="-", color=INK, align="center"):
        s.cx, s.cy, s.w, s.h = cx, cy, w, h
        style = "round,pad=0.02,rounding_size=0.12" if round_ else "square,pad=0.0"
        ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle=style, fc=fc, ec=ec, lw=lw, ls=ls, zorder=2))
        ax.text(cx if align == "center" else cx - w / 2 + 0.12, cy, text, ha=align, va="center", fontsize=fs, fontweight="bold" if bold else "normal",
                color=color, zorder=3, linespacing=1.25)

    top = property(lambda s: (s.cx, s.cy + s.h / 2)); bottom = property(lambda s: (s.cx, s.cy - s.h / 2))
    left = property(lambda s: (s.cx - s.w / 2, s.cy)); right = property(lambda s: (s.cx + s.w / 2, s.cy))


def arrow(ax, a, b, text=None, rad=0.0, ls="-", color=INK, fs=8.5, lw=1.1, both=False, tpos=0.5, toff=(0, 0.12), head="-|>"):
    ax.annotate("", xy=b, xytext=a, zorder=4, arrowprops=dict(arrowstyle=("<|-|>" if both else head), lw=lw, color=color, ls=ls,
                shrinkA=1, shrinkB=1, connectionstyle=f"arc3,rad={rad}", mutation_scale=12))
    if text:
        x = a[0] + (b[0] - a[0]) * tpos + toff[0]; y = a[1] + (b[1] - a[1]) * tpos + toff[1]
        ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=color, zorder=5,
                bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.95))


def path(ax, pts, ls="-", color=INK, lw=1.1, head=True):
    """Orthogonal polyline through the given points; arrowhead on the last segment."""
    xs, ys = zip(*pts)
    ax.plot(xs[:-1] + (xs[-1],), ys[:-1] + (ys[-1],), color=color, lw=lw, ls=ls, zorder=4, solid_capstyle="butt")
    if head:
        ax.annotate("", xy=pts[-1], xytext=pts[-2], zorder=4, arrowprops=dict(arrowstyle="-|>", lw=lw, color=color, ls=ls, shrinkA=0, shrinkB=1, mutation_scale=12))


def canvas(w, h, xmax, ymax, title=None):
    fig, ax = plt.subplots(figsize=(w, h)); ax.set_xlim(0, xmax); ax.set_ylim(0, ymax); ax.axis("off")
    if title:
        ax.text(xmax / 2, ymax - 0.25, title, ha="center", va="top", fontsize=13, fontweight="bold", color=BLUE)
    return fig, ax


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight", facecolor="white"); plt.close(fig); print("drew", name)


def group(ax, x, y, w, h, label, fc="#FAFBFE", ec="#9AAAC8"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15", fc=fc, ec=ec, lw=1.1, ls=(0, (4, 3)), zorder=1))
    ax.text(x + 0.15, y + h - 0.18, label, ha="left", va="top", fontsize=10.5, fontweight="bold", color=BLUE, zorder=3)


def store(ax, cx, cy, w, h, ident, text, fs=9):
    """DFD data store: open-ended box with an identifier compartment."""
    x0, y0 = cx - w / 2, cy - h / 2
    ax.add_patch(Rectangle((x0, y0), w, h, fc=GREY, ec="none", zorder=2))
    ax.plot([x0, x0 + w], [y0 + h, y0 + h], color=INK, lw=1.2, zorder=3); ax.plot([x0, x0 + w], [y0, y0], color=INK, lw=1.2, zorder=3)
    ax.plot([x0, x0], [y0, y0 + h], color=INK, lw=1.2, zorder=3); ax.plot([x0 + 0.55, x0 + 0.55], [y0, y0 + h], color=INK, lw=1.0, zorder=3)
    ax.text(x0 + 0.27, cy, ident, ha="center", va="center", fontsize=fs, fontweight="bold", zorder=4)
    ax.text(x0 + 0.55 + (w - 0.55) / 2, cy, text, ha="center", va="center", fontsize=fs, zorder=4)
    return B.__new__(B) if False else type("S", (), {"top": (cx, cy + h / 2), "bottom": (cx, cy - h / 2), "left": (x0, cy), "right": (x0 + w, cy)})()


def process(ax, cx, cy, r, num, text, fs=9):
    ax.add_patch(Circle((cx, cy), r, fc=PALE, ec=BLUE, lw=1.3, zorder=2))
    ax.plot([cx - r * 0.82, cx + r * 0.82], [cy + r * 0.45, cy + r * 0.45], color=BLUE, lw=0.9, zorder=3)
    ax.text(cx, cy + r * 0.66, num, ha="center", va="center", fontsize=fs, fontweight="bold", zorder=4)
    ax.text(cx, cy - r * 0.12, text, ha="center", va="center", fontsize=fs, zorder=4, linespacing=1.2)
    o = type("P", (), {})(); o.c = (cx, cy); o.r = r
    o.at = lambda ang, cx=cx, cy=cy, r=r: (cx + r * math.cos(math.radians(ang)), cy + r * math.sin(math.radians(ang)))
    o.right, o.left, o.top, o.bottom = (cx + r, cy), (cx - r, cy), (cx, cy + r), (cx, cy - r)
    return o


def actor(ax, cx, cy, label, s=1.0):
    ax.add_patch(Circle((cx, cy + 0.55 * s), 0.17 * s, fc="white", ec=INK, lw=1.3, zorder=3))
    ax.plot([cx, cx], [cy + 0.38 * s, cy - 0.1 * s], color=INK, lw=1.3); ax.plot([cx - 0.3 * s, cx + 0.3 * s], [cy + 0.22 * s, cy + 0.22 * s], color=INK, lw=1.3)
    ax.plot([cx, cx - 0.25 * s], [cy - 0.1 * s, cy - 0.5 * s], color=INK, lw=1.3); ax.plot([cx, cx + 0.25 * s], [cy - 0.1 * s, cy - 0.5 * s], color=INK, lw=1.3)
    ax.text(cx, cy - 0.72 * s, label, ha="center", va="top", fontsize=10, fontweight="bold", linespacing=1.2)


def usecase(ax, cx, cy, w, h, text, fs=9.5):
    ax.add_patch(Ellipse((cx, cy), w, h, fc=PALE, ec=BLUE, lw=1.2, zorder=2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, zorder=3, linespacing=1.15)
    return type("U", (), {"left": (cx - w / 2, cy), "right": (cx + w / 2, cy), "c": (cx, cy)})()


# ── 1. System architecture ─────────────────────────────────────────────────
def architecture():
    fig, ax = canvas(17, 10.5, 34, 21)
    group(ax, 0.2, 5.2, 6.0, 15.4, "1. Data sources")
    srcs = ["DPDP Act, 2023\n(Gazette PDF, 21 pages)", "DPDP Rules, 2025\nG.S.R. 846(E) + corrigendum\nG.S.R. 892(E), 843(E)",
            "Reference privacy policies\nof 10 Indian apps", "Organisation's privacy policy\n(upload PDF/DOCX or paste)", "Citizen question\n(English, Hindi, Marathi)"]
    S = [B(ax, 3.2, 18.6 - i * 2.85, 5.3, 2.1, t, fc=LAW if i < 2 else "white", ec="#B7791F" if i < 2 else BLUE, fs=9.5) for i, t in enumerate(srcs)]
    group(ax, 6.8, 5.2, 6.8, 15.4, "2. Knowledge-base construction (offline)")
    K = [B(ax, 10.2, 18.4 - i * 3.2, 6.0, 2.3, t, fs=9.5) for i, t in enumerate([
        "Statute parser + clause-aware chunker\n(sections, sub-sections, marginal titles,\npages; 82 chunks, mean 765 chars)",
        "Three-layer builder\nfacts → obligations (80) → principles (13)",
        "Deontic triplet extraction\nMUST / MUST_NOT / HAS_RIGHT / MAY\n+ cross-references, penalties",
        "Indexers: MiniLM embeddings,\nBM25+ sparse index, provision metadata"])]
    for a, b in zip(K, K[1:]): arrow(ax, a.bottom, b.top)
    group(ax, 14.2, 5.2, 6.4, 15.4, "3. Hybrid legal knowledge base")
    KB = [B(ax, 17.4, 18.6 - i * 2.85, 5.6, 2.1, t, fc=GREY, ec=INK, fs=9.5) for i, t in enumerate([
        "Dense vector index\n(Qdrant embedded / server)", "BM25+ sparse index", "Provision metadata store\n(exact section lookup, page)",
        "Knowledge graph\n287 nodes · 354 relationships", "Rule book (rulebook.json)\n45 requirements · 14 obligations"])]
    group(ax, 21.2, 5.2, 6.6, 15.4, "4. Multi-agent engine (LangGraph)")
    E = [B(ax, 24.5, 19.0 - i * 2.2, 5.8, 1.55, t, fs=9.5) for i, t in enumerate([
        "Orchestrator: language + intent", "Retrieval agent (hybrid + RRF\n+ cross-encoder re-rank)", "Obligation-mapping agent\n(statute, principle, exemptions)",
        "Compliance-checking agent\n(per-obligation LLM judge)", "Guardrails + rule-book reconcile", "Risk agent (Schedule penalties,\napplicability, in-force date)"])]
    for a, b in zip(E, E[1:]): arrow(ax, a.bottom, b.top)
    llm = B(ax, 24.5, 6.2, 5.8, 1.3, "LLM: gpt-oss-120b via Groq\n(temperature 0; cached)", fc=LAW, ec="#B7791F", fs=9.5)
    path(ax, [E[3].right, (27.6, E[3].cy), (27.6, 6.2), llm.right], ls="--")
    group(ax, 28.4, 5.2, 5.4, 15.4, "5. Interfaces & outputs")
    O = [B(ax, 31.1, 18.4 - i * 3.3, 4.8, 2.6, t, fc="white", fs=9.5) for i, t in enumerate([
        "Business workbench\naudit report, evidence,\nredlines, review trail",
        "Policy generator\nintake + rule-book draft\n(14/14 by construction)",
        "Citizen desk\ngrounded answers, app\npolicy check, rights letters",
        "Exports\nPDF · DOCX · Markdown"])]
    # sources → offline pipeline
    for s in S[:2]: path(ax, [s.right, (6.62, s.cy), (6.62, K[0].cy), K[0].left])
    path(ax, [S[2].right, (6.62, S[2].cy), (6.62, K[3].cy), K[3].left])
    # offline pipeline → knowledge base, through the gap at x = 13.9
    path(ax, [K[3].right, (13.9, K[3].cy), (13.9, KB[0].cy), KB[0].left]); path(ax, [(13.9, KB[1].cy), KB[1].left])
    path(ax, [K[1].right, (13.75, K[1].cy), (13.75, KB[2].cy - 0.4), (KB[2].left[0], KB[2].cy - 0.4)])
    path(ax, [K[2].right, (13.6, K[2].cy), (13.6, KB[3].cy), KB[3].left])
    # knowledge base → retrieval agent along a bus at x = 20.9
    for k in KB: path(ax, [k.right, (20.9, k.cy)], ls=":", color="#55607A", lw=1.0, head=False)
    path(ax, [(20.9, KB[-1].cy), (20.9, E[1].cy), E[1].left], ls=":", color="#55607A", lw=1.0)
    # user inputs → orchestrator, below the columns and up the gap at x = 21.05
    path(ax, [S[3].right, (6.38, S[3].cy), (6.38, 4.95), (21.05, 4.95), (21.05, E[0].cy), E[0].left])
    path(ax, [S[4].right, (6.38, S[4].cy)], head=False)
    # engine → interfaces along a bus at x = 28.1; exports from the workbench along the right edge
    path(ax, [E[5].right, (28.1, E[5].cy)], head=False); path(ax, [(28.1, E[5].cy), (28.1, O[0].cy)], head=False)
    for o in O[:3]: path(ax, [(28.1, o.cy), o.left])
    path(ax, [O[0].right, (33.75, O[0].cy), (33.75, O[3].cy), O[3].right])
    group(ax, 0.2, 0.2, 16.5, 4.5, "6. Persistence (SQLite, per user)", fc="#FAFAFA")
    for i, t in enumerate(["users · sessions\nuser_state", "documents · versions\n(sha256 per version)", "analyses · review_events\n(append-only trail)"]):
        B(ax, 3.0 + i * 5.3, 2.2, 4.6, 2.2, t, fc=GREY, ec=INK, fs=9.5)
    group(ax, 17.3, 0.2, 16.5, 4.5, "7. Evaluation layer", fc="#FAFAFA")
    for i, t in enumerate(["DPDP-QA\n198 questions\nEN · HI · MR", "DPDP-Synth\n40 policies\n(labels by construction)", "DPDP-Real\n20 Indian policies\n(2 annotators)"]):
        B(ax, 20.1 + i * 5.4, 2.2, 4.8, 2.6, t, fc=OK, ec="#2E7D32", fs=9.5)
    save(fig, "d01_architecture")


# ── 2. Modular structure ────────────────────────────────────────────────────
def modules():
    fig, ax = canvas(16, 5.6, 32, 14.6)
    ax.set_ylim(4.3, 14.6)
    root = B(ax, 16, 13.6, 15, 1.5, "DPDP Compass — DPDP Act Compliance Assessment\n& Citizen Rights Awareness", fs=11.5, bold=True, fc=BLUE, color="white")
    mods = [("Module 1\nLegal Knowledge Base", ["Gazette PDF parsing", "Clause-aware chunking", "Three-layer structure", "Triplets + graph", "Rules 2025 + corrigendum", "Rule book (45 rules)"]),
            ("Module 2\nMulti-Agent Engine", ["Orchestrator", "Hybrid retrieval + RRF", "Obligation mapping", "Compliance checking", "Guardrails", "Risk & applicability"]),
            ("Module 3\nBusiness Compliance", ["Upload / paste policy", "Audit report (14 obl.)", "Evidence viewer", "Redline + re-audit", "Review trail", "Policy generator"]),
            ("Module 4\nCitizen Rights", ["Grounded Q&A (EN/HI/MR)", "Claim support check", "App policy check", "Trust indicator", "Rights request letters", "Plain-language view"]),
            ("Module 5\nPlatform & Evaluation", ["Accounts + sessions", "Versioned documents", "Exports PDF/DOCX/MD", "Hardening, rate limits", "Evaluation metrics", "DPDP-QA / Synth / Real"])]
    for i, (m, subs) in enumerate(mods):
        x = 3.3 + i * 6.35
        mb = B(ax, x, 10.2, 5.6, 1.5, m, fs=10.5, bold=True)
        path(ax, [root.bottom, (root.cx, 11.75), (x, 11.75), mb.top]) if abs(x - root.cx) > 0.1 else path(ax, [root.bottom, mb.top])
        sb = B(ax, x, 6.75, 5.9, 3.9, "\n".join("•  " + s for s in subs), fc="white", ec="#9AAAC8", fs=10.5, align="left")
        path(ax, [mb.bottom, sb.top])
    save(fig, "d02_modules")


# ── 3–5. Data flow diagrams ─────────────────────────────────────────────────
def dfd0():
    fig, ax = canvas(14, 7.2, 28, 14.5)
    p = process(ax, 14, 7.2, 2.6, "0", "DPDP Compass\nCompliance &\nRights System", fs=11)
    ents = {"bu": B(ax, 3.2, 11.6, 5.2, 1.6, "Business user\n(Data Fiduciary)", fc="white", ec=INK, round_=False, fs=10.5, bold=True),
            "ci": B(ax, 3.2, 2.8, 5.2, 1.6, "Citizen\n(Data Principal)", fc="white", ec=INK, round_=False, fs=10.5, bold=True),
            "gz": B(ax, 24.8, 11.6, 5.4, 1.6, "Government Gazette\n(DPDP Act + Rules)", fc="white", ec=INK, round_=False, fs=10.5, bold=True),
            "ll": B(ax, 24.8, 2.8, 5.4, 1.6, "Language-model service\n(Groq, gpt-oss-120b)", fc="white", ec=INK, round_=False, fs=10.5, bold=True)}
    arrow(ax, ents["bu"].right, p.at(150), "privacy policy, intake answers,\nreview decisions", rad=-0.12, toff=(0.2, 0.75))
    arrow(ax, p.at(165), (ents["bu"].right[0], ents["bu"].right[1] - 0.5), "audit report, findings, redlines,\ngenerated policy, exports", rad=-0.12, toff=(-0.6, -1.0))
    arrow(ax, ents["ci"].right, p.at(205), "question, app name /\npolicy file", rad=0.12, toff=(0.2, -0.75))
    arrow(ax, p.at(192), (ents["ci"].right[0], ents["ci"].right[1] + 0.5), "cited answer, rights summary,\nrequest letter", rad=0.12, toff=(-0.6, 1.0))
    arrow(ax, ents["gz"].left, p.at(30), "Act, Rules, corrigendum\n(official PDFs)", rad=0.12, toff=(-0.3, 0.75))
    arrow(ax, p.at(-20), ents["ll"].left, "prompts with retrieved\nclauses (data only)", rad=0.12, toff=(0.4, -0.35))
    arrow(ax, (ents["ll"].left[0], ents["ll"].left[1] + 0.5), p.at(-5), "JSON verdicts,\ndrafted answers", rad=-0.12, toff=(-0.2, 0.75))
    save(fig, "d03_dfd0")


def lab(ax, x, y, t, fs=8.8, rot=0):
    ax.text(x, y, t, ha="center", va="center", fontsize=fs, rotation=rot, zorder=6, bbox=dict(fc="white", ec="none", pad=0.5))


def dfd1():
    fig, ax = canvas(17, 11, 34, 22)
    ent = lambda x, y, t: B(ax, x, y, 4.4, 1.6, t, fc="white", ec=INK, round_=False, fs=10.5, bold=True)
    bu = ent(2.6, 15.5, "Business user"); ci = ent(2.6, 4.0, "Citizen")
    bu2 = ent(30.6, 11.5, "Business user*"); ll = ent(30.6, 6.0, "LLM service")
    P1 = process(ax, 9.0, 17.5, 1.7, "1.0", "Authenticate\n& manage\naccount"); P2 = process(ax, 9.0, 11.5, 1.7, "2.0", "Store policy\nversion")
    P4 = process(ax, 16.0, 17.5, 1.7, "4.0", "Generate\npolicy from\nrule book"); P3 = process(ax, 16.0, 11.5, 1.8, "3.0", "Audit policy\n(14 obligations)")
    P7 = process(ax, 23.0, 17.5, 1.7, "7.0", "Review &\nredline\nfindings"); P6 = process(ax, 23.0, 11.5, 1.7, "6.0", "Export report\nPDF/DOCX/MD")
    P5 = process(ax, 9.0, 4.0, 1.8, "5.0", "Answer citizen\nquestion")
    D1 = store(ax, 9.0, 20.3, 5.0, 1.0, "D1", "Users · sessions"); D5 = store(ax, 16.0, 20.3, 4.6, 1.0, "D5", "Rule book")
    D2 = store(ax, 10.6, 7.8, 6.2, 1.0, "D2", "Documents · versions"); D3 = store(ax, 23.0, 14.5, 6.0, 1.0, "D3", "Analyses · review events")
    D4 = store(ax, 16.0, 1.0, 6.4, 1.0, "D4", "Legal knowledge base")
    path(ax, [(bu.right[0], 16.0), (P1.at(195)[0], 16.0), P1.at(205)]); lab(ax, 5.9, 16.0, "credentials")
    path(ax, [P1.top, D1.bottom]); lab(ax, 9.0, 19.45, "session", fs=8)
    path(ax, [(bu.right[0], 15.0), (6.0, 15.0), (6.0, 11.5), P2.left]); lab(ax, 6.0, 13.2, "policy file / text")
    path(ax, [P2.bottom, (9.0, D2.top[1])]); lab(ax, 9.0, 9.05, "text + sha256", fs=8)
    path(ax, [P2.right, P3.left]); lab(ax, 12.4, 11.5, "document id")
    path(ax, [D2.right, (14.9, 7.8), P3.at(-120)]); lab(ax, 14.2, 8.6, "policy text", fs=8)
    path(ax, [D5.bottom, P4.top]); lab(ax, 16.0, 19.45, "requirements", fs=8)
    path(ax, [D5.right, (19.4, 20.3), (19.4, 12.8), P3.at(40)]); lab(ax, 19.4, 15.0, "rules")
    path(ax, [(2.6, bu.top[1]), (2.6, 19.55), (14.3, 19.55), (14.3, P4.at(155)[1]), P4.at(155)]); lab(ax, 5.0, 19.55, "intake answers")
    path(ax, [P4.bottom, P3.top]); lab(ax, 16.0, 14.5, "draft →\nAudit this draft", fs=8)
    path(ax, [P4.left, (12.6, 17.5), (12.6, D2.top[1])], ls="--"); lab(ax, 12.6, 14.0, "saved\ndraft", fs=8)
    path(ax, [P3.at(35), (18.6, P3.at(35)[1]), (18.6, 14.5), D3.left]); lab(ax, 18.6, 13.6, "findings,\nscore", fs=8)
    path(ax, [D3.top, P7.bottom]); lab(ax, 23.0, 15.45, "finding", fs=8)
    path(ax, [D3.bottom, P6.top]); lab(ax, 23.0, 13.55, "analysis", fs=8)
    path(ax, [P6.right, bu2.left]); lab(ax, 26.6, 11.5, "report file")
    path(ax, [P7.top, (23.0, 21.4), (1.2, 21.4), (1.2, bu.top[1])]); path(ax, [(1.2, 21.4), (23.0, 21.4), P7.top])
    lab(ax, 12.0, 21.4, "accept / override decisions, redlines / updated findings")
    y3 = P3.at(-40)[1]
    path(ax, [P3.at(-40), (20.0, y3), (20.0, 6.2), (ll.left[0], 6.2)]); path(ax, [(20.0, 6.2), (20.0, y3), P3.at(-40)])
    lab(ax, 24.4, 6.2, "prompts / verdicts")
    path(ax, [(ci.right[0], 4.35), (P5.left[0], 4.35)]); lab(ax, 5.9, 4.7, "question", fs=8)
    path(ax, [(P5.left[0], 3.65), (ci.right[0], 3.65)]); lab(ax, 5.9, 3.25, "cited answer", fs=8)
    path(ax, [D4.left, (9.0, 1.0), P5.bottom]); lab(ax, 11.0, 1.0, "provisions", fs=8)
    path(ax, [D4.top, P3.bottom]); lab(ax, 16.0, 5.6, "statute,\nchunks", fs=8)
    path(ax, [P5.right, (30.6, 4.0), ll.bottom], ls=":"); lab(ax, 25.0, 4.0, "answer drafting", fs=8)
    save(fig, "d04_dfd1")


def dfd2():
    fig, ax = canvas(17, 8.6, 34, 17)
    P = [process(ax, 3.0 + i * 4.75, 10.5, 1.75, f"3.{i + 1}", t) for i, t in enumerate([
        "Chunk &\nindex the\npolicy", "Retrieve 3\nclauses per\nobligation", "Map obligation\n(statute,\nexemptions)", "Judge each\nobligation\n(LLM)",
        "Guardrails\n+ rule-book\nreconcile", "Risk, applic-\nability,\nin-force date", "Build report\n& save"])]
    for a, b in zip(P, P[1:]): arrow(ax, a.at(0), b.at(180))
    D2 = store(ax, 3.0, 15.2, 5.0, 1.0, "D2", "Policy version"); D4 = store(ax, 12.5, 15.2, 6.0, 1.0, "D4", "Legal knowledge base")
    D5 = store(ax, 22.0, 15.2, 4.6, 1.0, "D5", "Rule book"); D3 = store(ax, 31.5, 15.2, 4.6, 1.0, "D3", "Analyses")
    arrow(ax, D2.bottom, P[0].at(90), "policy text"); arrow(ax, D4.bottom, P[2].at(90), "statute text, principle,\nexemptions, penalty", toff=(0, 0.2))
    arrow(ax, D5.bottom, P[4].at(90), "45 requirements"); arrow(ax, P[6].at(90), D3.bottom, "analysis JSON")
    ll = B(ax, 17.25, 4.4, 5.6, 1.5, "LLM service", fc="white", ec=INK, round_=False, fs=10.5, bold=True)
    arrow(ax, P[3].at(-100), (ll.top[0] - 1.0, ll.top[1]), "obligation + tests +\nclauses (batch of 7)", rad=0.15, toff=(-2.4, 0))
    arrow(ax, (ll.top[0] + 1.0, ll.top[1]), P[3].at(-60), "status, quote,\nconfidence", rad=0.15, toff=(2.0, 0))
    notes = [(P[1], "dense + BM25+\nRRF over policy\nchunks"), (P[4], "verify quotes,\ncitations; hard\nflaws → Partial"), (P[5], "Schedule ceiling\n→ severity")]
    for p, t in notes:
        ax.text(p.c[0], p.c[1] - 3.1, t, ha="center", va="center", fontsize=8.8, style="italic", color="#444",
                bbox=dict(fc="#FFFDF5", ec="#C9B37E", boxstyle="round,pad=0.3"))
    save(fig, "d05_dfd2")


# ── 6. ER diagram ───────────────────────────────────────────────────────────
def table(ax, x, y, w, name, cols, pk=(), fk=()):
    rh = 0.52
    ax.add_patch(Rectangle((x, y - rh), w, rh, fc=BLUE, ec=BLUE, zorder=2))
    ax.text(x + w / 2, y - rh / 2, name, ha="center", va="center", color="white", fontsize=10.5, fontweight="bold", zorder=3)
    for i, c in enumerate(cols):
        yy = y - rh * (i + 2)
        ax.add_patch(Rectangle((x, yy), w, rh, fc="white" if i % 2 else "#F6F8FC", ec="#9AAAC8", lw=0.8, zorder=2))
        tag = "PK" if c in pk else "FK" if c in fk else ""
        ax.text(x + 0.12, yy + rh / 2, tag, ha="left", va="center", fontsize=8, fontweight="bold", color="#B7791F", zorder=3)
        ax.text(x + 0.75, yy + rh / 2, c, ha="left", va="center", fontsize=9, zorder=3, fontweight="bold" if c in pk else "normal")
    h = rh * (len(cols) + 1)
    return {"x": x, "w": w, "top": y, "bottom": y - h, "cx": x + w / 2}


def er():
    fig, ax = canvas(16, 8.2, 32, 16.5)
    ax.set_ylim(1.0, 16.5)
    U = table(ax, 1.0, 15.5, 6.0, "users", ["id", "email (unique)", "name", "pw_hash (scrypt)", "pw_salt", "created_at"], pk=["id"])
    S = table(ax, 1.0, 10.6, 6.0, "sessions", ["token_hash", "user_id", "expires_at"], pk=["token_hash"], fk=["user_id"])
    US = table(ax, 1.0, 7.6, 6.0, "user_state", ["user_id", "key", "value (JSON)", "updated_at"], pk=["user_id", "key"])
    LF = table(ax, 1.0, 4.0, 6.0, "login_failures", ["email", "at"])
    D = table(ax, 9.8, 15.5, 6.2, "documents", ["id", "owner", "name", "company", "created_at", "source", "meta (JSON)"], pk=["id"], fk=["owner"])
    V = table(ax, 9.8, 10.6, 6.2, "versions", ["doc_id", "n", "text", "sha256", "created_at", "note"], pk=["doc_id", "n"])
    A = table(ax, 18.8, 15.5, 6.2, "analyses", ["id", "owner", "body (analysis JSON)"], pk=["id"], fk=["owner"])
    R = table(ax, 18.8, 12.4, 6.2, "review_events", ["seq", "analysis_id", "finding_id", "decision", "status", "note", "user_id, user_name", "at"], pk=["seq"], fk=["analysis_id"])
    K = table(ax, 27.0, 15.5, 4.6, "kb_metadata", ["chunk_id", "source_document", "section", "subsection", "clause", "obligation_type", "legal_principle", "citation", "page", "text"], pk=["chunk_id"])
    def lab(x, y, t): ax.text(x, y, t, fontsize=10.5, fontweight="bold", color="#B7791F", ha="center", va="center", zorder=6)
    def line(pts, ls="-"):
        xs, ys = zip(*pts); ax.plot(xs, ys, color=INK, lw=1.3, ls=ls, zorder=1)
    # users 1—N sessions (vertical), users 1—N user_state (left rail), users 1—N documents, users 1—N analyses (over the top)
    line([(U["cx"], U["bottom"]), (U["cx"], S["top"])]); lab(U["cx"] + 0.3, U["bottom"] - 0.3, "1"); lab(U["cx"] + 0.3, S["top"] + 0.3, "N")
    line([(1.0, 13.0), (0.45, 13.0), (0.45, US["top"] - 1.0), (1.0, US["top"] - 1.0)]); lab(0.75, 13.3, "1"); lab(0.75, US["top"] - 0.7, "N")
    line([(7.0, 14.45), (9.8, 14.45)]); lab(7.35, 14.75, "1"); lab(9.45, 14.75, "N")
    line([(U["cx"], 15.5), (U["cx"], 16.1), (A["cx"], 16.1), (A["cx"], 15.5)]); lab(U["cx"] + 0.3, 15.8, "1"); lab(A["cx"] + 0.3, 15.8, "N")
    line([(D["cx"], D["bottom"]), (D["cx"], V["top"])]); lab(D["cx"] - 0.35, (D["bottom"] + V["top"]) / 2, "1"); lab(D["cx"] + 0.35, (D["bottom"] + V["top"]) / 2, "N")
    line([(A["cx"], A["bottom"]), (A["cx"], R["top"])]); lab(A["cx"] + 0.3, A["bottom"] - 0.25, "1"); lab(A["cx"] + 0.3, R["top"] + 0.25, "N")
    line([(16.0, 14.45), (18.8, 14.45)], ls="--"); lab(16.35, 14.75, "1"); lab(18.45, 14.75, "N")
    ax.text(17.4, 13.95, "policy_id\nin body", fontsize=8.5, style="italic", color="#555", ha="center", va="top")
    ax.text(K["cx"], K["bottom"] - 0.25, "PostgreSQL when available,\notherwise embedded store", fontsize=8.5, ha="center", va="top", style="italic", color="#555")
    ax.text(18.8, 5.6, "Three SQLite files:\n• storage/accounts.db — users, sessions,\n   user_state, login_failures\n• storage/documents.db — documents, versions\n"
            "• storage/analyses.db — analyses, review_events", fontsize=9.5, va="top", ha="left",
            bbox=dict(fc="#FAFAFA", ec="#BBB", boxstyle="round,pad=0.5"))
    save(fig, "d06_er")


# ── 7. Class diagram ────────────────────────────────────────────────────────
def klass(ax, x, y, w, name, attrs, methods, fs=9):
    lh = 0.42; hh = 0.6
    ha = lh * max(1, len(attrs)) + 0.2; hm = lh * max(1, len(methods)) + 0.2
    ax.add_patch(Rectangle((x, y - hh), w, hh, fc=BLUE, ec=BLUE, zorder=2))
    ax.text(x + w / 2, y - hh / 2, name, ha="center", va="center", color="white", fontweight="bold", fontsize=10, zorder=3)
    ax.add_patch(Rectangle((x, y - hh - ha), w, ha, fc="white", ec=BLUE, zorder=2))
    for i, a in enumerate(attrs): ax.text(x + 0.15, y - hh - 0.1 - lh * (i + 0.5), a, fontsize=fs, va="center", zorder=3)
    ax.add_patch(Rectangle((x, y - hh - ha - hm), w, hm, fc="#F6F8FC", ec=BLUE, zorder=2))
    for i, m in enumerate(methods): ax.text(x + 0.15, y - hh - ha - 0.1 - lh * (i + 0.5), m, fontsize=fs, va="center", zorder=3)
    h = hh + ha + hm
    return {"top": (x + w / 2, y), "bottom": (x + w / 2, y - h), "left": (x, y - h / 2), "right": (x + w, y - h / 2)}


def classes():
    fig, ax = canvas(16, 10, 32, 20)
    ax.set_xlim(0.2, 31.4)
    E = klass(ax, 11.5, 19.5, 8.0, "Engine", ["+ st : Statute", "+ kb : KnowledgeBase", "+ chunks : list[dict]", "+ index : Index"],
              ["+ provision_text(p) : str", "+ provision_page(p) : int", "+ exemptions(p) : list", "+ valid_provisions : set", "+ has_rules : bool"])
    St = klass(ax, 0.5, 19.5, 7.6, "Statute", ["+ name : str", "+ sections : list[Section]"], ["+ units(limit) : list[Unit]", "+ parse(pdf) : Statute  «static»", "+ chunk_clause_aware(st, n)"])
    KB = klass(ax, 0.5, 12.6, 7.6, "KnowledgeBase", ["+ nodes : dict", "+ edges : list[Edge]"], ["+ counts() : dict", "+ principle_of(p) : str", "+ penalty_ceiling(kb, p) : str"])
    IX = klass(ax, 0.5, 6.6, 7.6, "Index", ["+ chunks : list[dict]", "- dense, bm25, meta"], ["+ search(q, k, weights, rerank)", "  : (hits, timings)"])
    LL = klass(ax, 23.5, 19.5, 7.6, "LLM", ["+ model : str", "+ available : bool", "+ patience : int"], ["+ complete(system, user, max)", "  : str  (cached, failover)"])
    WF = klass(ax, 12.0, 11.0, 7.0, "State «TypedDict»", ["question, policy : str", "clauses, mapping : dict", "verdicts, findings", "result, trace"],
               ["orchestrator()", "retrieval() · compliance()", "guardrails() · risk()"])
    RB = klass(ax, 23.5, 12.6, 7.6, "rulebook «module»", ["+ RULES : dict[id, list]", "+ HARD : set[str]", "+ PLACEHOLDER : Pattern"],
               ["+ check(text) : dict", "+ reconcile(findings, policy)", "+ draft(facts) : str", "+ best_sections(text)"])
    DS = klass(ax, 23.5, 5.6, 7.6, "DocumentStore", ["- _db : sqlite3", "- _lock : Lock"], ["+ create(name, text, source)", "+ add_version(id, text)", "+ get(id) · text(id, n)", "+ find_by_text(text)"])
    AU = klass(ax, 12.0, 4.6, 7.0, "checklist «module»", ["+ CHECKLIST : 14 obligations", "+ METHOD : dict"], ["+ score(statuses) : float", "+ trust(score) : int"])
    def lab(x, y, t): ax.text(x, y, t, fontsize=8.8, ha="center", va="center", zorder=6, bbox=dict(fc="white", ec="none", pad=0.4))
    path(ax, [(11.5, 17.6), (8.1, 17.6)]); lab(9.8, 17.6, "has 1")
    path(ax, [(11.5, 14.7), (9.8, 14.7), (9.8, 11.0), (8.1, 11.0)]); lab(9.8, 13.0, "has 1")
    path(ax, [(11.5, 14.2), (10.3, 14.2), (10.3, 5.2), (8.1, 5.2)]); lab(10.3, 7.5, "has 1")
    path(ax, [WF["top"], (WF["top"][0], E["bottom"][1])], ls="--"); lab(15.5, 12.2, "uses")
    path(ax, [(19.0, 10.3), (21.0, 10.3), (21.0, 17.7), (23.5, 17.7)], ls="--"); lab(21.0, 14.5, "calls")
    path(ax, [(19.0, 9.3), (23.5, 9.3)], ls="--"); lab(21.3, 9.3, "reconcile()")
    path(ax, [WF["bottom"], AU["top"]], ls="--"); lab(15.5, 5.0, "score()")
    path(ax, [RB["bottom"], DS["top"]], ls=":"); lab(27.3, 6.1, "drafts saved by API")
    save(fig, "d07_class")


# ── 8. Sequence diagram ─────────────────────────────────────────────────────
def sequence():
    lanes = ["Business user", "React UI", "FastAPI\n/api/compliance", "DocumentStore", "LangGraph\nworkflow", "Engine /\nIndex", "LLM\n(Groq)", "Rule book"]
    fig, ax = canvas(17, 11, 34, 22)
    xs = [2 + i * 4.25 for i in range(len(lanes))]
    for x, l in zip(xs, lanes):
        if l == "Business user": actor(ax, x, 20.7, "", 0.8); ax.text(x, 19.9, l, ha="center", va="top", fontsize=10, fontweight="bold")
        else: B(ax, x, 20.8, 3.6, 1.2, l, fs=9.8, bold=True, round_=False)
        ax.plot([x, x], [19.6, 0.4], color="#777", lw=1, ls=(0, (5, 4)), zorder=1)
    msgs = [(0, 1, "1: paste policy, Run audit"), (1, 2, "2: POST /analyze {text, as_of, applicability}"), (2, 3, "3: find_by_text / create (sha256)"),
            (3, 2, "4: document {id, version}", True), (2, 4, "5: run(policy)"), (4, 5, "6: chunk policy; 3 clauses × 14 obligations"),
            (4, 5, "7: map obligations (statute, principle, exemptions)"), (4, 6, "8: judge(batch of 7 obligations)"), (6, 4, "9: JSON status, quote, confidence", True),
            (4, 4, "10: guardrails: verify quotes, citations"), (4, 7, "11: reconcile(findings, policy)"), (7, 4, "12: rule checks, fixes, hard flaws", True),
            (4, 4, "13: risk, applicability, in-force date, score"), (4, 2, "14: report", True), (2, 2, "15: save analysis (owner)"), (2, 1, "16: analysis JSON", True),
            (1, 0, "17: score, findings, evidence, fixes", True)]
    y = 18.6; ys = {}
    for k, m in enumerate(msgs):
        a, b, t = m[0], m[1], m[2]; ret = len(m) > 3
        if a == b:
            ax.annotate("", xy=(xs[a] + 0.15, y - 0.6), xytext=(xs[a] + 0.15, y), arrowprops=dict(arrowstyle="-|>", lw=1.0, color=INK, connectionstyle="arc3,rad=-1.4"))
            ax.text(xs[a] + 0.85, y - 0.3, t, fontsize=8.8, va="center", bbox=dict(fc="white", ec="none", pad=0.3))
            ys[k] = y; y -= 1.25; continue
        ax.annotate("", xy=(xs[b], y), xytext=(xs[a], y), arrowprops=dict(arrowstyle="-|>" if not ret else "->", lw=1.0, color=INK, ls="--" if ret else "-"))
        ax.text((xs[a] + xs[b]) / 2, y + 0.2, t, ha="center", va="bottom", fontsize=8.8, bbox=dict(fc="white", ec="none", pad=0.3))
        ys[k] = y; y -= 1.05
    ax.add_patch(Rectangle((xs[2] - 0.15, ys[16] - 0.2), 0.3, ys[1] + 0.3 - ys[16], fc=PALE, ec=BLUE, zorder=2))
    ax.add_patch(Rectangle((xs[4] - 0.15, ys[13] - 0.2), 0.3, ys[4] + 0.2 - ys[13], fc=PALE, ec=BLUE, zorder=2))
    save(fig, "d08_sequence")


# ── 9. Collaboration diagram ────────────────────────────────────────────────
def collaboration():
    fig, ax = canvas(15, 8.6, 30, 17.2)
    pos = {"user": (3.5, 9), "ui": (9.5, 15), "api": (16, 15), "store": (24.5, 15), "wf": (16, 8.5), "eng": (9.5, 2.4), "llm": (16, 2.4), "rb": (24.5, 2.4)}
    names = {"user": ":Business user", "ui": ":React UI", "api": ":FastAPI", "store": ":DocumentStore", "wf": ":Workflow", "eng": ":Engine / Index", "llm": ":LLM", "rb": ":rulebook"}
    for k, (x, y) in pos.items(): B(ax, x, y, 4.4, 1.3, names[k], fc="white", ec=INK, round_=False, fs=10.5, bold=True)
    def line(a, b, labels, at):
        (x1, y1), (x2, y2) = pos[a], pos[b]
        ax.plot([x1, x2], [y1, y2], color=INK, lw=1.1, zorder=1)
        ax.text(at[0], at[1], labels, ha="center", va="center", fontsize=9, bbox=dict(fc="white", ec="none", pad=0.5), zorder=5)
    line("user", "ui", "1: Run audit →\n← 17: report", (5.0, 12.6)); line("ui", "api", "2: POST /analyze →\n← 16: analysis", (12.75, 16.3))
    line("api", "store", "3: save version →\n← 4: doc id", (20.25, 16.3)); line("api", "wf", "5: run(policy) →\n← 14: report", (17.9, 11.8))
    line("wf", "eng", "6: retrieve clauses →\n7: map obligations →", (11.2, 5.9)); line("wf", "llm", "8: judge →\n← 9: verdicts", (17.6, 5.4))
    line("wf", "rb", "11: reconcile →\n← 12: checks, fixes", (21.6, 5.9))
    ax.text(21.6, 9.3, "self-messages of :Workflow\n10: guardrails\n13: risk + score\n(:FastAPI) 15: save analysis", ha="left", va="center", fontsize=9, style="italic",
            bbox=dict(fc="#FFFDF5", ec="#C9B37E", boxstyle="round,pad=0.4"))
    save(fig, "d09_collaboration")


# ── 10. Use case diagram ────────────────────────────────────────────────────
def usecases():
    fig, ax = canvas(16, 10.5, 32, 21)
    ax.add_patch(Rectangle((6.5, 0.6), 19.0, 19.6, fc="#FBFCFE", ec=INK, lw=1.4))
    ax.text(16, 19.75, "DPDP Compass", ha="center", fontsize=12, fontweight="bold", color=BLUE)
    actor(ax, 2.6, 13.8, "Business user\n(Data Fiduciary)", 1.3); actor(ax, 2.6, 4.2, "Citizen\n(Data Principal)", 1.3)
    actor(ax, 29.3, 18.0, "Reviewer /\nCompliance officer", 1.3); actor(ax, 29.3, 10.0, "LLM service\n«system»", 1.3)
    biz = ["View evidence & citations", "Run DPDP audit (14 obligations)", "Upload or paste policy", "Generate policy from rule book",
           "Apply redline & re-audit", "Compare versions", "Export report (PDF/DOCX/MD)"]
    cit = ["Ask about my rights (EN/HI/MR)", "Check an app's privacy policy", "Draft a rights request letter"]
    U = {}
    for i, t in enumerate(biz): U[t] = usecase(ax, 12.5, 18.2 - i * 1.7, 8.2, 1.3, t)
    for i, t in enumerate(cit): U[t] = usecase(ax, 12.5, 5.6 - i * 1.7, 8.2, 1.3, t)
    U["acc"] = usecase(ax, 21.8, 18.2, 6.4, 1.3, "Accept / override finding")
    U["judge"] = usecase(ax, 21.8, 14.6, 6.4, 1.3, "Judge each obligation\nwith cited clauses")
    U["ans"] = usecase(ax, 21.8, 5.6, 6.4, 1.3, "Draft a grounded,\ncited answer")
    for t in biz: ax.plot([3.4, U[t].left[0]], [13.8, U[t].left[1]], color=INK, lw=0.9)
    for t in cit: ax.plot([3.4, U[t].left[0]], [4.2, U[t].left[1]], color=INK, lw=0.9)
    ax.plot([28.5, U["acc"].right[0]], [18.0, 18.2], color=INK, lw=0.9)
    ax.plot([28.5, U["judge"].right[0]], [10.0, 14.6], color=INK, lw=0.9); ax.plot([28.5, U["ans"].right[0]], [10.0, 5.6], color=INK, lw=0.9)
    def inc(a, b, t, y_off=0.25):
        ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", lw=0.9, ls="--", color="#555"))
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + y_off, t, fontsize=8.5, ha="center", color="#555", bbox=dict(fc="#FBFCFE", ec="none", pad=0.2))
    inc(U["Run DPDP audit (14 obligations)"].right, U["judge"].left, "«include»")
    inc(U["Ask about my rights (EN/HI/MR)"].right, U["ans"].left, "«include»")
    inc(U["View evidence & citations"].right, U["acc"].left, "«extend»")
    ax.text(16, 1.0, "All use cases require Sign up / Sign in (account, private storage).", ha="center", fontsize=9, style="italic", color="#555")
    save(fig, "d10_usecase")


# ── 11. Activity diagram: policy generation ─────────────────────────────────
def decision(ax, cx, cy, w, h, text):
    ax.add_patch(Polygon([(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)], fc=LAW, ec="#B7791F", lw=1.2, zorder=2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=9, zorder=3, linespacing=1.15)
    return type("D", (), {"top": (cx, cy + h / 2), "bottom": (cx, cy - h / 2), "left": (cx - w / 2, cy), "right": (cx + w / 2, cy)})()


def activity():
    fig, ax = canvas(13, 13.5, 26, 27)
    ax.add_patch(Circle((9, 26.2), 0.35, fc=INK))
    a1 = B(ax, 9, 24.6, 9.5, 1.3, "Fill intake form (17 fields, (i) help on each)")
    a2 = B(ax, 9, 22.6, 9.5, 1.3, "intake.review(): vague / missing answers?")
    d1 = decision(ax, 9, 20.3, 6.0, 2.2, "Questions\nraised?")
    q = B(ax, 19.0, 20.3, 6.6, 1.6, "Show follow-up questions\nwith why + example")
    d2 = decision(ax, 19.0, 17.3, 6.0, 2.2, "Answer or\ndraft anyway?")
    a3 = B(ax, 9, 17.3, 9.5, 1.3, "Fill facts (placeholders for gaps)")
    a4 = B(ax, 9, 15.2, 9.5, 1.3, "rulebook.draft(): one section per obligation")
    a5 = B(ax, 9, 13.1, 9.5, 1.3, "check(): 45 rules + keyword judge")
    d3 = decision(ax, 9, 10.8, 6.0, 2.2, "LLM\navailable?")
    a6 = B(ax, 19.0, 10.8, 6.6, 1.3, "AI polishes wording")
    d4 = decision(ax, 19.0, 8.3, 6.0, 2.2, "Rewrite still\npasses all rules?")
    a7 = B(ax, 9, 5.6, 9.5, 1.3, "Save draft as a versioned document")
    a8 = B(ax, 9, 3.6, 9.5, 1.3, "Show draft: placeholders red-circled,\n'Passes N of 14 audit rules'")
    a9 = B(ax, 9, 1.6, 9.5, 1.3, "Optional: Audit this draft → 14/14 when complete")
    def lab(x, y, t): ax.text(x, y, t, fontsize=8.8, ha="center", va="center", zorder=6, bbox=dict(fc="white", ec="none", pad=0.3))
    path(ax, [(9, 25.85), a1.top]); path(ax, [a1.bottom, a2.top]); path(ax, [a2.bottom, d1.top])
    path(ax, [d1.right, q.left]); lab(14.0, 20.6, "yes")
    path(ax, [d1.bottom, a3.top]); lab(9.5, 18.6, "no")
    path(ax, [q.bottom, d2.top]); path(ax, [d2.left, a3.right]); lab(14.0, 17.6, "draft anyway")
    path(ax, [d2.right, (23.6, 17.3), (23.6, 24.6), a1.right]); lab(23.6, 21.5, "answer")
    for a, b in ((a3, a4), (a4, a5)): path(ax, [a.bottom, b.top])
    path(ax, [a5.bottom, d3.top]); path(ax, [d3.right, a6.left]); lab(14.0, 11.1, "yes")
    path(ax, [d3.bottom, a7.top]); lab(9.5, 8.0, "no")
    path(ax, [a6.bottom, d4.top])
    path(ax, [d4.bottom, (19.0, 5.85), (a7.right[0], 5.85)]); lab(19.0, 6.6, "yes: keep rewrite")
    path(ax, [d4.left, (14.6, 8.3), (14.6, 5.35), (a7.right[0], 5.35)], ls="--"); lab(14.6, 7.2, "no: keep\nrule-book draft")
    for a, b in ((a7, a8), (a8, a9)): path(ax, [a.bottom, b.top])
    ax.add_patch(Circle((9, 0.2), 0.4, fc="white", ec=INK, lw=1.5)); ax.add_patch(Circle((9, 0.2), 0.24, fc=INK))
    path(ax, [a9.bottom, (9, 0.6)])
    ax.set_ylim(-0.4, 27)
    save(fig, "d11_activity_generation")


# ── 12. Rule-book reconciliation ────────────────────────────────────────────
def reconcile():
    fig, ax = canvas(15, 8.5, 30, 17)
    s = B(ax, 5, 15.2, 8.5, 1.4, "For each of the 14 findings:\njudge status + rule-book check")
    best = B(ax, 5, 12.6, 8.5, 1.5, "Pick the policy section meeting most\ncontent requirements (hard rules break ties)")
    d1 = decision(ax, 5, 9.6, 6.8, 2.6, "Any hard flaw?\n(placeholder, forbidden\nwording)")
    p1 = B(ax, 15.5, 9.6, 7.5, 1.6, "Satisfied → Partial\nfixes listed, decided_by = rulebook", fc=WARN, ec="#C62828")
    d2 = decision(ax, 5, 5.6, 6.8, 2.6, "All requirements\nmet in one\nsection?")
    p2 = B(ax, 15.5, 5.6, 7.5, 1.8, "Status = Satisfied\nquote = matching sentence\n(verbatim, located in policy)", fc=OK, ec="#2E7D32")
    p3 = B(ax, 5, 1.6, 8.5, 1.8, "Keep the judge's verdict;\nattach failed requirements as fixes\n+ model wording (suggested rewrite)")
    out = B(ax, 25.8, 5.6, 6.0, 2.4, "Finding with rule\nchecks (met / not met),\nbasis (Section / Rule),\nfixes, example", fc="white")
    def lab(x, y, t): ax.text(x, y, t, fontsize=9, ha="center", va="center", zorder=6, bbox=dict(fc="white", ec="none", pad=0.3))
    path(ax, [s.bottom, best.top]); path(ax, [best.bottom, d1.top])
    path(ax, [d1.right, p1.left]); lab(10.3, 9.95, "yes"); path(ax, [d1.bottom, d2.top]); lab(5.5, 7.6, "no")
    path(ax, [d2.right, p2.left]); lab(10.3, 5.95, "yes"); path(ax, [d2.bottom, p3.top]); lab(5.5, 3.5, "no")
    path(ax, [p1.right, (25.8, 9.6), out.top]); path(ax, [p2.right, out.left]); path(ax, [p3.right, (25.8, 1.6), out.bottom])
    save(fig, "d12_rulebook_reconcile")


# ── 13. Deployment ──────────────────────────────────────────────────────────
def deployment():
    fig, ax = canvas(16, 8, 32, 16)
    def node(x, y, w, h, title):
        ax.add_patch(Polygon([(x, y), (x + w, y), (x + w + 0.5, y + 0.5), (x + w + 0.5, y + h + 0.5), (x + 0.5, y + h + 0.5), (x, y + h)], fc="#EEF2FA", ec=INK, lw=1.2, zorder=1))
        ax.add_patch(Rectangle((x, y), w, h, fc="#F8FAFE", ec=INK, lw=1.2, zorder=1))
        ax.text(x + 0.2, y + h - 0.25, title, fontsize=10.5, fontweight="bold", va="top", color=BLUE)
    node(0.5, 4.0, 7.0, 8.0, "«device» User's browser")
    B(ax, 4.0, 8.6, 6.0, 1.4, "React 18 SPA (TypeScript)\nVite build · Tailwind · Radix UI", fc="white")
    B(ax, 4.0, 6.2, 6.0, 1.2, "Session cookie (HttpOnly,\nSameSite=Lax)", fc="white")
    node(9.5, 1.0, 13.5, 13.5, "«server» Application host (Windows 10/11 or Linux)")
    B(ax, 16.2, 12.4, 12.0, 1.3, "Uvicorn · FastAPI app (REST + SSE), CSRF origin check, rate limits", fc="white")
    B(ax, 13.0, 10.0, 5.6, 1.6, "LangGraph workflow\n+ Compass engine", fc=PALE)
    B(ax, 19.4, 10.0, 5.6, 1.6, "sentence-transformers\nMiniLM + cross-encoder", fc=PALE)
    B(ax, 13.0, 7.4, 5.6, 1.6, "Embedded Qdrant\n(vector index)", fc=GREY, ec=INK)
    B(ax, 19.4, 7.4, 5.6, 1.6, "Rule book + checklist\n(JSON, in process)", fc=GREY, ec=INK)
    B(ax, 16.2, 4.6, 12.0, 1.6, "SQLite: accounts.db · documents.db · analyses.db", fc=GREY, ec=INK)
    B(ax, 16.2, 2.4, 12.0, 1.3, "Official Gazette PDFs: data/legal/official (Act, Rules, corrigendum)", fc=LAW, ec="#B7791F")
    node(25.0, 9.0, 6.5, 4.5, "«cloud» Groq API")
    B(ax, 28.2, 11.0, 5.6, 1.6, "gpt-oss-120b\n(fallback model + keys)", fc=LAW, ec="#B7791F")
    node(25.0, 1.5, 6.5, 5.6, "«optional» Servers")
    B(ax, 28.2, 4.3, 5.6, 2.6, "Qdrant · Neo4j ·\nPostgreSQL\n(same code, no changes)", fc="white", ls="--")
    arrow(ax, (7.5, 8.6), (10.2, 12.4), "HTTPS /api (JSON)", both=True, toff=(-0.4, 0.4))
    arrow(ax, (22.2, 12.4), (25.0, 11.4), "HTTPS", both=True, toff=(0, 0.35))
    arrow(ax, (22.2, 7.4), (25.0, 4.6), "optional", ls="--", both=True, toff=(0, 0.35))
    save(fig, "d13_deployment")


# ── 14. Gantt chart + incremental model ─────────────────────────────────────
def gantt():
    fig, ax = plt.subplots(figsize=(13, 5.2))
    tasks = [("Literature survey, Gazette + policy collection, requirements", 0.0, 0.9, "Increment 1"),
             ("Statute parser, clause-aware chunker, three layers, triplets", 0.4, 1.0, "Increment 1"),
             ("Hybrid retrieval, obligation mapping; DPDP-QA question set", 1.0, 1.0, "Increment 2"),
             ("Compliance agent, guardrails, risk; Business & Citizen UI", 1.8, 1.2, "Increment 3"),
             ("DPDP Rules 2025, accounts, documents, redlines, review trail", 2.4, 0.9, "Increment 3"),
             ("Rule book, policy generator, evaluation ablations, testing", 3.0, 1.0, "Increment 4"),
             ("Accessible UI refinement, report and paper drafting", 3.4, 0.6, "Increment 4"),
             ("Project review by the external examiner", 4.0, 0.45, "November: review"),
             ("Research paper submission and publication", 4.15, 0.85, "November: review"),
             ("Final report submission and project demonstration", 4.5, 0.5, "November: review")]
    colors = {"Increment 1": "#9DB3DB", "Increment 2": "#6E8FCB", "Increment 3": "#3F66B0", "Increment 4": "#2A4E8F", "November: review": "#B7791F"}
    for i, (t, s, d, inc) in enumerate(tasks[::-1]):
        ax.barh(i, d, left=s, color=colors[inc], edgecolor=INK, height=0.6)
    ax.set_yticks(range(len(tasks))); ax.set_yticklabels([t[0] for t in tasks[::-1]], fontsize=10)
    ax.set_xticks([0.5, 1.5, 2.5, 3.5, 4.5]); ax.set_xticklabels(["July", "August", "September", "October", "November"], fontsize=10.5)
    for x in (1, 2, 3, 4): ax.axvline(x, color="#999", ls=":", lw=1)
    ax.axvline(4, color="#B7791F", lw=1.6); ax.text(4.03, len(tasks) - 0.4, "development complete", fontsize=9, color="#B7791F", va="center")
    ax.set_xlim(0, 5.0); ax.set_ylim(-0.6, len(tasks) - 0.1); ax.set_axisbelow(True)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(fc=c, ec=INK, label=k) for k, c in colors.items()], loc="lower left", fontsize=9, ncol=5, bbox_to_anchor=(0, -0.2), frameon=False)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    save(fig, "d14_gantt")


def incremental():
    fig, ax = canvas(15, 4.6, 30, 9.2)
    phases = ["Requirements", "Design", "Code", "Test"]
    for r, (inc, txt) in enumerate([("Increment 1 (Jul)", "Knowledge base"), ("Increment 2 (Aug)", "Retrieval + mapping"),
                                    ("Increment 3 (Sep)", "Audit, UI, accounts"), ("Increment 4 (Oct)", "Generator, evaluation")]):
        y = 7.8 - r * 2.0; x0 = 1.6 + r * 2.0
        ax.text(x0 - 0.1, y, f"{inc}\n{txt}", ha="right", va="center", fontsize=9, fontweight="bold", color=BLUE)
        for i, ph in enumerate(phases):
            B(ax, x0 + 1.9 + i * 3.6, y, 3.3, 1.2, ph, fc=[PALE, "#DCE6F6", "#C9D7F0", OK][i], fs=9.5)
            if i < 3: path(ax, [(x0 + 1.9 + i * 3.6 + 1.65, y), (x0 + 1.9 + (i + 1) * 3.6 - 1.65, y)])
        B(ax, x0 + 1.9 + 4 * 3.6 + 0.3, y, 3.2, 1.2, "Working build", fc="white", fs=9.5)
        path(ax, [(x0 + 1.9 + 3 * 3.6 + 1.65, y), (x0 + 1.9 + 4 * 3.6 + 0.3 - 1.6, y)])
    ax.set_xlim(-2.5, 30)
    save(fig, "d15_incremental")


# ── 15. Result charts from the paper's measured tables ──────────────────────
def charts():
    sysn = ["Dense only", "BM25+ only", "Graph only", "RRF dense+sparse", "RRF + graph", "RRF + metadata", "Full system\n(+ re-rank)"]
    hit1 = [0.468, 0.611, 0.206, 0.611, 0.500, 0.690, 0.746]; ndcg = [0.668, 0.722, 0.377, 0.748, 0.653, 0.823, 0.861]
    fig, ax = plt.subplots(figsize=(12, 4.6)); x = range(len(sysn)); w = 0.38
    b1 = ax.bar([i - w / 2 for i in x], hit1, w, label="Hit@1", color="#6E8FCB", edgecolor=INK); b2 = ax.bar([i + w / 2 for i in x], ndcg, w, label="nDCG@10", color=BLUE, edgecolor=INK)
    for bars in (b1, b2):
        for r in bars: ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.012, f"{r.get_height():.3f}", ha="center", fontsize=8.5)
    ax.set_xticks(list(x)); ax.set_xticklabels(sysn, fontsize=9.5); ax.set_ylim(0, 1); ax.legend(); ax.grid(axis="y", ls=":")
    ax.set_title("Retrieval ablation on the DPDP-QA test split (126 answerable questions)", fontsize=12, fontweight="bold", color=BLUE)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    save(fig, "c01_retrieval")
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.4))
    names = ["Keyword rules", "Single-prompt LLM", "Pipeline (no guardrails)", "Full pipeline"]
    for ax, title, kap, mae in ((axs[0], "DPDP-Synth (8 held-out policies, 112 decisions)", [0.625, 0.774, 0.785, 0.785], [11.2, 7.6, 4.5, 4.5]),
                                (axs[1], "DPDP-Real (20 policies, 280 decisions)", [0.443, 0.623, 0.672, 0.688], [14.9, 10.2, 7.3, 6.8])):
        bars = ax.bar(range(4), kap, color=["#B0B0B0", "#9DB3DB", "#3F66B0", BLUE], edgecolor=INK)
        for r, m in zip(bars, mae): ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.015, f"κ {r.get_height():.3f}\nMAE {m}", ha="center", fontsize=8.8)
        ax.set_xticks(range(4)); ax.set_xticklabels(names, fontsize=8.8, rotation=12); ax.set_ylim(0, 1); ax.set_title(title, fontsize=10.5, fontweight="bold", color=BLUE)
        ax.set_ylabel("Cohen's kappa"); ax.grid(axis="y", ls=":")
        for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    save(fig, "c02_audit")
    fig, ax = plt.subplots(figsize=(11, 4.2))
    s = ["LLM, no retrieval", "Dense RAG", "Hybrid RAG", "Full system"]
    unsup = [63.1, 10.8, 7.9, 7.9]; full = [64, 76, 76, 76]; fab = [4.0, 0, 0, 0]
    x = range(4); w = 0.27
    for k, (vals, lab, col) in enumerate(((full, "Fully correct (%)", BLUE), (unsup, "Unsupported claims (%)", "#C62828"), (fab, "Fabricated citations (%)", "#B7791F"))):
        bars = ax.bar([i + (k - 1) * w for i in x], vals, w, label=lab, color=col, edgecolor=INK)
        for r in bars: ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 1, f"{r.get_height():g}", ha="center", fontsize=8.5)
    ax.set_xticks(list(x)); ax.set_xticklabels(s); ax.set_ylim(0, 90); ax.legend(fontsize=9); ax.grid(axis="y", ls=":")
    ax.set_title("Question answering on 25 DPDP-QA test questions", fontsize=12, fontweight="bold", color=BLUE)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    save(fig, "c03_qa")


for fn in (architecture, modules, dfd0, dfd1, dfd2, er, classes, sequence, collaboration, usecases, activity, reconcile, deployment, gantt, incremental, charts):
    fn()
