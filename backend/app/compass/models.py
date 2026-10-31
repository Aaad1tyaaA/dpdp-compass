"""The two retrieval models, with a light runtime for small servers.

load_embedder / load_reranker return objects with the sentence-transformers interface used across the app
(`encode(texts, normalize_embeddings=True)` and `predict(pairs)`). With sentence-transformers installed
(development, experiments) they are the PyTorch models; without it (the deployed image) the same models run
on ONNX via fastembed, which needs a fraction of the memory.
"""
from __future__ import annotations

import os

import numpy as np

# fastembed's names for the same weights
_THREADS = int(os.getenv("MODEL_THREADS", "1"))  # each onnxruntime thread keeps its own buffers; 1 fits a 512 MB server
_ONNX_NAMES = {"cross-encoder/ms-marco-MiniLM-L-6-v2": "Xenova/ms-marco-MiniLM-L-6-v2"}


def _torch_available() -> bool:
    if os.getenv("MODEL_RUNTIME", "").lower() == "onnx":
        return False
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


class _OnnxEmbedder:
    def __init__(self, name: str):
        from fastembed import TextEmbedding
        self.model = TextEmbedding(name, cache_dir=os.getenv("FASTEMBED_CACHE_PATH"), threads=_THREADS)

    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False, **_):
        # small batches: one big batch makes onnxruntime's memory pool grow past 1 GB and keep it
        v = np.asarray(list(self.model.embed(list(texts), batch_size=8)), dtype=np.float32)
        if normalize_embeddings and len(v):
            v /= np.linalg.norm(v, axis=1, keepdims=True).clip(min=1e-12)
        return v


class _OnnxReranker:
    def __init__(self, name: str):
        from fastembed.rerank.cross_encoder import TextCrossEncoder
        self.model = TextCrossEncoder(_ONNX_NAMES.get(name, name), cache_dir=os.getenv("FASTEMBED_CACHE_PATH"), threads=_THREADS)

    def predict(self, pairs, show_progress_bar=False, **_):
        """Scores per (query, text) pair; only their order is used."""
        out = np.zeros(len(pairs), dtype=np.float32)
        by_query: dict[str, list[int]] = {}
        for i, (q, _t) in enumerate(pairs):
            by_query.setdefault(q, []).append(i)
        for q, idx in by_query.items():
            out[idx] = list(self.model.rerank(q, [pairs[i][1] for i in idx], batch_size=4))
        return out


def load_embedder(name: str):
    if _torch_available():
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(name)
    return _OnnxEmbedder(name)


def load_reranker(name: str):
    if _torch_available():
        from sentence_transformers import CrossEncoder
        return CrossEncoder(name)
    return _OnnxReranker(name)


if __name__ == "__main__":  # self-check: both runtimes give the same ranking
    import sys
    q = "How long can a company keep my personal data?"
    docs = ["The Data Fiduciary shall erase personal data once the purpose is no longer served.",
            "The Board shall consist of a Chairperson and other Members.",
            "A child means an individual who has not completed eighteen years of age."]
    os.environ["MODEL_RUNTIME"] = "onnx"
    e = _OnnxEmbedder("sentence-transformers/all-MiniLM-L6-v2"); r = _OnnxReranker("cross-encoder/ms-marco-MiniLM-L-6-v2")
    onnx_rank = list(np.argsort(-(e.encode(docs) @ e.encode([q])[0]))), list(np.argsort(-r.predict([(q, d) for d in docs])))
    print("onnx  dense", onnx_rank[0], "rerank", onnx_rank[1])
    try:
        from sentence_transformers import CrossEncoder, SentenceTransformer
        se = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2"); sr = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        a, b = se.encode(docs, normalize_embeddings=True), se.encode([q], normalize_embeddings=True)[0]
        print("torch dense", list(np.argsort(-(a @ b))), "rerank", list(np.argsort(-sr.predict([(q, d) for d in docs]))))
        print("max |cos diff|", float(np.abs(e.encode(docs) @ e.encode([q])[0] - a @ b).max()))
    except ImportError:
        sys.exit(0)
