# Ideation Loop — Minimal Chat Rebuild (Restricted to Images + PDF)

## Condition Loop

1. **Minimal UI** — Previous dashboard had 4 cards, severity grids, metric grids, agent traces always visible → congested. Minimal keeps only: chat thread + upload/ask input + single evidence drawer. Metrics/evaluation hidden behind “Details” toggle. Required points only: compliance verdict per obligation (Satisfied/Partial/Missing), risk + citation, suggested fix + ideal policy (Business); plain rights summary + answer with citations (Citizen).

2. **Chat-like for both** — Business: “Upload your privacy policy → get audit report as chat reply → follow-up questions refine report/ideal policy”. Citizen: “Paste policy URL or ask ‘What does X company do with my data?’ → grounded answer”. Single `ChatShell` component shared, mode toggles system prompt.

3. **Only two images as context** — Rebuilt strictly from:
   - Fig2 Knowledge Base Pipeline (7 offline steps: Source Docs → PAKTON-style clause-aware chunking → Metadata (Section/Clause/Entity/Obligation/Principle/Source/Citation) → Triplet Extraction (RAGulating Compliance SPO) → Embedding → Hybrid KB (ChromaDB vector + Neo4j graph + Postgres metadata) → Three-Layer Structure (Facts/Obligations/Principles)).
   - Fig3 Multi-Agent Online (Orchestrator → Retrieval (hybrid semantic+graph top-k+citations) → Obligation Mapping → Compliance Checking (4 states) → Risk Assessment → Final Output, with feedback loop) + System Architecture overview (Data Sources 1 → KB 2 → Shared Engine 3 → Outputs 4 → Evaluation 5).
   No extra agents, no invented layers.

4. **PDF parsed + links verified** — DPDP core: 3 roles (Principal/Fiduciary/Processor), S8 obligations (notice, free/specific consent, stop on withdrawal, accuracy, security safeguards, breach notice, children verifiable consent + no tracking), Principal rights (access/correct/erase/restrict/portability), SDF extras, penalties ₹250cr (S8(5) top), enforcement 13 Nov 2025 / 13 Nov 2026 / 13 May 2027 (computed). Datasets: OPP-115/APP-350 mapped GDPR→DPDP precedent. Rulebook pile: Act/Rules/Timeline/KPMG. Papers verified: PAKTON EMNLP 2025 oral (multi-agent + RAG for long agreements), RAGulating 2508.09893 (ontology-free SPO + vector DB + multi-agent), LegalGraphRAG ACL 2026 (HierarGraph Facts/Ontology/Rule + Researcher/Auditor/Adjudicator → maps to our Facts/Obligations/Principles). RAG (Lewis 2020) + RAGAS (Es 2023).

5. **Methodology as core (unchanged)** — KB stays PAKTON chunking + RAGulating triplets + LegalGraphRAG three layers. Evaluation stays RAGAS (Context Precision, Faithfulness, Recall/Answer Relevance) + Citation Accuracy + Expert Checklist + Hallucination Detection + Overall Performance. No new metric invented.

6. **Web search enrichment** — Meity Gazette verified Section 8 text, dpdprules.org timeline, saralprivacy plain English confirms enforcement phasing; ACL Anthology confirms PAKTON 2025.emnlp-main.403; arXiv confirms RAGulating & LegalGraphRAG hierarchical graph motivation (granularity bias, verification). Knowledge kept subordinate to PDF.

## Decision

Business Mode = chat audit + ideal policy artifact. Citizen Mode = chat QA over same KB. Both share Engine 3; outputs diverge only at formatting (Structured report vs Simplified summary). Frontend becomes `ChatShell` with minimal chrome; backend already matches images except vector store naming (Qdrant in prior tech stack → switch to ChromaDB per Fig2/2.4).

## Minimal IA

- Top bar: Business | Citizen toggle + “How it works” minimal.
- Chat thread: user bubble (policy upload / question) + assistant bubble (audit cards or answer + citations).
- Input: file drop + text box (business text overrides upload).
- Drawer: “Evidence & Reasoning” expandable per finding/question, not default.
- No persistent dashboard grids.
