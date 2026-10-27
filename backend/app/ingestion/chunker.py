"""Figure 2 Knowledge Base Construction (Offline Pipeline) — minimal deterministic stubs
2.1 Clause-aware Chunking (PAKTON-style section based) → 2.2 Metadata Extraction → 2.3 Triplet Extraction (RAGulating Compliance SPO) → 2.4 Hybrid KB (ChromaDB/Neo4j/Postgres) → 2.5 Three-Layer Structure
"""
import re
from dataclasses import dataclass

@dataclass
class ClauseChunk:
    id: str
    text: str
    section: str | None
    clause: str | None
    entities: list[str]
    obligation: str | None
    principle: str | None

def clause_aware_chunk(text: str) -> list[ClauseChunk]:
    # Split on headings like "Section X" or numbered clauses
    parts = re.split(r"\n(?=Section\s+\d+|Clause\s+\d+|\d+\.\s)", text)
    chunks = []
    for i, p in enumerate([x.strip() for x in parts if x.strip()]):
        m = re.search(r"Section\s+(\d+(?:\.\d+)?)", p)
        section = m.group(0) if m else f"Section {i+1}"
        chunks.append(ClauseChunk(
            id=f"chunk_{i}", text=p[:2000], section=section, clause=f"Clause {i+1}",
            entities=[], obligation=None, principle=None
        ))
    return chunks or [ClauseChunk(id="chunk_0", text=text[:2000], section="Section 1", clause="Clause 1", entities=[], obligation=None, principle=None)]

def extract_triplets(chunk: ClauseChunk) -> list[tuple[str,str,str]]:
    # 2.3 RAGulating Compliance: SPO triplets (e.g., "Data Fiduciary — must obtain — verifiable consent")
    return [("Data Fiduciary", "must notify", "Data Protection Board"), ("Data Principal", "has right to", "withdraw consent")]

def build_knowledge_layers(chunks: list[ClauseChunk]):
    # 2.5 Three-Layer Legal Knowledge Structure per LegalGraphRAG: Facts (what exists) / Obligations (what must be done) / DPDP Principles (why it matters)
    return {
        "facts": [{"chunk": c.id, "text": c.text[:200]} for c in chunks],
        "obligations": [{"id": f"obl_{i}", "text": c.text[:200]} for i,c in enumerate(chunks)],
        "principles": ["Consent", "Purpose Limitation", "Storage Limitation", "Accountability"]
    }

# 2.4 Hybrid Legal Knowledge Base — ChromaDB (vectors), Neo4j (triplets graph), Postgres/SQLite (metadata)
HYBRID_KB = {"vector_store": "ChromaDB", "knowledge_graph": "Neo4j", "metadata_store": "PostgreSQL/SQLite"}
