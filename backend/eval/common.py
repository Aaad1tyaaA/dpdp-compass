"""Shared evaluation helpers: corpus loading, ranking metrics, bootstrap statistics."""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.compass import layers, statute

BACKEND = Path(__file__).resolve().parents[1]
ACT_PDF = BACKEND.parent / "data" / "legal" / "DPDP_Act_2023.pdf"
RESULTS = BACKEND / "eval" / "results"
B = 10000
rng = np.random.default_rng(2023)


@lru_cache(maxsize=1)
def corpus():
    st = statute.parse(ACT_PDF)
    return st, layers.build(st)


def save(name: str, data) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / name
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return path


def load(name: str, default=None):
    path = RESULTS / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def rank_metrics(rel: list[bool], n_relevant: int) -> dict:
    """Metrics for one query from the relevance of its ranked top 10."""
    first = next((i for i, r in enumerate(rel, 1) if r), None)
    dcg = sum(1 / math.log2(i + 1) for i, r in enumerate(rel[:10], 1) if r)
    idcg = sum(1 / math.log2(i + 1) for i in range(1, min(10, max(n_relevant, 1)) + 1))
    return {"hit1": float(any(rel[:1])), "hit5": float(any(rel[:5])), "r10": float(any(rel[:10])),
            "mrr": 1 / first if first else 0.0, "ndcg10": min(1.0, dcg / idcg)}


def ci(values) -> tuple[float, float]:
    x = np.asarray(values, float)
    m = x[rng.integers(0, len(x), (B, len(x)))].mean(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def paired_p(a, b) -> float:
    """Two-sided paired bootstrap p-value for mean(a) != mean(b)."""
    d = np.asarray(a, float) - np.asarray(b, float)
    m = d[rng.integers(0, len(d), (B, len(d)))].mean(1)
    return float(max(1 / B, min(1.0, 2 * min((m <= 0).mean(), (m >= 0).mean()))))
