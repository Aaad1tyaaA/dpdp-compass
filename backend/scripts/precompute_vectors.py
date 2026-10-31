"""Runs the start-up indexing once and saves every passage vector to EMBED_CACHE (used at image build).

    EMBED_CACHE=/opt/models/vectors.npz python scripts/precompute_vectors.py
The server then reads these vectors at start instead of embedding the Act, the Rules and the reference
policies again (about 3 minutes on a free instance). Needs MODEL_RUNTIME=onnx (the deployed runtime).
"""
import asyncio, os, sys

os.environ.update(EMBED_CACHE_WRITE="1", MOCK_LLM="false", MODEL_RUNTIME="onnx")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.knowledge_base.auto_indexer import initialize_default_knowledge_base  # noqa: E402
from app.hardening import warm_engine  # noqa: E402
from app.compass.models import save_vectors  # noqa: E402

asyncio.run(initialize_default_knowledge_base())
warm_engine()
print("saved", save_vectors(), "vectors to", os.environ["EMBED_CACHE"])
