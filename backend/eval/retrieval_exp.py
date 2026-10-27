"""Retrieval experiments: knowledge-base statistics, chunking ablation, fusion weights, retrieval ablation.

    python -m eval.retrieval_exp

No generation is involved; the only model calls translate the Hindi and Marathi questions to English
for search (cached). Writes eval/results/retrieval.json.
"""
from __future__ import annotations

import time

import numpy as np

from app.compass import statute
from app.compass.llm import LLM, QuotaExhausted
from app.compass.retrieval import Index

from . import dpdp_qa
from .common import ci, corpus, paired_p, rank_metrics, save

GRAPH_WEIGHTS = [0.0, 0.1, 0.25, 0.5, 1.0]
TRANSLATE = ("Translate the user's question into English for searching the text of India's Digital Personal Data "
             "Protection Act, 2023. Keep section numbers. Reply with the English question only.")


def translate(items: list[dict]) -> dict[str, str]:
    """English search queries for the non-English questions (the answer language is unaffected)."""
    out, models = {}, [None, "qwen/qwen3.8-27b"]
    for it in items:
        if it["lang"] == "en":
            continue
        for model in models:
            try:
                out[it["id"]] = LLM(model=model).complete(TRANSLATE, it["question"], 120).strip()
                break
            except QuotaExhausted:
                continue
    return out


def run(index: Index, items: list[dict], queries: dict[str, str], **search) -> tuple[dict, dict]:
    per, ms, chars = {k: [] for k in ("hit1", "hit5", "r10", "mrr", "ndcg10")}, [], []
    n_rel = {it["id"]: sum(dpdp_qa.relevant(t, it) for t in index.texts) for it in items}
    for it in items:
        hits, timing = index.search(queries.get(it["id"], it["question"]), k=10, **search)
        m = rank_metrics([dpdp_qa.relevant(h["text"], it) for h in hits], n_rel[it["id"]])
        for k, v in m.items():
            per[k].append(v)
        ms.append(timing["total_ms"])
        chars.append(sum(len(h["text"]) for h in hits[:5]))
    summary = {k: round(float(np.mean(v)), 3) for k, v in per.items()}
    summary.update(ms_per_query=round(float(np.median(ms)), 1), chars_top5=round(float(np.mean(chars))),
                   ndcg10_ci=[round(x, 3) for x in ci(per["ndcg10"])], n=len(items))
    return summary, per


def main():
    st, kb = corpus()
    items = dpdp_qa.load()
    problems = dpdp_qa.validate(items, st)
    assert not problems, problems
    queries = translate(items)
    ours = statute.chunk_clause_aware(st, 1200)
    lengths = [len(c["text"]) for c in ours]
    out = {"dataset": {"hash": dpdp_qa.dataset_hash(items), "items": len(items),
                       "by_lang": {l: sum(i["lang"] == l for i in items) for l in ("en", "hi", "mr")},
                       "dev": sum(i["split"] == "dev" for i in items), "test": sum(i["split"] == "test" for i in items),
                       "unanswerable": sum(not i["answerable"] for i in items),
                       "sections_covered": len({i["provision"].split("(")[0] for i in items if i["answerable"] and i["provision"] != "Schedule"}),
                       "types": sorted({i["type"] for i in items}), "translated": len(queries)},
           "kb": {"chunks": len(ours), "mean_chars": round(float(np.mean(lengths))), "max_chars": max(lengths), "sections": len(st.sections),
                  "pages": st.schedule_page, **kb.counts()},
           "translations": queries}

    # 1. Chunking ablation: English test questions, dense + BM25+ fused by RRF, no re-ranking, no metadata lookup.
    en_test = [i for i in items if i["split"] == "test" and i["answerable"] and i["lang"] == "en"]
    plain = {"weights": {"dense": 1, "sparse": 1}, "rerank": False}
    chunkers = [("Clause-aware, 1,200 (ours)", ours), ("Clause-aware, 600", statute.chunk_clause_aware(st, 600)),
                ("Whole sections", statute.chunk_sections(st)), ("Fixed windows, 1,200", statute.chunk_fixed(st, 1200)),
                ("Fixed windows, 600", statute.chunk_fixed(st, 600)), ("Fixed windows, 300", statute.chunk_fixed(st, 300))]
    rows, per_chunker = [], {}
    for name, chunks in chunkers:
        summary, per = run(Index(chunks), en_test, queries, **plain)
        rows.append({"chunking": name, "chunks": len(chunks), **summary})
        per_chunker[name] = per
        print("chunking", name, summary, flush=True)
    out["chunking"] = {"n": len(en_test), "rows": rows,
                       "p_mrr_ours_vs_fixed1200": paired_p(per_chunker[chunkers[0][0]]["mrr"], per_chunker[chunkers[3][0]]["mrr"]),
                       "p_mrr_ours_vs_sections": paired_p(per_chunker[chunkers[0][0]]["mrr"], per_chunker[chunkers[2][0]]["mrr"])}

    # 2. Fusion weights on the development split (before re-ranking).
    index = Index(ours, kb)
    dev = [i for i in items if i["split"] == "dev" and i["answerable"]]
    grid = []
    for meta in (0.0, 1.0, 2.0):
        for g in GRAPH_WEIGHTS:
            s, _ = run(index, dev, queries, weights={"dense": 1, "sparse": 1, "metadata": meta, "graph": g}, rerank=False)
            grid.append({"metadata": meta, "graph": g, "ndcg10": s["ndcg10"], "mrr": s["mrr"], "hit5": s["hit5"]})
    best = max(grid, key=lambda r: (r["ndcg10"], r["mrr"], -r["graph"]))
    out["fusion"] = {"n": len(dev), "grid": grid, "chosen": best,
                     "graph_sweep_at_metadata_2": [r for r in grid if r["metadata"] == 2.0]}
    chosen = {"dense": 1.0, "sparse": 1.0, "metadata": best["metadata"], "graph": best["graph"]}
    print("fusion chosen", best, flush=True)

    # 3. Retrieval ablation on the test split (answerable questions, non-English ones translated for search).
    test = [i for i in items if i["split"] == "test" and i["answerable"]]
    systems = [
        ("Dense (MiniLM)", {"weights": {"dense": 1}, "rerank": False}),
        ("Sparse (BM25+)", {"weights": {"sparse": 1}, "rerank": False}),
        ("Graph", {"weights": {"graph": 1}, "rerank": False}),
        ("Dense + sparse, weighted", {"weights": {"dense": 1, "sparse": 1}, "rerank": False, "fusion": "weighted"}),
        ("Dense + sparse, RRF", {"weights": {"dense": 1, "sparse": 1}, "rerank": False}),
        (" + graph, equal vote", {"weights": {"dense": 1, "sparse": 1, "graph": 1}, "rerank": False}),
        (" + metadata lookup", {"weights": {**chosen, "graph": 0.0}, "rerank": False}),
        (" + re-ranking (full)", {"weights": chosen, "rerank": True}),
        ("Dense + re-ranking", {"weights": {"dense": 1}, "rerank": True}),
    ]
    index.search("warm up", rerank=True)
    rows, per_system = [], {}
    for name, cfg in systems:
        t = time.perf_counter()
        summary, per = run(index, test, queries, **cfg)
        rows.append({"system": name, **summary})
        per_system[name] = per
        print("retrieval", name, summary, f"{time.perf_counter() - t:.0f}s", flush=True)
    full, dense = per_system[" + re-ranking (full)"], per_system["Dense (MiniLM)"]
    out["retrieval"] = {"n": len(test), "by_lang": {l: sum(i["lang"] == l for i in test) for l in ("en", "hi", "mr")}, "rows": rows,
                        "weights": chosen,
                        "p_full_vs_dense": {"hit1": paired_p(full["hit1"], dense["hit1"]), "ndcg10": paired_p(full["ndcg10"], dense["ndcg10"])},
                        "p_full_vs_rrf": {"hit1": paired_p(full["hit1"], per_system["Dense + sparse, RRF"]["hit1"]),
                                          "ndcg10": paired_p(full["ndcg10"], per_system["Dense + sparse, RRF"]["ndcg10"])},
                        "p_graph_vote_vs_rrf_ndcg10": paired_p(per_system[" + graph, equal vote"]["ndcg10"], per_system["Dense + sparse, RRF"]["ndcg10"])}
    print("saved", save("retrieval.json", out))


if __name__ == "__main__":
    main()
