"""Audit experiment on DPDP-Synth: keyword rules, single prompt, and the pipeline with and without guardrails.

    python -m eval.audit_exp            # resumable: model responses are cached on disk

Writes eval/results/audit.json. If the provider's daily limit is reached the run stops and reports
only the policies completed by every system.
"""
from __future__ import annotations

import time

import numpy as np

from app.compass import audit as A
from app.compass.checklist import CHECKLIST, STATUSES, score
from app.compass.llm import LLM, QuotaExhausted
from app.compass.retrieval import Index

from . import synth
from .common import ci, load, save

SYSTEMS = ["Keyword rules", "Single prompt", "Pipeline, no guardrails", "Pipeline + guardrails (full)"]


def kappa(gold: list[str], pred: list[str]) -> float:
    n = len(gold)
    po = sum(g == p for g, p in zip(gold, pred)) / n
    pe = sum((gold.count(s) / n) * (pred.count(s) / n) for s in STATUSES)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def f1(gold: list[str], pred: list[str], cls: str) -> float:
    tp = sum(g == cls and p == cls for g, p in zip(gold, pred))
    fp = sum(g != cls and p == cls for g, p in zip(gold, pred))
    fn = sum(g == cls and p != cls for g, p in zip(gold, pred))
    return 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0


def summarise(rows: list[dict], policies: dict[str, dict]) -> dict:
    gold = [policies[r["policy"]]["labels"][f["id"]] for r in rows for f in r["findings"]]
    pred = [f["status"] for r in rows for f in r["findings"]]
    per_policy_acc = [np.mean([policies[r["policy"]]["labels"][f["id"]] == f["status"] for f in r["findings"]]) for r in rows]
    err = [abs(score([f["status"] for f in r["findings"]]) - score(list(policies[r["policy"]]["labels"].values()))) for r in rows]
    shown = [f for r in rows for f in r["findings"] if f["status"] != "Missing"]
    inj = [(policies[r["policy"]]["labels"][f["id"]], f["status"]) for r in rows if policies[r["policy"]]["injected"] for f in r["findings"]]
    clean = [(policies[r["policy"]]["labels"][f["id"]], f["status"]) for r in rows if not policies[r["policy"]]["injected"] for f in r["findings"]]
    false_sat = lambda pairs: (sum(g != "Satisfied" and p == "Satisfied" for g, p in pairs) / max(1, sum(g != "Satisfied" for g, _ in pairs)))
    hard = [(f["status"]) for r in rows for f in r["findings"] if policies[r["policy"]]["kinds"][f["id"]] == "hard_negative"]
    lo, hi = ci(per_policy_acc)
    return {"policies": len(rows), "decisions": len(gold), "accuracy": round(float(np.mean([g == p for g, p in zip(gold, pred)])), 3),
            "accuracy_ci": [round(lo, 3), round(hi, 3)], "macro_f1": round(float(np.mean([f1(gold, pred, s) for s in STATUSES])), 3),
            "f1": {s: round(f1(gold, pred, s), 3) for s in STATUSES}, "kappa": round(kappa(gold, pred), 3),
            "score_mae": round(float(np.mean(err)), 1), "verified_quote_rate": round(sum(f["quote_verified"] for f in shown) / len(shown), 3) if shown else None,
            "false_satisfied_injected": round(false_sat(inj), 3), "false_satisfied_clean": round(false_sat(clean), 3),
            "hard_negative_correct": round(sum(s == "Missing" for s in hard) / len(hard), 3) if hard else None,
            "tokens_per_policy": round(float(np.mean([r["tokens"] for r in rows]))), "calls_per_policy": round(float(np.mean([r["calls"] for r in rows])), 2),
            "seconds_per_policy": round(float(np.median([r["seconds"] for r in rows])), 2)}


def main():
    engine = A.get_engine()
    mapping = A.map_obligations(engine)
    policies = synth.generate()
    by_id = {p["id"]: p for p in policies}
    llm = LLM()
    rows = {s: [] for s in SYSTEMS}
    stopped = None
    for p in policies:
        try:
            t = time.perf_counter()
            rules = A.raw_findings(A.judge_rules(p["text"]), p["text"], mapping)
            t_rules = time.perf_counter() - t

            llm.reset()
            t = time.perf_counter()
            chunks = A.chunk_policy(p["text"])
            clauses = A.retrieve_clauses(Index(chunks))
            verdicts = A.judge(clauses, mapping, llm)
            t_pipe, use_pipe = time.perf_counter() - t - llm.wait, (llm.calls, llm.prompt_tokens + llm.completion_tokens)

            llm.reset()
            t = time.perf_counter()
            single = A.judge_single_prompt(p["text"], llm)
            t_single, use_single = time.perf_counter() - t - llm.wait, (llm.calls, llm.prompt_tokens + llm.completion_tokens)
        except QuotaExhausted as e:
            stopped = f"{e}; {len(rows[SYSTEMS[0]])} of {len(policies)} policies completed"
            print(stopped, flush=True)
            break
        t = time.perf_counter()
        guarded = A.apply_guardrails(verdicts, p["text"], mapping, engine, clauses)
        t_guard = time.perf_counter() - t
        rows["Keyword rules"].append({"policy": p["id"], "findings": rules, "tokens": 0, "calls": 0, "seconds": t_rules})
        rows["Single prompt"].append({"policy": p["id"], "findings": A.raw_findings(single, p["text"], mapping), "tokens": use_single[1], "calls": use_single[0], "seconds": t_single})
        rows["Pipeline, no guardrails"].append({"policy": p["id"], "findings": A.raw_findings(verdicts, p["text"], mapping), "tokens": use_pipe[1], "calls": use_pipe[0], "seconds": t_pipe})
        rows["Pipeline + guardrails (full)"].append({"policy": p["id"], "findings": guarded, "tokens": use_pipe[1], "calls": use_pipe[0], "seconds": t_pipe + t_guard})
        print(p["id"], "done", {s: sum(by_id[p["id"]]["labels"][f["id"]] == f["status"] for f in rows[s][-1]["findings"]) for s in SYSTEMS}, flush=True)

    labels = [l for p in policies for l in p["labels"].values()]
    out = {"dataset": {"hash": synth.dataset_hash(policies), "policies": len(policies), "obligations": len(CHECKLIST), "decisions": len(labels),
                       "labels": {s: labels.count(s) for s in STATUSES}, "injected": sum(p["injected"] for p in policies),
                       "hard_negatives": sum(k == "hard_negative" for p in policies for k in p["kinds"].values())},
           "model": llm.model, "complete": stopped is None, "stopped": stopped,
           "systems": {s: summarise(r, by_id) for s, r in rows.items() if r},
           "guardrail_flags": {}, "raw": rows}
    for r in rows["Pipeline + guardrails (full)"]:
        for f in r["findings"]:
            for flag in f["guardrail_flags"]:
                out["guardrail_flags"][flag] = out["guardrail_flags"].get(flag, 0) + 1
            if f["model_status"] != f["status"]:
                out["guardrail_flags"]["status_changed"] = out["guardrail_flags"].get("status_changed", 0) + 1
    print({s: {k: v for k, v in m.items() if k in ("policies", "accuracy", "macro_f1", "kappa", "tokens_per_policy")} for s, m in out["systems"].items()})
    print("saved", save("audit.json", out))


if __name__ == "__main__":
    main()
