"""The two retrieval models, with a light runtime for small servers.

load_embedder / load_reranker return objects with the sentence-transformers interface used across the app
(`encode(texts, normalize_embeddings=True)` and `predict(pairs)`). With sentence-transformers installed
(development, experiments) they are the PyTorch models; without it (the deployed image) the same models run
on ONNX via fastembed, which needs a fraction of the memory.
"""
from __future__ import annotations

import os

import numpy as np

_THREADS = int(os.getenv("MODEL_THREADS", "1"))  # each onnxruntime thread keeps its own buffers; 1 fits a 512 MB server
# int8 copies of the same two models: 87 MB together instead of ~225 MB. On the DPDP chunks they agree with the
# full-precision models on the top dense hit and the top re-ranked hit for every test question (MODEL_INT8=0: fp32).
_INT8 = os.getenv("MODEL_INT8", "1") != "0"
_ONNX_NAMES = {"sentence-transformers/all-MiniLM-L6-v2": "dpdp/all-MiniLM-L6-v2-int8" if _INT8 else "sentence-transformers/all-MiniLM-L6-v2",
               "cross-encoder/ms-marco-MiniLM-L-6-v2": "dpdp/ms-marco-MiniLM-L-6-v2-int8" if _INT8 else "Xenova/ms-marco-MiniLM-L-6-v2"}
_registered = False


def _register_int8() -> None:
    global _registered
    if _registered or not _INT8:
        return
    from fastembed import TextEmbedding
    from fastembed.common.model_description import ModelSource, PoolingType
    from fastembed.rerank.cross_encoder import TextCrossEncoder
    TextEmbedding.add_custom_model("dpdp/all-MiniLM-L6-v2-int8", PoolingType.MEAN, True,
                                   ModelSource(hf="Xenova/all-MiniLM-L6-v2"), 384, model_file="onnx/model_quantized.onnx")
    TextCrossEncoder.add_custom_model("dpdp/ms-marco-MiniLM-L-6-v2-int8", ModelSource(hf="Xenova/ms-marco-MiniLM-L-6-v2"),
                                      model_file="onnx/model_quantized.onnx")
    _registered = True


def _lean_onnx_sessions() -> None:
    """Turn off onnxruntime's memory arena and pattern cache for every session fastembed opens. They keep
    hundreds of MB reserved; without them the models fit a 512 MB server, at a small speed cost."""
    import onnxruntime as ort
    if getattr(ort.InferenceSession, "_lean", False):
        return
    base = ort.InferenceSession

    class Lean(base):
        _lean = True

        def __init__(self, path, sess_options=None, *a, **kw):
            so = sess_options or ort.SessionOptions()
            so.enable_cpu_mem_arena = False
            so.enable_mem_pattern = False
            super().__init__(path, so, *a, **kw)

    ort.InferenceSession = Lean


def _torch_available() -> bool:
    if os.getenv("MODEL_RUNTIME", "").lower() == "onnx":
        return False
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


_VECTORS = os.getenv("EMBED_CACHE")  # file of precomputed vectors, filled at image build (save_vectors)
_embedders: list = []


class _OnnxEmbedder:
    def __init__(self, name: str):
        _lean_onnx_sessions(); _register_int8()
        from fastembed import TextEmbedding
        self.model = TextEmbedding(_ONNX_NAMES.get(name, name), cache_dir=os.getenv("FASTEMBED_CACHE_PATH"), threads=_THREADS)
        # The law and reference policies are the same text on every start: their vectors are computed once when
        # the image is built and read back here, instead of ~3 minutes of embedding on a small server's CPU.
        self.saved: dict[str, np.ndarray] = {}
        if _VECTORS and os.path.exists(_VECTORS):
            with np.load(_VECTORS) as f:
                self.saved = dict(zip(f["keys"].tolist(), f["vectors"]))
        self.recording = os.getenv("EMBED_CACHE_WRITE") == "1"
        _embedders.append(self)

    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False, **_):
        import hashlib
        texts = list(texts)
        keys = [hashlib.sha1(t.encode("utf-8")).hexdigest() for t in texts]
        todo = [i for i, k in enumerate(keys) if k not in self.saved]
        fresh = {}
        if todo:
            # small batches: one big batch makes onnxruntime's memory pool grow past 1 GB and keep it
            new = np.asarray(list(self.model.embed([texts[i] for i in todo], batch_size=8)), dtype=np.float32)
            new /= np.linalg.norm(new, axis=1, keepdims=True).clip(min=1e-12)
            fresh = {keys[i]: new[j] for j, i in enumerate(todo)}
            if self.recording:
                self.saved.update(fresh)
        v = np.asarray([self.saved[k] if k in self.saved else fresh[k] for k in keys], dtype=np.float32).reshape(len(keys), -1)
        return v  # always unit length (normalize_embeddings=False is never used in this app)


def save_vectors() -> int:
    """Write every vector recorded so far (EMBED_CACHE_WRITE=1) to EMBED_CACHE; returns how many."""
    saved = {k: v for e in _embedders for k, v in e.saved.items()}
    np.savez(_VECTORS, keys=np.array(list(saved)), vectors=np.asarray(list(saved.values()), dtype=np.float32))
    return len(saved)


class _OnnxReranker:
    def __init__(self, name: str):
        _lean_onnx_sessions(); _register_int8()
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
