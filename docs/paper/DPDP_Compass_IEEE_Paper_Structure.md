## How to use this document

This is a section-by-section outline for an IEEE conference paper on DPDP Compass. Each section says what goes in it, roughly how long it should be, and which figures or tables belong there. Wording marked as a draft is a starting point only: rewrite it in your own words before submission. Numbers in square brackets such as [X] are placeholders that must come from experiments you actually run.

**Target format:** IEEE conference template (IEEEtran), two columns, 10-pt Times, usually 6–8 pages. A journal version (e.g. IEEE Access) would run 10–14 pages. Sections use Roman numerals (I, II, III), subsections use capital letters (A, B, C), and references use numbered square brackets such as [1].

## Title Options

Aim for 10–15 words, no abbreviations except well-known ones.

1. Evidence-Grounded Retrieval-Augmented Multi-Agent Compliance Analysis under India's DPDP Act, 2023
2. DPDP Compass: A Citation-Enforced Hybrid RAG Framework for Privacy-Policy Auditing and Citizen Rights Guidance
3. Clause-Aware Hybrid Retrieval and Guardrailed LLM Agents for Automated DPDP Compliance Assessment

**Author block:** author names, department, institution, city, country and email, using the fields in the IEEE template.

## Abstract

**Length and rules:** 150–250 words in a single paragraph. No citations, no figures, and no undefined abbreviations.

**What it must cover:** the problem, the gap in existing work, the proposed system, how it was evaluated, the key results, and why they matter.

**Draft (rewrite before submission):**

India's Digital Personal Data Protection (DPDP) Act, 2023 imposes enforceable obligations on organisations that process personal data, yet citizens and small businesses lack accessible tools to interpret it. General-purpose large language models (LLMs) answer legal questions fluently but frequently cite provisions that do not exist. We present DPDP Compass, a retrieval-augmented multi-agent system that grounds every output in clause-level passages of the Act. The system combines dense, sparse (BM25+) and knowledge-graph retrieval with cross-encoder re-ranking, and routes each request through specialised agents for obligation mapping, compliance classification and risk scoring. Seven guardrails reject outputs that contain unsupported claims, fabricated citations or prompt-injection content. We evaluate the system on [N] annotated question–answer pairs and [M] privacy policies from Indian applications. Hybrid retrieval improves Recall@5 by [X] points over dense retrieval alone, the guardrails reduce the fabricated-citation rate from [A]% to [B]%, and obligation-level classification reaches a macro-F1 of [F] against expert annotation. Streaming delivers the first tokens in [T] seconds. These results suggest that citation-enforced retrieval makes LLM-based legal assistance more reliable in low-resource regulatory settings.

**Index Terms (alphabetical):** Compliance checking, data protection, DPDP Act, knowledge graphs, large language models, legal informatics, privacy policies, retrieval-augmented generation.

## I. Introduction

**Length:** about 1 page.

**Context:** The DPDP Act, 2023 and the DPDP Rules, 2025; enforcement phased in through May 2027; penalties of up to ₹250 crore for failing to protect personal data.

**Problem:** Statutory text is difficult for non-lawyers to interpret, manual compliance audits are slow and costly, and general LLMs often invent section numbers when asked legal questions.

**Research gap:** Existing NLP work on privacy policies focuses mainly on the GDPR or US law. There is no clause-grounded system for the DPDP Act, and no support for Indian languages such as Hindi and Marathi.

**Contributions (3–4 bullet points):**

- A clause-aware ingestion and hybrid retrieval pipeline for Indian statutory text.
- A multi-agent workflow that maps a privacy policy to 11 DPDP obligations and produces a deterministic compliance score.
- A seven-check guardrail layer that enforces a "no citation, no claim" rule.
- An annotated evaluation dataset and an ablation study (and an open-source release, if planned).

**Paper organisation:** one sentence describing each of the remaining sections.

## II. Background and Related Work

**Length:** about 1 page.

**A. The DPDP Act and comparable regimes:** Data Principals and Data Fiduciaries; consent (§6); general obligations (§8); children's data (§9); rights of Data Principals (§§11–14). Briefly contrast with the GDPR.

**B. NLP for privacy policies:** OPP-115 corpus (Wilson et al., ACL 2016); Polisis (Harkous et al., USENIX Security 2018); PrivacyQA (Ravichander et al., EMNLP 2019); automated completeness checking of privacy policies against the GDPR (Amaral et al., IEEE TSE 2022).

**C. Retrieval-augmented generation:** RAG (Lewis et al., NeurIPS 2020); Self-RAG (Asai et al., 2023); Corrective RAG (Yan et al., 2024); GraphRAG (Edge et al., 2024).

**D. Legal NLP and hallucination:** LegalBench (Guha et al., NeurIPS 2023); studies of hallucinated citations in legal LLM output.

**E. Retrieval methods:** BM25 (Robertson and Zaragoza, 2009); BM25+ (Lv and Zhai, CIKM 2011); Sentence-BERT (Reimers and Gurevych, EMNLP 2019); Reciprocal Rank Fusion (Cormack et al., SIGIR 2009).

**Closing table:** compare prior work with this system on jurisdiction, grounding, multilingual support, compliance scoring and guardrails.

## III. Problem Formulation

**Length:** about half a page.

**Knowledge base:** K = {k1, …, kn}, where each clause ki carries a section identifier such as §8(6).

**Task 1, citizen question answering:** given a question q, produce an answer a together with a citation set C that is a subset of K.

**Task 2, policy audit:** given a policy P and the obligation set O = {o1, …, o11}, assign each obligation a status from {Satisfied, Partial, Missing, Not applicable}.

**Compliance score:** S = (number Satisfied + 0.5 × number Partial) ÷ number of applicable obligations × 100.

**Grounding constraint:** every claim in the answer a must be supported by at least one citation in C.

## IV. System Architecture and Methodology

**Length:** 2–2.5 pages. This is the core section of the paper.

**A. Overview:** present Fig. 1, the layered architecture (frontend, API, agent workflow, retrieval, knowledge base, language model).

**B. Clause-aware ingestion:** splitting at section and sub-clause boundaries without truncation, and the metadata kept with each chunk. Report the corpus size: 71 legal passages and 69 reference-policy passages from 10 Indian applications.

**C. Hybrid retrieval:** dense retrieval (MiniLM sentence embeddings), sparse retrieval (BM25+, with the reason for choosing it over BM25 Okapi on a small corpus), knowledge-graph retrieval over subject–predicate–object triples, score fusion, and cross-encoder re-ranking. Include the equations.

**D. Multi-agent workflow:** present Fig. 2, the LangGraph state machine: Orchestrator → Retrieval → Obligation Mapping → Compliance → Risk → Guardrails → Generation, including the fast path for citizen questions.

**E. Compliance classification:** the LLM mode, in which policy text is treated as untrusted data, and the rule-based fallback, which uses keyword rules and overlap thresholds (0.5 for Satisfied, 0.25 for Partial). Describe statutory-evidence alignment: each finding quotes the sub-clause of its own obligation.

**F. Guardrails:** Table I lists the seven checks: citation exists, high-risk evidence, hallucinated citation, confidence range, malformed output, prompt injection, and unsupported claim.

**G. Streaming and latency engineering:** evidence and citations sent first, then answer tokens streamed over Server-Sent Events; an LRU answer cache; model fallback and API-key failover.

**H. Multilingual handling:** questions in Hindi and Marathi are searched against the English text of the Act, and the answer is generated in the user's language.

## V. Experimental Setup

**Length:** about 1 page. Include everything a reader needs to reproduce the results.

**Datasets:**

- DPDP-QA: about 200 questions with gold clause labels, written by the authors and checked by a legal annotator.
- Policy audit set: privacy policies of 10 Indian applications, annotated per obligation by two annotators. Report inter-annotator agreement (Cohen's κ).

**Baselines:** the LLM with no retrieval; dense-only RAG; BM25-only RAG; the full system without guardrails.

**Metrics:**

- Retrieval: Recall@k, MRR, nDCG@5.
- Generation: faithfulness and answer relevance (RAGAS, Es et al., 2023), citation precision, fabricated-citation rate.
- Audit: per-class and macro F1, and κ against the human annotators.
- Efficiency: time to first token, p50 and p95 end-to-end latency, cost per query.

**Implementation details:** FastAPI, LangGraph, Groq gpt-oss-120b with a Qwen fallback, temperature 0.1, the hardware used, and the versions of all software libraries.

## VI. Results and Discussion

**Length:** 1.5–2 pages.

| Item | Content |
|---|---|
| Table II | Retrieval ablation: dense, sparse, graph, hybrid, hybrid with re-ranker |
| Table III | Generation quality with and without guardrails, including fabricated-citation rate |
| Table IV | Obligation classification F1 compared with human annotators |
| Fig. 3 | Latency distribution, streaming vs. non-streaming |
| Fig. 4 | Case study: law and policy side by side for one application |

**Discussion points:** why hybrid retrieval helps (exact section numbers favour keyword search, paraphrased questions favour dense search); the most common error types; performance in Hindi compared with English.

## VII. Limitations and Threats to Validity

**Length:** about half a page.

- The corpus is small, and the DPDP Rules, 2025 are only partly ingested.
- Keyword rules can match negated statements such as "we do not share your data".
- The system depends on a single LLM provider, whose free tier has rate limits.
- The annotators are not practising lawyers (state this if it applies), and the policies are a snapshot taken on one date.
- The system gives guidance, not legal advice; discuss the ethics of automated legal assistance.

## VIII. Conclusion and Future Work

**Length:** about a third of a page.

Restate the contributions and headline results in new wording. Do not copy the abstract.

**Future work:** an applicability engine (Significant Data Fiduciary status, cross-border transfers); dual-model agreement checks on high-risk findings; full ingestion of the DPDP Rules; a public benchmark (DPDPA-Bench); user studies with citizens and compliance officers.

## Acknowledgment

Thank your guide, institution and any funding bodies. IEEE spells the heading "Acknowledgment", with no "e" after the "g". Disclose any use of AI tools in preparing the manuscript here.

## References

**Style:** IEEE numbered style, 20–35 entries for a conference paper.

**Format:** [1] A. Author and B. Author, "Title of paper," in Proc. Conference Name, Year, pp. x–y, doi: ….

**Primary source to cite:** The Digital Personal Data Protection Act, 2023 (Act No. 22 of 2023), Gazette of India, August 2023; and the Digital Personal Data Protection Rules, 2025.

Look up every work named in Section II yourself on Google Scholar, IEEE Xplore or the ACL Anthology, and copy the details exactly. Do not cite any work you have not opened.

## Figures and Tables Checklist

| Number | Item | Source in this project |
|---|---|---|
| Fig. 1 | System architecture | Architecture diagram in the project report |
| Fig. 2 | Agent workflow | Workflow page of the report; app/graph/workflow.py |
| Fig. 3 | Latency distribution | To be measured |
| Fig. 4 | Audit case study | Export from the Business workbench |
| Table I | Guardrails | app/guardrails/engine.py |
| Tables II–IV | Results | New experiments |

Refer to every figure and table in the text before it appears. Figure captions go below the figure ("Fig. 1."), and table captions go above the table ("TABLE I").

## Meeting IEEE and Plagiarism Standards

| Rule | What to do |
|---|---|
| Original wording | Rewrite every sentence in your own voice, including the drafts in this document. IEEE journals usually flag an overall similarity above about 15–20%, or above about 5% from any single source, in iThenticate (CrossCheck). |
| Quoting the Act | Put statute text in quotation marks with a citation, and paraphrase long provisions. |
| Self-plagiarism | Do not reuse text from the project README, blueprint or report if any of it has been published before, unless you cite it. |
| Honest results | Every bracketed number must come from an experiment you ran. So far only informal figures exist: 71 passages, 72 passing tests, and first words in about 1–2 seconds. |
| AI disclosure | IEEE requires AI-generated content to be disclosed in the acknowledgments section. AI tools cannot be listed as authors. |
| Pre-submission checks | Run Turnitin or iThenticate (usually available through your university), then validate the PDF with IEEE PDF eXpress. |

## Recommended Order of Work

1. Build the DPDP-QA dataset (about 200 questions) and annotate the 10 policies. This is the main missing piece.
2. Run the retrieval ablation and the comparison with and without guardrails.
3. Measure latency over about 100 queries and report p50 and p95.
4. Write Section IV first (the system is already built), then Sections V and VI, then the Introduction, and the Abstract last.
