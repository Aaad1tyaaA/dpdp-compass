"""Hybrid retrieval: dense, sparse (BM25+), metadata lookup and graph, merged by weighted Reciprocal
Rank Fusion and re-ranked by a cross-encoder.

    index = Index(chunks, kb)                      # any chunk list: the Act, or a policy under audit
    hits, timing = index.search("...", k=10)       # the deployed configuration
    index.search(q, weights={"dense": 1}, rerank=False)   # any ablation

score(d) = sum over retrievers r of w_r / (60 + rank_r(d)).
"""
from __future__ import annotations

import logging
import re
import threading
import time
from functools import lru_cache

import numpy as np
from rank_bm25 import BM25Plus

from .layers import GraphRetriever, KnowledgeBase

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEPLOYED = {"dense": 1.0, "sparse": 1.0, "metadata": 1.0, "graph": 0.0}  # chosen on the DPDP-QA development split
RRF_K = 60
_STOP = set("a an and are as at be been but by can do does for from had has have her his how i if in into is it its may me my "
            "no not of on or our shall she should so such than that the their them then there these they this to under upon was "
            "we were what when where which who will with would you your any all also about".split())


def stems(text: str) -> list[str]:
    """Lower-case content words cut to six characters (consent / consents / consented share a stem)."""
    return [w[:6] for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 1]


_load_lock = threading.Lock()


def _load(factory, name: str):
    """Load a model once at a time, retrying: transformers is not safe when two models initialise
    concurrently in different threads (the second can come up with empty 'meta' weights)."""
    last = None
    for attempt in range(4):
        with _load_lock:
            try:
                return factory(name)
            except NotImplementedError as e:  # another loader was mid-initialisation; wait and retry
                last = e
        time.sleep(2 + attempt)
    raise last


@lru_cache(maxsize=2)
def embedder(name: str = EMBEDDING_MODEL):
    from sentence_transformers import SentenceTransformer
    return _load(SentenceTransformer, name)


@lru_cache(maxsize=1)
def reranker(name: str = RERANK_MODEL):
    from sentence_transformers import CrossEncoder
    return _load(CrossEncoder, name)


_PROV = [
    (re.compile(r"sub-?section \((\d+)\) of section (\d+)", re.I), lambda m: f"{m[2]}({m[1]})"),
    (re.compile(r"\b(?:section|sec\.?|s\.)\s*(\d+)((?:\s?\([0-9a-z]{1,2}\))*)", re.I), lambda m: m[1] + re.sub(r"\s", "", m[2] or "")),
    (re.compile(r"\brules?\s*(\d+)((?:\s?\([0-9a-z]{1,3}\))*)", re.I), lambda m: "R" + m[1] + re.sub(r"\s", "", m[2] or "")),
    (re.compile(r"\b(first|second|third|fourth|fifth|sixth|seventh) schedule", re.I),
     lambda m: "Sch" + str(["first", "second", "third", "fourth", "fifth", "sixth", "seventh"].index(m[1].lower()) + 1)),
]


def named_provisions(query: str) -> list[str]:
    out = [make(m) for rx, make in _PROV for m in rx.finditer(query)]
    if re.search(r"\bschedule\b", query, re.I):
        out.append("Schedule")
    return list(dict.fromkeys(out))


def rrf(lists: dict[str, list[int]], weights: dict[str, float]) -> dict[int, float]:
    fused: dict[int, float] = {}
    for name, ranked in lists.items():
        w = weights.get(name, 0.0)
        if w:
            for rank, i in enumerate(ranked, 1):
                fused[i] = fused.get(i, 0.0) + w / (RRF_K + rank)
    return fused


class Index:
    def __init__(self, chunks: list[dict], kb: KnowledgeBase | None = None, embed: bool = True):
        self.chunks = chunks
        self.texts = [c["text"] for c in chunks]
        self.bm25 = BM25Plus([stems(t) or ["_"] for t in self.texts])
        self.vectors = np.asarray(embedder().encode(self.texts, normalize_embeddings=True, show_progress_bar=False)) if embed and chunks else None
        self.graph = GraphRetriever(kb) if kb else None
        self.by_prov: dict[str, list[int]] = {}
        for i, c in enumerate(chunks):
            for p in c.get("provisions", []):
                self.by_prov.setdefault(p, []).append(i)
                self.by_prov.setdefault(p.split("(")[0], [])
                if i not in self.by_prov[p.split("(")[0]]:
                    self.by_prov[p.split("(")[0]].append(i)

    # ── the four retrievers; each returns chunk indexes, best first ─────────
    def dense(self, query: str, n: int) -> list[tuple[int, float]]:
        scores = self.vectors @ embedder().encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
        return [(int(i), float(scores[i])) for i in np.argsort(-scores)[:n]]

    def sparse(self, query: str, n: int) -> list[tuple[int, float]]:
        scores = self.bm25.get_scores(stems(query) or ["_"])
        floor = scores.min()  # BM25+ gives every document a positive floor; keep real matches only
        return [(int(i), float(scores[i])) for i in np.argsort(-scores)[:n] if scores[i] > floor]

    def chunks_for(self, provision: str) -> list[int]:
        """Chunks holding a provision: exact, else its parent sub-section, else its whole section."""
        p = provision
        while p:
            if p in self.by_prov:
                return self.by_prov[p]
            covering = [i for q, idx in self.by_prov.items() if q.startswith(p + "(") for i in idx]
            if covering:
                return list(dict.fromkeys(covering))
            p = p[:p.rfind("(")] if "(" in p else ""
        return []

    def metadata(self, query: str) -> list[int]:
        out: list[int] = []
        for p in named_provisions(query):
            out += [i for i in self.chunks_for(p) if i not in out]
        return out

    def graph_lookup(self, query: str, seeds: list[int], n: int) -> list[int]:
        if not self.graph:
            return []
        seed_provs = [p for i in seeds for p in self.chunks[i].get("provisions", [])]
        scored: dict[int, float] = {}
        for prov, s in self.graph.provisions(query, seed_provs).items():
            for i in self.chunks_for(prov):
                scored[i] = scored.get(i, 0.0) + s
        return sorted(scored, key=lambda i: -scored[i])[:n]

    # ── fusion and re-ranking ───────────────────────────────────────────────
    def search(self, query: str, k: int = 10, weights: dict[str, float] | None = None, rerank: bool = True,
               pool: int = 20, fusion: str = "rrf", alpha: float = 0.5) -> tuple[list[dict], dict]:
        w = DEPLOYED if weights is None else weights
        t0 = time.perf_counter()
        lists: dict[str, list[int]] = {}
        d = self.dense(query, 50) if w.get("dense") else []
        s = self.sparse(query, 50) if w.get("sparse") else []
        if d:
            lists["dense"] = [i for i, _ in d]
        if s:
            lists["sparse"] = [i for i, _ in s]
        if w.get("metadata"):
            lists["metadata"] = self.metadata(query)
        if w.get("graph"):
            seeds = sorted(rrf({k_: v for k_, v in lists.items() if k_ in ("dense", "sparse")}, {"dense": 1, "sparse": 1}).items(), key=lambda x: -x[1])[:3]
            lists["graph"] = self.graph_lookup(query, [i for i, _ in seeds], 50)
        if fusion == "weighted":  # convex combination of min-max normalised scores (dense and sparse only)
            fused = {}
            for part, weight in ((d, alpha), (s, 1 - alpha)):
                if part:
                    lo, hi = min(x for _, x in part), max(x for _, x in part)
                    for i, x in part:
                        fused[i] = fused.get(i, 0.0) + weight * ((x - lo) / (hi - lo) if hi > lo else 1.0)
        else:
            fused = rrf(lists, w)
        ranked = sorted(fused, key=lambda i: -fused[i])
        t_retrieve = time.perf_counter() - t0
        reranked = False
        if rerank and ranked:
            head = ranked[:pool]
            try:
                scores = reranker().predict([(query, self.texts[i]) for i in head], show_progress_bar=False)
            except Exception as e:  # serve the fused ranking; a re-ranker fault must not fail the request
                logging.getLogger(__name__).warning("re-ranking skipped: %s", type(e).__name__)
            else:
                order = [head[j] for j in np.argsort(-np.asarray(scores))]
                for j, i in enumerate(order):
                    fused[i] = float(len(order) - j)  # keep a monotone score after re-ranking
                ranked, reranked = order + ranked[pool:], True
        hits = [{**self.chunks[i], "score": round(float(fused[i]), 5), "rank": r,
                 "sources": [name for name, l in lists.items() if i in l]} for r, i in enumerate(ranked[:k], 1)]
        return hits, {"retrieve_ms": round(t_retrieve * 1000, 2), "total_ms": round((time.perf_counter() - t0) * 1000, 2), "reranked": reranked}
