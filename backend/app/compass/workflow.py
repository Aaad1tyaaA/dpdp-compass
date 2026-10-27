"""The agent workflow as a LangGraph state machine.

    orchestrator ─┬─ question ──> answer (retrieve, generate, citation guardrails) ──> END
                  └─ audit ─────> retrieval -> obligation_mapping -> compliance -> guardrails -> risk ──> END

The orchestrator detects language and intent. A question with no policy skips the audit agents.
Every node appends a step (agent, duration, summary) to the trace.
"""
from __future__ import annotations

import logging
import time
from datetime import date
from functools import lru_cache
from typing import TypedDict

from langgraph.graph import END, StateGraph

from . import audit as A
from . import rulebook
from . import applicability, claims, qa, sources
from .checklist import score
from .llm import LLM
from .redact import redact
from .retrieval import Index


log = logging.getLogger(__name__)


class State(TypedDict, total=False):
    question: str
    policy: str
    language: str
    intent: str
    mapping: dict
    clauses: dict
    verdicts: dict
    findings: list
    result: dict
    trace: list
    llm: object
    degraded: str
    as_of: object
    answers: dict


def _timed(name: str, summary):
    def wrap(fn):
        def node(state: State) -> dict:
            t = time.perf_counter()
            out = fn(state) or {}
            step = {"agent": name, "status": "COMPLETED", "duration_ms": round((time.perf_counter() - t) * 1000), "output_summary": summary({**state, **out})}
            return {**out, "trace": [*state.get("trace", []), step]}
        return node
    return wrap


@_timed("orchestrator", lambda s: f"intent={s['intent']}, language={s['language']}")
def orchestrator(state: State) -> dict:
    text = state.get("question") or ""
    return {"language": qa.detect_language(text), "intent": "audit" if state.get("policy") else "question"}


@_timed("answer", lambda s: f"{len(s['result']['citations'])} citation(s), flags={s['result']['guardrail_flags']}")
def answer(state: State) -> dict:
    engine, llm = A.get_engine(rules=True), state.get("llm")
    if llm is not None:
        try:
            res = qa.answer(state["question"], engine, llm, "full")
            texts = {c["id"]: c["text"] for c in engine.chunks}
            return {"result": {**res, "claim_check": claims.check(res["answer"], [texts[h["id"]] for h in res["retrieved"] if h["id"] in texts])}}
        except Exception as e:  # model unavailable: degrade to the provisions themselves, and say so
            log.warning("answer agent: model unavailable (%s); returning retrieved provisions", type(e).__name__)
            state = {**state, "degraded": f"model unavailable ({type(e).__name__})"}
    if True:  # no model: return the retrieved provisions themselves
        hits, _ = engine.index.search(state["question"], k=3)
        text = "\n".join(f"- {h['text'][:400]} [{qa.label(h['provisions'][0]) if h.get('provisions') else ''}]" for h in hits)
        return {"result": {"answer": text, "citations": list(dict.fromkeys(p for h in hits for p in h.get("provisions", [])))[:8], "abstained": False, "guardrail_flags": [],
                           "language": state["language"], "retrieved": [{"id": h["id"], "provisions": h.get("provisions", []), "score": h["score"]} for h in hits],
                           "fabricated_citations": [], "outside_evidence": [], "mode": "extractive", "degraded": state.get("degraded")}}


@_timed("retrieval", lambda s: f"{sum(len(v) for v in s['clauses'].values())} policy clauses for {len(s['clauses'])} obligations")
def retrieval(state: State) -> dict:
    chunks = A.chunk_policy(state["policy"])
    clauses = A.retrieve_clauses(Index(chunks))
    # Dense + sparse retrieval can miss the clause a short query should find; add the section the rule book matched
    # for the obligation, so the judge always sees it.
    for oid, sec in rulebook.best_sections(state["policy"]).items():
        if not any(sec[:200] in h["text"] or h["text"][:200] in sec for h in clauses[oid]):
            clauses[oid] = [{"id": f"R-{oid}", "text": sec[:1500], "provisions": []}] + clauses[oid][:2]
    return {"clauses": clauses}


@_timed("obligation_mapping", lambda s: f"{len(s['mapping'])} obligations grounded in the knowledge base")
def obligation_mapping(state: State) -> dict:
    return {"mapping": A.map_obligations(A.get_engine(rules=True))}


@_timed("compliance", lambda s: f"{len(s['verdicts'])} verdicts")
def compliance(state: State) -> dict:
    llm = state.get("llm")
    if llm is not None:
        try:
            return {"verdicts": A.judge(state["clauses"], state["mapping"], llm)}
        except Exception as e:  # model unavailable: degrade to keyword rules, and say so in the report
            log.warning("compliance agent: model unavailable (%s); using keyword rules", type(e).__name__)
            return {"verdicts": A.judge_rules(state["policy"]), "llm": None, "degraded": f"model unavailable ({type(e).__name__})"}
    return {"verdicts": A.judge_rules(state["policy"])}


@_timed("guardrails", lambda s: f"{sum(bool(f['guardrail_flags']) for f in s['findings'])} finding(s) flagged")
def guardrails(state: State) -> dict:
    if state.get("llm") is None:  # keyword rules give no quotes to verify
        findings = A.raw_findings(state["verdicts"], state["policy"], state["mapping"])
    else:
        findings = A.apply_guardrails(state["verdicts"], state["policy"], state["mapping"], A.get_engine(rules=True), state["clauses"])
    rulebook.reconcile(findings, state["policy"])  # the same rule book the policy generator drafts against
    return {"findings": findings}


@_timed("risk", lambda s: f"score {s['result']['score']}")
def risk(state: State) -> dict:
    findings = state["findings"]
    for f in findings:  # raw findings carry fewer fields; fill from the mapping
        m = state["mapping"][f["id"]]
        f.setdefault("statute", m["statute"]), f.setdefault("principle", m["principle"]), f.setdefault("exemptions", m["exemptions"])
        f.setdefault("confidence", 0.5)
    A.assess_risk(findings, state["mapping"])
    sources.annotate(findings, state.get("as_of"))
    scope = applicability.assess(state.get("answers"), state["policy"])
    applicability.apply(findings, scope)
    for f in findings:
        if not f["applies"]:
            f["risk"] = "none"
        f["passages"] = [c["text"] for c in state.get("clauses", {}).get(f["id"], [])[:2]]  # the policy text the judge read
    conflicts = claims.conflicts(state["policy"])
    for f in findings:
        f["conflicts"] = [c for c in conflicts if c["obligation_id"] == f["id"]]
        # Support for the verdict: a verbatim quote, a clause the policy contradicts elsewhere, or no quote to check.
        f["support"] = ("conflicting" if f["conflicts"] else "quoted" if f.get("quote") and f.get("quote_verified", True)
                        else "not quoted" if f["status"] != "Missing" else "absent")
    return {"result": {"conflicts": conflicts, "applicability": {"answers": scope["answers"], "notes": scope["notes"]},"assessed_on": (state.get("as_of") or date.today()).isoformat(), "sources": SOURCE_VERSIONS,"score": score([f["status"] for f in findings]), "findings": findings,
                       "counts": {s: sum(f["status"] == s for f in findings) for s in ("Satisfied", "Partial", "Missing", "Not applicable")},
                       "judge": "llm" if state.get("llm") else "keyword rules", "degraded": state.get("degraded")}}


@lru_cache(maxsize=1)
def graph():
    g = StateGraph(State)
    for name, fn in (("orchestrator", orchestrator), ("answer", answer), ("retrieval", retrieval), ("obligation_mapping", obligation_mapping),
                     ("compliance", compliance), ("guardrails", guardrails), ("risk", risk)):
        g.add_node(name, fn)
    g.set_entry_point("orchestrator")
    g.add_conditional_edges("orchestrator", lambda s: s["intent"], {"question": "answer", "audit": "retrieval"})
    g.add_edge("answer", END)
    for a, b in (("retrieval", "obligation_mapping"), ("obligation_mapping", "compliance"), ("compliance", "guardrails"), ("guardrails", "risk")):
        g.add_edge(a, b)
    g.add_edge("risk", END)
    return g.compile()


def get_llm() -> LLM | None:
    """The configured model, or None in mock mode or without a key (the workflow then uses its rule fallbacks)."""
    from app.config import effective_llm_key, settings
    if settings.mock_llm or not effective_llm_key():
        return None
    llm = LLM(patience=3)  # a live request should fail over quickly, not wait out a rate limit
    return llm if llm.available else None


SOURCE_VERSIONS = [{"id": d["id"], "gazette": d["gazette"], "published": d["published"]} for d in sources.REGISTRY]


def run(question: str = "", policy: str | None = None, llm: LLM | None | str = "auto", as_of: date | None = None,
        answers: dict | None = None) -> dict:
    """Run the workflow. Personal data in a question is redacted before it is processed or logged."""
    question, redactions = redact(question or "")
    llm = get_llm() if llm == "auto" else llm
    state = graph().invoke({"question": question, "policy": policy or "", "llm": llm, "trace": [], "as_of": as_of, "answers": answers})
    return {**state["result"], "intent": state["intent"], "language": state["language"], "trace": state["trace"], "redactions": redactions}
