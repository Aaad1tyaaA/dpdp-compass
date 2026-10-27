# Multi-Agent RAG System for DPDP Act Compliance & Citizen Rights Awareness

Production-quality prototype — B.Tech final year, research-paper ready.

## Architecture
```
Data Sources → Knowledge Base (Vector Qdrant + Graph Neo4j + Postgres) → LangGraph Multi-Agent Engine (Orchestrator→Retrieval→Obligation Mapping→Compliance Checking→Risk & Reporting→Guardrails) → Business/Citizen Output → Evaluation Layer
```

Evidence-first: Legal obligation → legal evidence → policy evidence → comparison → decision → citation-backed explanation.

## Stack
- Frontend: React 18 + TypeScript + Vite + Tailwind — design inspired by Lumeo AI Assistant (Dribbble 25706500) adapted for legal-tech
- Backend: Python FastAPI (async), LangGraph
- KB: Qdrant, Postgres, Neo4j
- LLM: provider-agnostic (OpenAI/Claude) with MOCK_LLM=true for demo

## Quick start
```bash
# backend
cd project/backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
# frontend
cd project/frontend && npm install && npm run dev
# docker
docker compose up --build
```
Set `MOCK_LLM=true` to run without API keys (deterministic demo data).

## API
- `POST /api/policies/upload` — upload privacy policy (PDF/TXT)
- `GET /api/policies` — list
- `POST /api/compliance/analyze {policy_id}` — run LangGraph pipeline
- `GET /api/compliance/{analysis_id}/findings`
- `POST /api/citizen/analyze` — plain-language rights analysis
- `GET /api/evaluation/{analysis_id}/metrics` — extensible metrics
- `GET /api/evaluation/{analysis_id}/guardrails`

## Business Mode
Dashboard with compliance score, severity/urgency distribution, findings as auditable records (status, policy evidence, legal citation, reasoning, recommended action, rewrite). EvidencePanel shows source document/section/clause.

## Citizen Mode
Simplified: plain summary, your rights, company obligations, data collected, purpose, sharing, retention, shortfalls, trust score. No agent jargon.

## Evaluation — extensible
`backend/app/evaluation/registry.py` — implement `BaseMetric` and `@register_metric("my_metric")`. Do not hard-code final research metrics; candidates (Compliance Evidence Alignment, Evidence sufficiency, Risk calibration, etc.) are NOT validated — add via registry when finalized.

Built-ins: Context Precision/Recall, Faithfulness (RAGAS), Citation Accuracy, Unsupported Claim Rate, Expert Checklist Agreement, Hallucination Detection.

## Guardrails — middleware
`backend/app/guardrails/engine.py` — `REGISTRY` of callables. Each returns `GuardrailResult {passed, severity, reason, violated_rule, recommendation}`. Failing high-risk with insufficient evidence → INSUFFICIENT_EVIDENCE instead of fabricating. Extend by appending to REGISTRY.

## Knowledge Base Pipeline
`app/ingestion/chunker.py`: clause-aware chunking → metadata (section/clause/entity/obligation/principle) → triplet (S-P-O) → hybrid KB (vector + graph + metadata) → 3 layers (Facts/Obligations/Principles).

## Project structure
```
project/
  frontend/src/{components,pages,services,types,utils}
  backend/app/{api,agents,ingestion,retrieval,knowledge_base,evaluation,guardrails,models,services,config}
  docker-compose.yml
```

## Testing (TODO: expand)
`pytest` for endpoints, models, retrieval, guardrails; frontend Vitest for components. Include missing-evidence, invalid citation cases.

## Env
See `.env.example` — never commit secrets.

## Research note
Do not claim novel metrics/guardrails until validated against literature. Architecture is designed for paper experiments with reproducible runs (log query, retrieved docs, evidence, decision, confidence, citations, guardrail, latency, token usage, model version).
## Compass engine, evaluation and paper

The audit and legal retrieval run on the engine in `backend/app/compass/`:

| Module | Job |
|---|---|
| `statute.py` | Clause-aware chunker for the Gazette PDF (83 chunks, all 44 sections, the Schedule rebuilt row by row) |
| `layers.py` | Three knowledge layers and the graph: 28 definitions, 74 obligation records, 13 principles, 264 relationships |
| `retrieval.py` | Dense + BM25+ + provision lookup + graph, weighted Reciprocal Rank Fusion, cross-encoder re-ranking |
| `checklist.py`, `audit.py` | 14-obligation checklist, per-obligation policy clauses, guardrails, risk from the Schedule |
| `qa.py` | Grounded answers with citation guardrails (English, Hindi, Marathi) |
| `workflow.py` | The LangGraph state machine; degrades to rules when the model is unavailable |
| `adapter.py` | Maps engine output to the existing API shapes |

API: `POST /api/compliance/analyze` (audit, used by the web app), `POST /api/compass/ask`, `POST /api/compass/audit`, `GET /api/compass/kb`, `GET /ready`.

Experiments live in `backend/eval/` and write to `backend/eval/results/`. Model calls are cached on disk, so every command resumes where it stopped.

```bash
cd backend
python -m eval.retrieval_exp     # knowledge-base counts, chunking, fusion weights, retrieval ablation (no generation)
python -m eval.triplet_check     # automated check of extracted triplets
python -m eval.audit_exp         # DPDP-Synth: rules, single prompt, pipeline with and without guardrails
python -m eval.qa_exp            # DPDP-QA test split: closed-book, dense RAG, hybrid RAG, full system
python ../docs/paper/build_paper.py   # rebuilds docs/paper/DPDP_Compass_Paper_IEEE.docx and .pdf from the results
```

Datasets: `eval/dpdp_qa.py` (198 questions with evidence phrases, validated against the Act) and `eval/synth.py` (40 synthetic policies with labels by construction). Both were drafted with an AI assistant and have not been reviewed by a lawyer.

Production deployment and operations: `docs/OPERATIONS.md`.
