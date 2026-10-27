"""Chapter text of the DPDP Compass project report. [[...]] marks a red-circle placeholder for data the team must supply."""
import pathlib

PAPERFIG = pathlib.Path(r"D:\DPDPRag\project\docs\paper\figures")

ONE_PAGE = (
    "India's Digital Personal Data Protection (DPDP) Act, 2023 and the DPDP Rules, 2025 place enforceable duties on every organisation that "
    "processes personal data, yet privacy policies are rarely checked against the law and citizens have no easy way to learn their rights. "
    "This project builds DPDP Compass, a multi-agent Retrieval-Augmented Generation (RAG) system with two modes on one engine. In Business "
    "mode, an organisation uploads or pastes its privacy policy and receives a citation-backed audit against 14 obligations of a Data "
    "Fiduciary, each marked Covered, Partial or Missing with the clause quoted, the section of the Act and the Rule it rests on, the penalty "
    "ceiling, and the exact wording to fix it; the same rule book drafts a new policy that passes its own audit. In Citizen mode, anyone can "
    "ask about their rights in English, Hindi or Marathi, check a well-known app's policy, and write a request to see, correct or erase their "
    "data. A clause-aware knowledge base of the Gazette text, hybrid retrieval (dense, BM25+ and exact provision lookup with re-ranking), "
    "LangGraph agents and output guardrails keep every citation real. The system is built with React, TypeScript, FastAPI, LangGraph, "
    "sentence-transformers, Qdrant and SQLite, uses the gpt-oss-120b model through the Groq API, and is evaluated on 198 questions and 60 policies.")

OBLIGATIONS = [
    ("NOTICE", "Notice of data and purpose", "5(1)", "Rule 3", "₹50 crore"), ("CONSENT", "Free, specific, informed consent", "6(1)", "Rule 3", "₹50 crore"),
    ("LANGUAGE", "Plain language, Eighth Schedule languages", "6(3)", "Rule 3", "₹50 crore"), ("WITHDRAWAL", "Withdrawal of consent", "6(4)", "Rule 3", "₹50 crore"),
    ("PROCESSOR", "Data Processors under contract", "8(2)", "Rule 6(1)(f)", "₹50 crore"), ("ACCURACY", "Accuracy of personal data", "8(3)", "—", "₹50 crore"),
    ("SECURITY", "Reasonable security safeguards", "8(5)", "Rule 6", "₹250 crore"), ("BREACH", "Intimation of personal data breach", "8(6)", "Rule 7", "₹200 crore"),
    ("ERASURE", "Erasure and retention", "8(7)", "Rule 8, Third Sch.", "₹50 crore"), ("CONTACT", "Published privacy contact", "8(9)", "Rule 9", "₹50 crore"),
    ("GRIEVANCE", "Grievance redressal", "8(10)", "Rule 14(3)", "₹50 crore"), ("CHILDREN", "Children's personal data", "9(1)", "Rules 10, 12", "₹200 crore"),
    ("ACCESS", "Access, correction and erasure", "11(1), 12", "Rule 14", "₹50 crore"), ("NOMINATION", "Right to nominate", "14(1)", "Rule 14(4)", "₹50 crore")]


def chapters(a):
    H, P, Bl, F, Tb, Cd, PB, PH = a["heading"], a["para"], a["bullets"], a["figure"], a["table"], a["code"], a["page_break"], a["placeholder_box"]
    S = a["S"]; img = lambda n: S / "img" / f"{n}.png"; dia = lambda n: S / "dia" / f"{n}.png"

    # ═════ 1 Introduction ═════
    H("1 Introduction", 1)
    H("1.1 Present Scenario", 2)
    P("Digital services now collect personal data at every step: a food-delivery app keeps addresses and payment details, an edtech platform "
      "keeps children's records, and a fintech app keeps PAN and bank accounts. India's **Digital Personal Data Protection (DPDP) Act, 2023** "
      "(Act No. 22 of 2023) governs all of this processing. It makes every organisation that decides why and how personal data is processed a "
      "**Data Fiduciary**, gives every individual (the **Data Principal**) enforceable rights, and sets penalties of up to ₹250 crore for a single "
      "breach of duty. The **DPDP Rules, 2025** (G.S.R. 846(E), notified on 13 November 2025, corrected by G.S.R. 892(E)) add the operational "
      "detail, and the commencement notification G.S.R. 843(E) brings the duties of every Data Fiduciary into force on **13 May 2027**.")
    P("For most organisations the privacy policy is the first visible evidence of compliance, and for most citizens it is the only account they "
      "will ever read of what happens to their data. Checking a policy against a statute is slow, expert work. Retrieval-Augmented Generation (RAG) grounds a model's answer in retrieved source text, and a multi-agent design "
      "divides the work the way a compliance team does: one agent finds the law, one decides what it requires, one checks the policy, and one "
      "rates the risk.")
    H("1.2 Need of the Work and Problem Identification", 2)
    P("A review of the literature and of the tools available in India shows that existing work addresses only part of the problem. The problems identified are:")
    Bl(["**No DPDP-specific tooling:** automated privacy-policy analysis targets the GDPR or US practice; we found no system or benchmark built on the text of the DPDP Act.",
        "**Hallucinated law:** LLMs cite non-existent sections and state penalties or deadlines that the Act does not contain, which is unacceptable for compliance work.",
        "**Retrieval that breaks statutes:** fixed-size chunks cut sub-sections apart, and embeddings blur the exact legal terms on which meaning turns.",
        "**Two audiences, two tools:** organisational compliance checkers and citizen rights explainers are built and evaluated separately.",
        "**Opaque scores:** compliance tools rarely show the clause they relied on, the provision behind each verdict, or how to fix a gap.",
        "**Drafting without checking:** policy generators produce text that is never audited against the same rules, so a generated policy can fail its own audit."])
    P("There is therefore a need for one system that reads a policy the way the law is written, cites only provisions that exist, explains every "
      "verdict with evidence, helps an organisation fix and draft its policy, and serves ordinary citizens from the same engine.")
    H("1.2.1 Problem Statement", 3)
    P("**“To enable organisations to assess their privacy policies for compliance with the DPDP Act, 2023, while helping citizens understand their "
      "rights and whether those policies uphold them, through a unified AI-powered multi-agent RAG system that accurately evaluates privacy policies "
      "against DPDP obligations and presents the findings in an accessible manner.”**")
    H("1.3 Objectives and Goals of Project", 2)
    P("The primary objectives of the project are:")
    Bl(["To design and develop a multi-agent RAG compliance engine that retrieves, maps and verifies an organisation's data-handling practices against the obligations of the DPDP Act, 2023 and the DPDP Rules, 2025.",
        "To develop a business module that audits an uploaded privacy policy and returns a citation-backed report with urgency-ranked gaps, suggested compliant rewrites, and a policy generator whose drafts pass the same audit.",
        "To develop a citizen module that answers questions about data-principal rights in plain language (English, Hindi, Marathi), checks public company policies, and drafts rights requests.",
        "To evaluate correctness and reliability against a single-prompt LLM baseline and a keyword baseline on new DPDP benchmarks, with every citation verified."], num=True)
    P("The work is divided into five modules: **Module 1 – Legal Knowledge Base**, **Module 2 – Multi-Agent Engine**, **Module 3 – Business Compliance**, "
      "**Module 4 – Citizen Rights Awareness**, and **Module 5 – Platform and Evaluation**. **Success criteria:** every legal citation shown to a user exists "
      "in the Act or Rules; every Satisfied or Partial verdict quotes the policy verbatim; a policy drafted from complete answers audits at 14 of 14; and "
      "the audit beats the baselines. **Constraints:** the system gives guidance, not legal advice, and runs on free and open-source tools with a hosted LLM API.")
    PB()

    # ═════ 2 Requirement Analysis ═════
    H("2 Requirement Analysis", 1)
    H("2.1 Literature Survey", 2)
    P("Research on multi-agent legal question answering, regulatory knowledge graphs, privacy-policy NLP and legal hallucination was reviewed to "
      "understand what existing work offers and where it stops short. Tab. 1 summarises the survey and the improvement this project makes on each.")
    Tb("Literature survey and proposed improvements", ["No.", "Title", "Author(s) & Year", "Summary", "Limitations", "Proposed Improvement"], [
        ("1", "PAKTON: A Multi-Agent Framework for QA in Long Legal Agreements", "P. Roy et al., 2025", "Coordinated agents answer questions over long contracts more reliably than one LLM pass.", "Question answering only; no compliance checking or risk.", "Per-obligation audit with risk from the Schedule."),
        ("2", "RAGulating Compliance: Multi-Agent Knowledge Graph for Regulatory QA", "B. Agarwal et al., 2025", "Extracts subject-predicate-object triplets from regulations for precise retrieval.", "Regulation side only; little handling of real organisational documents.", "Audits real policies against the Act's triplets."),
        ("3", "LegalGraphRAG: Multi-Agent Graph RAG for Legal Reasoning", "2026", "Organises legal knowledge across facts, rules and principles.", "Needs a curated ontology.", "Builds the three layers automatically from the Gazette text."),
        ("4", "LLM Agents in Law: Taxonomy, Applications, Challenges", "2026", "Survey of LLM legal-agent systems.", "Confirms no validated DPDP system exists.", "First DPDP-specific system and benchmarks."),
        ("5", "Helping Johnny Make Sense of Privacy Policies with LLMs", "2026", "Translates policy findings into plain language for consumers.", "Standalone consumer tool.", "Citizen and business modes share one engine."),
        ("6", "OPP-115 / Polisis / PrivacyQA", "Wilson 2016; Harkous 2018; Ravichander 2019", "Annotated policy corpora, segment classifiers and policy QA.", "GDPR / US practice; no link to a governing provision.", "Every decision cites a DPDP provision."),
        ("7", "Large Legal Fictions; Hallucination-Free?", "Dahl 2024; Magesh 2025", "LLMs and commercial legal tools hallucinate law.", "Diagnosis, not a remedy.", "Citations attached from the KB; guardrails verify quotes.")],
       [0.9, 3.0, 2.2, 3.4, 3.0, 3.0], 9.5)
    P("The survey shows a clear gap: multi-agent legal QA, regulatory knowledge graphs and consumer-facing explanation exist separately, none is built "
      "on India's DPDP Act, and none checks a generated policy against the same rules. This project combines them in one working, evaluated system.")
    H("2.2 Survey, Analysis, and Feasibility Study", 2)
    H("2.2.1 Analysis of Information Gathered", 3)
    P("The Gazette texts of the Act, the Rules, the corrigendum and the commencement notification were studied together with the public privacy "
      "policies of Indian apps (food delivery, payments, e-commerce, health and education). The stakeholders are the **Data Fiduciary** (founders, "
      "compliance officers, legal teams) who need an accurate and explainable gap report, and the **Data Principal** (citizens) who need plain "
      "answers about their rights. The major functions identified are listed in Tab. 2.")
    Tb("Major functions identified", ["Module", "Major functions", "Main technologies"], [
        ("1. Legal Knowledge Base", "Gazette PDF parsing, clause-aware chunking, three-layer structure, triplets and graph, Rules 2025 with corrigendum, rule book", "Python, PyMuPDF, pypdf, regex NLP, JSON"),
        ("2. Multi-Agent Engine", "Orchestrator, hybrid retrieval with RRF and re-ranking, obligation mapping, compliance checking, guardrails, risk", "LangGraph, sentence-transformers, BM25+, Qdrant, Groq LLM"),
        ("3. Business Compliance", "Upload/paste, audit report, evidence viewer, redline and re-audit, review trail, version compare, policy generator", "FastAPI, React, TypeScript, SQLite"),
        ("4. Citizen Rights", "Grounded Q&A in EN/HI/MR, claim support check, app policy check, trust indicator, rights request letters", "FastAPI SSE, langdetect, React"),
        ("5. Platform & Evaluation", "Accounts, sessions, versioned documents, exports, security hardening, evaluation sets and metrics", "scrypt, SQLite, python-docx, pytest")],
       [3.2, 7.8, 4.5])
    P("Major issues identified were: keeping provision structure intact while chunking a Gazette PDF; stopping the LLM from inventing sections; "
      "making the audit agree with a lawyer's reading of real, hedged clauses; making a generated policy pass its own audit; protecting uploaded "
      "policies as private data; and keeping the interface simple enough for older, non-technical users.")
    H("2.2.2 Feasibility Study", 3)
    Bl(["**Technical feasibility:** every component (FastAPI, LangGraph, sentence-transformers, Qdrant in embedded mode, SQLite, React) is mature and runs on an ordinary laptop; the LLM is reached through an OpenAI-compatible API with a cache and failover.",
        "**Economic feasibility:** all software is free or open source; LLM usage is the only running cost, estimated at ₹3,000–5,000 in the synopsis. Actual spend: [[actual LLM API cost incurred]].",
        "**Operational feasibility:** users need only a web browser; the interface uses large text, plain labels and help on every field.",
        "**Legal feasibility:** the Act and Rules are public Gazette documents; the system processes only the policies users choose to upload and stores them privately per account.",
        "**Schedule feasibility:** development splits into four increments from July to October; November is reserved for the external examiner's review, paper publication and report submission."])
    H("2.2.3 Estimate of Effort", 3)
    P("Development took four months (July to October 2026) for a team of five students, about 20 person-months of effort; November was kept for the project review by the external examiner, publication of the research paper, and submission of the final report. The month-wise plan is given in Tab. 3 and Fig. 2.")
    H("2.3 Appropriate Life Cycle Model", 2)
    P("The **Incremental model** was chosen [1], [2]. The system splits into modules that build on each other: the knowledge base must exist before "
      "retrieval, retrieval before auditing, and auditing before the generator can be checked. Each increment was analysed, designed, coded and tested "
      "as a working build, and evaluation results from one increment (for example, the finding that the knowledge graph lowered ranking) changed the next.")
    F(dia("d15_incremental"), "Incremental life-cycle model followed by the project", 15.5)
    Tb("Project plan and increments", ["Sr. No.", "Month", "Increment", "Plan"], [
        ("1", "July", "Increment 1", "Literature survey, collection of the Gazette PDFs and Indian privacy policies, requirement analysis, statute parser, clause-aware chunker and three-layer knowledge base."),
        ("2", "August", "Increment 2", "Hybrid retrieval, obligation-mapping agent, triplets and graph; DPDP-QA question set; first retrieval checkpoint."),
        ("3", "September", "Increment 3", "Compliance-checking agent, guardrails and risk agent; Business and Citizen interfaces; accounts, versioned documents, redlines and review trail; DPDP Rules 2025."),
        ("4", "October", "Increment 4", "Rule book and policy generator; full evaluation (retrieval, chunking, audit, QA ablations); accessible UI refinement; testing and integration. Development complete."),
        ("5", "November", "Review", "Project review by the external examiner, research paper submission and publication, final report submission and project demonstration.")],
       [1.4, 2.0, 2.4, 10.0])
    F(dia("d14_gantt"), "Project schedule (Gantt chart)", 15.5)
    PB()

    # ═════ 3 SRS ═════
    H("3 Software Requirements Specification (SRS)", 1)
    H("3.1 Introduction", 2)
    P("**Purpose:** this chapter specifies the requirements of DPDP Compass following the usual structure of an SRS. **Scope:** a web application "
      "that audits privacy policies against the DPDP Act, 2023 and Rules, 2025, drafts compliant policies, and answers citizens' questions with "
      "verified citations. **Definitions:** *Data Fiduciary* – person who determines the purpose and means of processing (Section 2(i)); *Data "
      "Principal* – the individual to whom the data relates (Section 2(j)); *Data Processor* – processes data on behalf of a Fiduciary (Section 2(k)); "
      "*RAG* – Retrieval-Augmented Generation; *RRF* – Reciprocal Rank Fusion; *BM25+* – lower-bounded BM25 sparse ranking; *SDF* – Significant "
      "Data Fiduciary; *DPO* – Data Protection Officer; *SSE* – Server-Sent Events.")
    H("3.2 Overall Description", 2)
    P("The product is a three-tier web application: a React 18 single-page application in TypeScript, a FastAPI backend that exposes REST and SSE "
      "endpoints and runs the LangGraph engine, and SQLite databases with an embedded vector index. There are three user classes. The **Business "
      "user** uploads, audits, reviews, redlines, generates and exports policies. The **Citizen** asks questions, checks app policies and writes "
      "rights requests. The **Reviewer** (a compliance officer using a business account) accepts or overrides automated findings. The system runs "
      "in a modern browser; the backend runs on Windows 10/11 or Linux, directly or with Docker Compose. It is assumed that a valid LLM API key is "
      "configured; without it the system falls back to keyword rules and says so.")
    H("3.3 Functional Requirements", 2)
    Tb("Functional requirements", ["ID", "Requirement", "Module"], [
        ("FR-1", "The system shall parse the Gazette PDF of the Act into clause chunks that keep section, sub-section, title and page.", "Module 1"),
        ("FR-2", "The system shall load the DPDP Rules, 2025, apply the corrigendum G.S.R. 892(E), and know each provision's commencement date.", "Module 1"),
        ("FR-3", "The system shall retrieve legal evidence with dense, BM25+ and exact provision lookup, fused by weighted RRF and re-ranked.", "Module 2"),
        ("FR-4", "For each of the 14 obligations the system shall judge the policy from its own retrieved clauses and return Satisfied, Partial, Missing or Not applicable.", "Module 2"),
        ("FR-5", "Every Satisfied or Partial finding shall quote the policy verbatim; a quote not found in the policy shall downgrade the finding.", "Module 2"),
        ("FR-6", "Legal citations shall be attached from the knowledge base, never generated; a citation that does not exist shall be removed.", "Module 2"),
        ("FR-7", "The system shall compute S = 100 (n_sat + 0.5 n_part) / n_applicable and rate risk from the Schedule's penalty ceilings.", "Module 2"),
        ("FR-8", "A user shall upload (PDF, DOCX, TXT, MD) or paste a policy; each text shall be saved as a version with its SHA-256 hash.", "Module 3"),
        ("FR-9", "Each finding shall show the policy clause, the Act text, the Rules, the rule-book checklist, fixes and suggested wording.", "Module 3"),
        ("FR-10", "A reviewer shall accept or override a finding; decisions shall be kept in an append-only trail.", "Module 3"),
        ("FR-11", "A user shall apply a redline, which creates a new version, re-audits it and compares versions.", "Module 3"),
        ("FR-12", "The generator shall ask follow-up questions for vague answers and draft a policy that passes every rule-book requirement.", "Module 3"),
        ("FR-13", "Unfilled placeholders shall be marked in red and shall prevent an obligation from being reported as fully Satisfied.", "Module 3"),
        ("FR-14", "A citizen shall ask questions in English, Hindi or Marathi and receive an answer citing only retrieved provisions.", "Module 4"),
        ("FR-15", "A citizen shall check a reference company's policy and see which rights it respects, with a trust indicator.", "Module 4"),
        ("FR-16", "A citizen shall generate an access, correction, erasure or grievance request letter addressed to the policy's contact.", "Module 4"),
        ("FR-17", "Users shall sign up, sign in, change password and delete the account, which deletes their documents and audits.", "Module 5"),
        ("FR-18", "Reports and answers shall export as PDF, Word (DOCX) or Markdown.", "Module 5")],
       [1.6, 11.6, 2.2])
    H("3.4 Non-Functional Requirements", 2)
    Bl(["**Faithfulness:** no fabricated citations; unsupported legal statements kept below 10% (measured 7.9%).",
        "**Privacy by design (DPDP applied to ourselves):** uploaded policies are private to the owner, never added to the shared index; account deletion erases them; only data needed for the service is stored.",
        "**Security:** scrypt password hashing, HttpOnly SameSite=Lax session cookies with server-side hashed tokens, login throttling, CSRF origin checks, rate limiting, upload type and size checks, SSRF protection, secrets held as SecretStr, prompt-injection flagging.",
        "**Accessibility and usability:** Atkinson Hyperlegible font at 18 px, high contrast, large buttons with plain words, a help (i) on every input, keyboard focus outlines, minimal motion.",
        "**Performance:** retrieval about 12 ms without re-ranking and about 1.3 s with the CPU cross-encoder; a full audit in about 9–30 s depending on the model.",
        "**Reliability:** LLM failover to backup keys and a fallback model; degraded mode (keyword rules) is labelled in every response.",
        "**Maintainability and extensibility:** the rule book is a JSON file (45 requirements) that can be edited without code; 116 automated tests."])
    H("3.5 External Interface and System Requirements", 2)
    P("**User interface:** responsive web pages built with React, Tailwind CSS and Radix UI. **Software interfaces:** REST/JSON and SSE between "
      "frontend and backend; an OpenAI-compatible HTTPS API to Groq; optional Qdrant, Neo4j and PostgreSQL servers. Hardware and software requirements are listed in Tab. 6 and Tab. 7.")
    Tb("Hardware requirements", ["Item", "Specification"], [
        ("Computer", "Laptop/desktop, Intel i5 or equivalent"), ("Memory", "Minimum 8 GB RAM (16 GB recommended for running evaluation and server together)"),
        ("Storage", "256 GB SSD; about 2 GB for models and indexes"), ("Network", "Stable internet connection for the LLM API")], [4, 11.5])
    Tb("Software requirements", ["Item", "Specification"], [
        ("Operating system", "Windows 10/11 (development); Linux with Docker for deployment"), ("Runtimes", "Python 3.13, Node.js 20+ with npm"),
        ("Editor and tools", "Visual Studio Code, Git and GitHub, Postman / Swagger UI"), ("Containers", "Docker and Docker Compose"),
        ("Browser", "Google Chrome / Microsoft Edge"), ("LLM access", "Groq API key (gpt-oss-120b) or another OpenAI-compatible endpoint")], [4, 11.5])
    H("3.6 Constraints, Assumptions and Data Requirements", 2)
    P("The system gives guidance, not legal advice. Evaluation is run on the Act alone (21 Gazette pages); the live application also indexes the "
      "Rules, 2025. The data handled are: the official Gazette PDFs; reference policies of 10 Indian apps; user accounts (name, e-mail, password "
      "hash); uploaded policy versions; analyses and review events; and per-user interface state. Questions are redacted for personal data before "
      "logging. Development cost excluding the laptop and internet is limited to LLM usage.")
    H("3.7 DPDP Obligations Covered", 2)
    P("Tab. 8 lists the 14 obligations of a Data Fiduciary that every audit checks, with the provision, the Rule that gives it detail, and the "
      "maximum penalty in the Schedule, which the risk agent uses for severity. All of them commence on 13 May 2027.")
    Tb("The 14 DPDP obligations checked by the audit", ["No.", "Obligation", "Act section", "Rules, 2025", "Penalty ceiling"],
       [(str(i), t, s, r, pen) for i, (_, t, s, r, pen) in enumerate(OBLIGATIONS, 1)], [1.1, 6.5, 2.4, 3.0, 2.6])
    PB()

    # ═════ 4 Design ═════
    H("4 Design", 1)
    H("4.1 System Architecture Diagram", 2)
    P("Fig. 3 shows the architecture. **Data sources** are the official Gazette PDFs of the Act and the Rules (with corrigendum and commencement "
      "notification), reference policies of Indian apps, the organisation's own policy and citizens' questions. The **offline pipeline** parses the "
      "statute, chunks it clause by clause, builds three layers (facts, obligations, principles), extracts deontic triplets and builds the indexes. "
      "The **hybrid knowledge base** holds the dense index, the BM25+ index, the provision metadata store, the knowledge graph and the rule book. The "
      "**multi-agent engine**, a LangGraph state machine, routes each request through the orchestrator, retrieval, obligation-mapping, "
      "compliance-checking, guardrail and risk agents, calling the LLM only for judgement. **Outputs** reach the business workbench, the policy "
      "generator, the citizen desk and the exporters, while SQLite keeps accounts, versioned documents and analyses, and the evaluation layer measures every component.")
    F(dia("d01_architecture"), "System architecture of DPDP Compass", 15.8)
    H("4.2 Modular Structure", 2)
    P("The system is divided into five modules (Fig. 4). **Module 1 (Legal Knowledge Base)** turns the Gazette texts into clause chunks, "
      "obligation records, principles, a graph and a rule book. **Module 2 (Multi-Agent Engine)** retrieves evidence and judges each obligation. "
      "**Module 3 (Business Compliance)** presents audits, evidence, redlines, reviews and the policy generator. **Module 4 (Citizen Rights)** "
      "answers questions, checks app policies and writes rights requests. **Module 5 (Platform and Evaluation)** provides accounts, documents, "
      "exports, security hardening and the evaluation sets. Modules 3 and 4 both depend on Module 2, which depends on Module 1.")
    F(dia("d02_modules"), "Modular structure of the system", 15.8)
    H("4.3 Important Design Diagrams and Specifications", 2)
    H("4.3.1 Data Flow Diagrams (DFDs)", 3)
    P("The level-0 DFD (Fig. 5) shows the system as one process with four external entities: the business user, the citizen, the Government "
      "Gazette and the LLM service. The level-1 DFD (Fig. 6) splits it into seven processes and five data stores. The level-2 DFD (Fig. 7) expands "
      "process 3.0, the policy audit.")
    F(dia("d03_dfd0"), "Data Flow Diagram - Level 0 (Context Diagram)", 15.5)
    F(dia("d04_dfd1"), "Data Flow Diagram - Level 1", 15.8)
    F(dia("d05_dfd2"), "Data Flow Diagram - Level 2 (Policy Audit, process 3.0)", 15.8)
    H("4.3.2 Database Design", 3)
    P("Persistent data is kept in three SQLite files so that each concern can be backed up and deleted independently (Fig. 8, Tab. 9). Every "
      "document, analysis and state row carries its owner, and every query is scoped to the signed-in user. Policy versions are immutable and "
      "identified by SHA-256, so an audit always names exactly the text it read. Reviewer decisions are appended, never overwritten.")
    F(dia("d06_er"), "Database schema / Entity-Relationship diagram", 15.8)
    Tb("Database tables", ["Table", "Purpose", "Key fields"], [
        ("users", "Registered accounts", "id, email (unique), name, pw_hash, pw_salt"), ("sessions", "Signed-in sessions (token stored hashed)", "token_hash, user_id, expires_at"),
        ("user_state", "Per-user saved interface state", "user_id, key, value"), ("login_failures", "Throttling of repeated failed logins", "email, at"),
        ("documents", "One row per policy (owner-scoped)", "id, owner, name, company, source"), ("versions", "Each text of a policy with its hash", "doc_id, n, text, sha256"),
        ("analyses", "Saved audit reports", "id, owner, body (JSON)"), ("review_events", "Append-only reviewer decisions", "analysis_id, finding_id, decision, status, user"),
        ("kb_metadata", "Clause metadata (PostgreSQL when available)", "chunk_id, section, subsection, citation, page")], [3.2, 6.0, 6.3])
    H("4.3.3 Class Diagram", 3)
    P("Fig. 9 shows the main classes and modules. **Engine** owns the parsed **Statute**, the **KnowledgeBase** (layers and graph) and the hybrid "
      "**Index**. The LangGraph **State** carries a request through the agents; the compliance node calls **LLM**, and the guardrail node calls the "
      "**rulebook** module. **DocumentStore** persists versioned policies, and the **checklist** module defines the 14 obligations and the score.")
    F(dia("d07_class"), "Class diagram", 15.8)
    H("4.3.4 Sequence and Collaboration Diagrams", 3)
    P("Fig. 10 shows the sequence of a policy audit from the user's click to the rendered report; Fig. 11 shows the same interaction as a "
      "collaboration diagram with numbered messages.")
    F(dia("d08_sequence"), "Sequence diagram - Policy audit", 15.8)
    F(dia("d09_collaboration"), "Collaboration diagram - Policy audit", 15.5)
    H("4.3.5 Use Case Diagram", 3)
    P("Fig. 12 shows the actors and their use cases. Business users upload, audit, review, redline, compare, generate and export; citizens ask, "
      "check app policies and write requests; the reviewer accepts or overrides findings; the LLM service participates as a secondary actor.")
    F(dia("d10_usecase"), "Use case diagram", 15.5)
    H("4.3.6 Knowledge Base, Hybrid Retrieval and Agent Workflow", 3)
    P("Fig. 13 traces one provision, Section 8(5), across the three layers: the clause text (facts), the obligation extracted from it, the "
      "principle it serves, and the penalty linked to it in the graph. Fig. 14 shows hybrid retrieval: four retrievers fused by weighted RRF "
      "(dense = sparse = 1, metadata = 2, graph = 0 after tuning) and re-ranked by a cross-encoder. Fig. 15 shows the LangGraph agent workflow.")
    F(PAPERFIG / "fig2_layers.png", "Three-layer knowledge structure for Section 8(5)", 15.0)
    F(PAPERFIG / "fig3_retrieval.png", "Hybrid retrieval with weighted Reciprocal Rank Fusion", 15.0)
    F(PAPERFIG / "fig4_workflow.png", "Multi-agent workflow (LangGraph state machine)", 13.0)
    H("4.3.7 Rule Book and Policy Generation", 3)
    P("The rule book (rulebook.json) lists 45 requirements across the 14 obligations, each with its legal basis and a fix. The same rules draft "
      "the generated policy and check every audited policy. Fig. 16 shows the generation activity and Fig. 17 shows how the rule book reconciles "
      "with the LLM judge: hard flaws (unfilled placeholders, forbidden wording such as “by using this app you agree”) cap a finding at Partial, "
      "and an obligation whose requirements are all met in one section is Satisfied with the matching sentence quoted.")
    F(dia("d11_activity_generation"), "Activity diagram - Policy generation from the rule book", 12.5)
    F(dia("d12_rulebook_reconcile"), "Rule-book reconciliation of each audit finding", 15.5)
    H("4.3.8 Deployment Diagram", 3)
    P("Fig. 18 shows deployment. The browser runs the React application; the application host runs Uvicorn with the FastAPI app, the LangGraph "
      "engine, the embedding and re-ranking models, the embedded vector index, the rule book and the SQLite databases; the LLM is called over "
      "HTTPS. The same code runs against Qdrant, Neo4j and PostgreSQL servers through Docker Compose (docker-compose.yml, docker-compose.prod.yml).")
    F(dia("d13_deployment"), "Deployment diagram", 15.8)
    PB()

    # ═════ 5 Implementation ═════
    H("5 Implementation and Coding", 1)
    H("5.1 Technology, Language, and Tools Used", 2)
    P("The backend is written in **Python 3.13** with **FastAPI** and **LangGraph**; the frontend in **TypeScript** with **React 18** and **Vite**. "
      "The tech stack differs from the synopsis where measurement or simplicity called for it: SQLite and an embedded Qdrant index replace "
      "always-on PostgreSQL and Qdrant servers (both remain supported), the LLM is **gpt-oss-120b served by Groq** (OpenAI-compatible) instead of "
      "Claude/GPT, and evaluation uses our own DPDP benchmarks with judge-based and citation metrics in the spirit of RAGAS. Tab. 10 summarises the stack.")
    Tb("Technology stack summary", ["Layer or category", "Technology", "Purpose / description"], [
        ("Frontend", "React 18, TypeScript 5, Vite 7, Tailwind CSS 3, Radix UI, React Router 7, lucide-react, sonner, motion", "Accessible single-page app: audit, generator, citizen desk, dashboard"),
        ("Backend", "Python 3.13, FastAPI, Uvicorn, Pydantic v2, pydantic-settings", "REST + SSE API, validation, configuration"),
        ("Agents", "LangGraph state machine", "Orchestrator, retrieval, mapping, compliance, guardrails, risk"),
        ("Retrieval", "sentence-transformers all-MiniLM-L6-v2, rank-bm25 (BM25+), cross-encoder ms-marco-MiniLM-L-6-v2, Qdrant", "Dense, sparse, metadata lookup, re-ranking"),
        ("LLM", "gpt-oss-120b via Groq (httpx / OpenAI-compatible), fallback model and keys, response cache", "Per-obligation judgement, answers, polishing"),
        ("Documents", "PyMuPDF, pypdf, python-docx, BeautifulSoup, Markdown", "Parsing Gazette PDFs and uploads; PDF/DOCX/MD export"),
        ("Data", "SQLite (accounts, documents, analyses); optional PostgreSQL, Neo4j", "Owner-scoped persistence, versioning"),
        ("Security", "scrypt, HttpOnly cookies, CSRF origin check, rate limits, SSRF guard", "Accounts and API hardening"),
        ("Quality", "pytest (116 tests), ESLint + jsx-a11y, TypeScript type-check, Playwright", "Automated and UI testing"),
        ("Tools", "VS Code, Git/GitHub, Docker Compose, Swagger UI", "Development, versioning, deployment, API testing")],
       [3.0, 6.7, 5.8], 10)
    H("5.2 Important Constructs, Classes, Algorithms, and Pseudo-codes", 2)
    P("The important constructs are the **Engine** (statute, knowledge base, index), the LangGraph **State** and its nodes, the **rulebook** module, "
      "and the **DocumentStore** (Fig. 9). Retrieval runs four retrievers and one fusion step per query; the audit makes four batched LLM calls per "
      "policy (14 obligations, 7 per batch) plus linear-time guardrail and rule checks. The main algorithms follow.")
    Cd("Algorithm 1: Clause-aware chunking of the statute", """Input : text of the Gazette PDF of the DPDP Act
Output: chunks with section, sub-sections, title, chapter and page
1. remove page headers and masthead noise; separate marginal notes
2. detect sections by running number (accept only the next number) and
   attach each marginal note as the section title
3. split each section into numbered sub-sections, again in running order
4. pack consecutive sub-sections into chunks of <= 1,200 characters;
   split an over-long sub-section at its lettered clauses
5. prefix every chunk with "Section n. Title" and store its metadata
6. rebuild the penalty Schedule as one row per breach
Result on the Act: 82 chunks covering all 44 sections (mean 765 chars)""")
    Cd("Algorithm 2: Hybrid retrieval with weighted Reciprocal Rank Fusion", """Input : query q, weights w = {dense: 1, sparse: 1, metadata: 2, graph: 0}
Output: top-k evidence chunks
1. R_dense  <- cosine top-20 of MiniLM(q) in the vector index
2. R_sparse <- BM25+ top-20 over stemmed tokens
3. R_meta   <- all chunks of any provision named in q (e.g. "8(6)")
4. for each chunk d: score(d) = sum_r  w_r / (60 + rank_r(d))
5. candidates <- top-20 by score; re-rank with the cross-encoder
6. return top-k with provenance (retrievers, ranks, provision, page)""")
    Cd("Algorithm 3: Per-obligation audit with guardrails", """Input : policy P, checklist O (14 obligations)
Output: findings with status, quote, citation, risk; score S
1. chunk P into paragraphs; build an in-memory hybrid index over P
2. for each obligation o: clauses[o] <- top-3 policy chunks for o.query
3. mapping[o] <- statute text by exact lookup, principle, exemptions, penalty
4. in batches of 7: verdicts <- LLM(o.tests, mapping[o], clauses[o])
5. for each verdict v:
     if v.status != Missing and quote(v) not verbatim in P:
         Satisfied -> Partial (confidence <= 0.5); Partial without quote -> Missing
     if citation not in the Act: remove it
     flag clauses that contain instruction-like text (prompt injection)
6. rulebook.reconcile(findings, P)                      (Algorithm 4)
7. risk <- f(Schedule penalty ceiling, status); applicability; in-force date
8. S = 100 * (n_sat + 0.5 * n_part) / n_applicable""")
    Cd("Algorithm 4: Rule-book check and reconciliation", """Input : policy text P, findings F, RULES (45 requirements), HARD (no-flaw rules)
1. sections <- markdown sections of P (or 3-paragraph windows)
2. for each obligation o:
     best <- section maximising (content rules met, hard rules met, -length)
     checks <- [ test(best, P) for every requirement of o + "no placeholder" ]
3. for each finding f of obligation o:
     attach checks, failed fixes and model wording
     if any hard check fails:  if f = Satisfied then f <- Partial
     elif all checks pass:     f <- Satisfied, quote = matching sentence""")
    Cd("Algorithm 5: Policy generation that passes its own audit", """Input : intake answers A (17 fields)
1. Q <- intake.review(A)          # vague or missing answers -> questions
2. if Q is not empty and the user does not choose "draft anyway": return Q
3. facts <- A, with [placeholders] for every field still in question
4. draft <- rulebook.draft(facts)  # one section per obligation
5. if an LLM is available:
       r <- LLM.polish(draft)
       if check(r) meets all 14 obligations and the keyword judge agrees: draft <- r
6. save draft as a versioned document; return draft, rule results, placeholders""")
    P("Two short excerpts from the implementation show how the score and the rule book are coded:")
    Cd("Code 1: compliance score (backend/app/compass/checklist.py)", """def score(statuses: list[str]) -> float:
    \"\"\"S = 100 (n_sat + 0.5 n_part) / n_applicable.\"\"\"
    applicable = [code(s) for s in statuses if code(s) != "NOT_APPLICABLE"]
    return round(100 * sum(WEIGHTS.get(s, 0.0) for s in applicable)
                 / len(applicable), 1) if applicable else 0.0""")
    Cd("Code 2: one rule-book requirement (backend/app/compass/rulebook.json)", """"GRIEVANCE": [
  { "rule":  "Promises a response within 90 days",
    "basis": "Rule 14(3)",
    "check": "max_90_days",
    "fix":   "State a response time of at most 90 days, e.g. 'We will respond within 30 days.'" },
  ...""")
    Cd("Code 3: the agent graph (backend/app/compass/workflow.py)", """g = StateGraph(State)
for name, fn in (("orchestrator", orchestrator), ("answer", answer), ("retrieval", retrieval),
                 ("obligation_mapping", obligation_mapping), ("compliance", compliance),
                 ("guardrails", guardrails), ("risk", risk)):
    g.add_node(name, fn)
g.set_entry_point("orchestrator")
g.add_conditional_edges("orchestrator", lambda s: s["intent"],
                        {"question": "answer", "audit": "retrieval"})""")
    H("5.3 Application Screenshots with Labels and Descriptions", 2)
    shots = [("s01_landing", "Landing page", "The public page explains the product in one sentence and offers two large actions: check a privacy policy, or ask about your rights."),
             ("s02_signin", "Sign-in screen", "Accounts keep each user's policies, audits and questions private; passwords are hashed with scrypt and sessions use HttpOnly cookies."),
             ("s03_dashboard", "Home dashboard", "After signing in, three large actions, the number of days until the duties commence (13 May 2027), recent checks and saved policies."),
             ("s04_audit_input", "Policy audit input", "A policy is uploaded or pasted; the user can also answer applicability questions, choose the assessment date, or try a bundled Indian app policy."),
             ("s05_audit_result", "Audit result: score and findings", "The compliance score out of 100, counts of Covered, Partial and Missing obligations, and the 14 findings sorted with gaps first."),
             ("s06_audit_finding", "A finding with its evidence", "Each finding states the reasoning and penalty ceiling, opens the evidence in the document, and lets a reviewer accept or override it."),
             ("s07_create_form", "Policy generator intake", "The generator asks detailed questions with plain labels; required fields are starred."),
             ("s08_info_tooltip", "Help on every field", "An (i) next to each field explains what to enter, with an example and the provision that requires it."),
             ("s09_followup_questions", "Follow-up questions", "Vague or missing answers come back as specific questions with why each matters and an example answer."),
             ("s10_placeholders", "Placeholders marked in red", "When the user drafts anyway, each missing fact is marked with a red circle so it cannot be overlooked."),
             ("s11_generated_policy", "Generated policy", "A draft from complete answers passes 14 of 14 rule-book checks, cites the sections it implements, and can be audited in one click."),
             ("s12_generated_audit_100", "Audit of the generated policy", "Auditing the generated draft gives 100 out of 100 with all 14 obligations Covered."),
             ("s13_citizen", "Citizen desk", "Citizens choose between asking a question, checking an app's policy, and writing a rights request."),
             ("s14_citizen_answer", "Citizen answer with sources", "Answers quote the Act and the Rules, list their sources, and show a claim check that marks supported and unsupported sentences."),
             ("s16_about", "How it works", "Explains the sources, the method and the guardrails in plain language."),
             ("s17_account", "Account page", "Users change their password or delete the account, which erases their documents and audits (the right to erasure applied to our own system)."),
             ("s18_mobile", "Mobile view", "On a phone the layout stacks into one column with a large Menu button.")]
    for n, t, d in shots:
        F(img(n), t, 15.5 if n != "s18_mobile" else 6.5)
        P(d)
    PB()

    # ═════ 6 Testing ═════
    H("6 Testing", 1)
    H("6.1 Various Testing Mechanisms Used", 2)
    P("The backend is a mix of classes (Engine, Index, DocumentStore) and functional modules (agents, rule book, API routes), so both "
      "object-oriented and functional testing apply. The following mechanisms were used:")
    Bl(["**Unit testing (pytest):** the chunker, layers, cross-references, retrieval, score formula, guardrails, rule book, intake review and claim checks are tested in isolation.",
        "**Functional / API testing:** every REST endpoint is exercised through FastAPI's TestClient and Swagger UI (Fig. 36).",
        "**Integration testing:** the LangGraph workflow is run end to end for citizen questions and business audits, including the degraded path when the LLM is unavailable.",
        "**Security testing:** sign-in, throttling, session expiry, CSRF origin checks, rate limits, SSRF, upload types and prompt-injection are tested.",
        "**Self-check of the rule book:** python -m app.compass.rulebook verifies that the generated draft and every suggested clause pass their own rules.",
        "**End-to-end UI testing:** Playwright drives the real interface (sign-in, audit, generation, citizen answer) and captures the screenshots in Chapter 5.",
        "**Evaluation:** retrieval, chunking, audit and question-answering ablations on the DPDP-QA, DPDP-Synth and DPDP-Real sets (Section 6.3)."])
    H("6.2 Various Testing Methods and Test Cases", 2)
    P("Black-box test cases were derived from the functional requirements in Chapter 3; white-box tests cover both the valid and invalid paths of "
      "the guardrails, rule book and authentication code. Each case below is an automated test in backend/tests; the result column is the "
      "outcome of the final run.")
    tc = [("Module 1 (Legal Knowledge Base)", [
        ("TC_101", "Chunker covers every section", "DPDP Act Gazette PDF", "All 44 sections chunked with provision metadata"),
        ("TC_102", "Chunking baselines use the same text", "Same cleaned text", "Fixed-window and clause chunkers compared fairly"),
        ("TC_103", "Three knowledge layers built", "Parsed statute", "Facts, obligations and principles present"),
        ("TC_104", "Cross-references skip other Acts", "Sections citing other laws", "No REFERS_TO edge to another Act"),
        ("TC_105", "Rules parsed with corrigendum", "Rules PDF + G.S.R. 892(E)", "23 rules, 7 schedules; corrections applied"),
        ("TC_106", "Commencement dates", "Provision ids", "Correct in-force dates (13 May 2027 etc.)")]),
        ("Module 2 (Multi-Agent Engine)", [
        ("TC_201", "Retrieval finds the gold provision", "DPDP-QA questions", "Gold clause in top results"),
        ("TC_202", "Exact provision lookup", "Query naming 'Section 8(6)'", "Chunks of 8(6) fetched"),
        ("TC_203", "Guardrails correct unverifiable findings", "Quote not in policy", "Satisfied downgraded; quote removed"),
        ("TC_204", "Hallucinated citation removed", "Non-existent section", "Citation dropped"),
        ("TC_205", "Prompt injection ignored", "Policy with 'ignore previous instructions'", "Finding unchanged; chunk flagged"),
        ("TC_206", "Workflow degrades without model", "LLM unavailable", "Keyword rules used; marked degraded"),
        ("TC_207", "Score formula", "Statuses incl. Not applicable", "S excludes Not applicable")]),
        ("Module 3 (Business Compliance)", [
        ("TC_301", "Documents private and versioned", "Two users upload", "Each sees only own versions with sha256"),
        ("TC_302", "Redline accept re-audits and compares", "Accept suggested clause", "New version, new audit, diff shown"),
        ("TC_303", "Review trail override and conflict", "Override with stale revision", "Override saved; stale update gets 409"),
        ("TC_304", "Generator asks before drafting", "Vague answers", "Questions returned; draft only on request"),
        ("TC_305", "Complete generated policy passes audit", "17 complete answers", "14 of 14 rules met; audit 14 Satisfied"),
        ("TC_306", "Draft with placeholders never 100", "3 fields left blank", "CONTACT, GRIEVANCE, SECURITY flagged; score < 100"),
        ("TC_307", "Export formats", "Report markdown", "Valid PDF, real DOCX, titled Markdown")]),
        ("Module 4 (Citizen Rights)", [
        ("TC_401", "Citizen workflow end to end", "Question in English", "Answer with verified citations"),
        ("TC_402", "Answer carries a claim check", "Answer with a number", "Unsupported number flagged"),
        ("TC_403", "App policy check", "Reference company", "Practices from policy text; trust score"),
        ("TC_404", "General question has no trust score", "Question without a policy", "No trust indicator shown"),
        ("TC_405", "Rights request letter", "Policy with contact", "Letter addressed to the policy's contact"),
        ("TC_406", "Repeated question cached", "Same question twice", "Second answer served from cache")]),
        ("Module 5 (Platform, Security) and integration", [
        ("TC_501", "Sign-up sets HttpOnly cookie", "New account", "Signed in; cookie HttpOnly"),
        ("TC_502", "Same answer for wrong password / unknown e-mail", "Bad credentials", "Identical error (no account enumeration)"),
        ("TC_503", "Repeated failures throttled", "Many failed logins", "Further attempts blocked"),
        ("TC_504", "Deleting the account removes its data", "Account with policies", "Documents, audits and state erased"),
        ("TC_505", "Cross-site requests refused", "Foreign Origin with session", "403 refused"),
        ("TC_506", "SSRF and upload checks", "Private URL; .exe upload", "Both rejected"),
        ("TC_507", "LLM key failover", "Primary key rate-limited", "Backup key used, same model")])]
    for name, rows in tc:
        Tb(f"Test cases - {name}", ["Test ID", "Test objective", "Input / preconditions", "Expected output", "Result"],
           [r + ("PASS",) for r in rows], [1.7, 4.0, 4.1, 4.2, 1.5], 10)
    H("6.3 Results Obtained", 2)
    P("All 116 automated tests in 24 test files pass (Tab. 16, Fig. 37). The rule-book self-check confirms that the generated policy meets all 45 "
      "requirements and that every suggested clause meets its own rules once its blanks are filled (Fig. 38).")
    Tb("Test summary report", ["Metric", "Value"], [("Test files", "24"), ("Total test cases", "116"), ("Test cases passed", "116"),
                                                     ("Test cases failed", "0"), ("Pass rate (%)", "100")], [8, 7.5])
    F(img("t02_pytest"), "Automated test run (pytest, per test file)", 15.5)
    F(img("t03_rulebook"), "Rule-book and intake self-checks", 15.5)
    F(img("t01_swagger_api"), "API testing through the Swagger UI of the FastAPI backend", 15.5)
    P("The system was also evaluated quantitatively, as reported in the accompanying research paper. Tab. 17 summarises the knowledge base, "
      "and Tab. 18–21 report retrieval, chunking, auditing and question answering.")
    Tb("Knowledge base built from the DPDP Act, 2023", ["Item", "Count"], [("Clause chunks (Layer 1)", "82"), ("Obligation records (Layer 2)", "80"),
        ("Principles (Layer 3)", "13"), ("Graph nodes / relationships", "287 / 354"), ("MUST / MUST_NOT / HAS_RIGHT / MAY", "43 / 5 / 5 / 27"),
        ("Rule-book requirements (live system)", "45")], [10, 5.5])
    Tb("Retrieval ablation on the DPDP-QA test split (126 answerable questions)", ["System", "Hit@1", "Hit@5", "MRR", "nDCG@10", "Latency (ms)"], [
        ("Dense only (MiniLM)", "0.468", "0.817", "0.612", "0.668", "11"), ("BM25+ only", "0.611", "0.802", "0.688", "0.722", "0.3"),
        ("Dense-sparse fusion via RRF", "0.611", "0.857", "0.713", "0.748", "11"), ("RRF plus graph (equal weight)", "0.500", "0.738", "0.604", "0.653", "15"),
        ("RRF plus metadata lookup", "0.690", "0.921", "0.790", "0.823", "12"), ("**Full system (with re-ranking)**", "**0.746**", "**0.944**", "**0.832**", "**0.861**", "1,291")],
       [6.0, 1.8, 1.8, 1.8, 2.0, 2.1], 10)
    F(dia("c01_retrieval"), "Retrieval ablation: Hit@1 and nDCG@10", 15.5)
    Tb("Chunking ablation (114 English test questions)", ["Chunking", "Chunks", "Hit@1", "MRR", "Text in top 5 (chars)"], [
        ("Ours: clause-aware, 1,200 chars", "82", "0.614", "0.717", "4,219"), ("Full sections", "46", "0.614", "0.719", "10,095"),
        ("Fixed windows, 1,200 chars", "59", "0.482", "0.622", "5,971"), ("Fixed windows, 300 chars", "236", "0.307", "0.440", "1,497")], [6.0, 2.0, 2.0, 2.0, 3.5], 10)
    Tb("Policy audit on DPDP-Synth (112 decisions) and DPDP-Real (280 decisions)", ["System", "Synth acc.", "Synth kappa", "Synth MAE", "Real kappa", "Real MAE"], [
        ("Keyword-rule baseline", "0.750", "0.625", "11.2", "0.443", "14.9"), ("Single-prompt LLM", "0.848", "0.774", "7.6", "0.623", "10.2"),
        ("Pipeline without guardrails", "0.857", "0.785", "4.5", "0.672", "7.3"), ("**Full pipeline**", "**0.857**", "**0.785**", "**4.5**", "**0.688**", "**6.8**")],
       [5.0, 2.0, 2.2, 2.0, 2.2, 2.1], 10)
    F(dia("c02_audit"), "Audit agreement with labels (Cohen's kappa) and score error", 15.5)
    Tb("Question answering on 25 DPDP-QA test questions", ["System", "Fully correct (%)", "Citation recall", "Fabricated (%)", "Unsupported (%)"], [
        ("LLM, no retrieval", "64", "0.32", "4.0", "63.1"), ("Dense RAG", "76", "0.80", "0.0", "10.8"), ("Hybrid RAG", "76", "0.80", "0.0", "7.9"),
        ("**Full system**", "**76**", "**0.80**", "**0.0**", "**7.9**")], [5.0, 2.8, 2.6, 2.6, 2.6], 10)
    F(dia("c03_qa"), "Question answering: correctness, unsupported claims and fabricated citations", 15.5)
    P("**Interpretation.** Preserving the statute's structure pays off: clause-aware chunks beat fixed windows of the same size (MRR 0.717 vs 0.622), "
      "and exact provision lookup with re-ranking lifts first-rank accuracy from 0.47 to 0.75. Attaching citations from the knowledge base cut unsupported legal "
      "statements from 63% to 8% and fabricated provisions to zero.")
    PB()

    # ═════ 7 Challenges ═════
    H("7 Challenges, Learnings, Contributions", 1)
    H("7.1 Technical Challenges Faced", 2)
    Bl(["**Parsing the Gazette PDF:** page headers, a legacy-font masthead and marginal notes were mixed into the text; sections are accepted only in running order, and the penalty Schedule had to be rebuilt row by row.",
        "**Hallucinated citations:** the model sometimes cited sections it was never shown; citations are now attached by the system and every quote is verified word for word.",
        "**Real policies are hedged:** clauses that use the topic's vocabulary without meeting the duty (“we may retain your information indefinitely”) were read as Partial; hard-negative tests and the rule book now catch them.",
        "**A generated policy failed its own audit:** the drafting template and the audit used different tests; one shared rule book now drafts and checks.",
        "**Memory on a student laptop:** embedding models, the evaluation and the server competed for 8–16 GB RAM; model loading was serialised and experiments run separately.",
        "**Designing for every user:** two motion-heavy designs were rejected as hard to use; the final interface favours large type, plain words and minimal motion."])
    H("7.2 Learning and Insights", 2)
    Bl(["How Retrieval-Augmented Generation, hybrid retrieval and re-ranking work, and why statutory text needs structure-aware chunking.",
        "Designing multi-agent systems with LangGraph and keeping the LLM to judgement while the system controls citations.",
        "Measuring before believing: the knowledge graph, expected to help, lowered ranking, and we report it.",
        "Reading and applying the DPDP Act and Rules, including commencement, penalties and Data Principal rights.",
        "Secure web development (sessions, CSRF, rate limits) and privacy-by-design for our own users.",
        "Teamwork with Git, incremental delivery, automated testing and writing a research paper."])
    H("7.3 Individual Contributions", 2)
    P("Responsibilities and contribution of each member:")
    Tb("Individual contributions", ["Sr. No.", "Member", "Primary responsibilities", "Contribution (%)"],
       [(str(i), n, "[[Add responsibilities]]", "[[%]]") for i, (n, _, _) in enumerate(a["TEAM"], 1)], [1.4, 4.6, 7.0, 2.5])
    PB()

    # ═════ 8 Conclusion ═════
    H("8 Conclusion and Future Work", 1)
    H("8.1 Conclusion", 2)
    P("This project built DPDP Compass, a retrieval-augmented, multi-agent system that audits privacy policies against India's DPDP Act, 2023 and "
      "Rules, 2025, drafts policies that pass the same audit, and answers citizens' questions about their rights. A clause-aware knowledge base of "
      "the Gazette text, hybrid retrieval with exact provision lookup and re-ranking, per-obligation judgement, citations attached by construction, "
      "guardrails and a shared rule book together make each verdict traceable to the clause it read and the provision it rests on.")
    P("All four objectives were addressed: the engine retrieves and verifies obligations (Hit@1 0.746, nDCG@10 0.861); the business module returns "
      "a cited, ranked report with fixes and a generator whose complete drafts audit at 100; the citizen module answers in three languages and "
      "checks app policies; and evaluation shows the pipeline agrees with human labels better than a single prompt and keyword rules (kappa 0.69 "
      "on 20 real policies) while eliminating fabricated citations in our sample. The system gives guidance, not legal advice.")
    H("8.2 Future Work", 2)
    Bl(["Index the full DPDP Rules, 2025 in the evaluation and handle Significant Data Fiduciary duties (DPIA, audits, DPO).",
        "Extend DPDP-Real to more sectors and policies, and have DPDP-QA reviewed by legal practitioners.",
        "Add Consent Manager integration once the Board publishes the technical standards.",
        "Add a user study with citizens and compliance officers; add more Indian languages.",
        "Offer a browser extension that checks a website's policy in place, and continuous monitoring of policy changes.",
        "Deploy on a cloud platform with managed Qdrant and PostgreSQL."])
    PB()

    # ═════ 9 References ═════
    H("9 References", 1)
    H("9.1 Books", 2)
    Bl(["I. Sommerville, Software Engineering, 10th ed. Pearson, 2016.",
        "R. S. Pressman and B. R. Maxim, Software Engineering: A Practitioner's Approach, 9th ed. McGraw-Hill, 2019.",
        "C. D. Manning, P. Raghavan and H. Schütze, Introduction to Information Retrieval. Cambridge University Press, 2008."])
    H("9.2 Research Papers and Journal Articles", 2)
    refs = ["P. Roy et al., “PAKTON: A multi-agent framework for question answering in long legal agreements,” in Proc. EMNLP, 2025.",
            "B. Agarwal et al., “RAGulating compliance: A multi-agent knowledge graph for regulatory question answering,” arXiv:2508.09893, 2025.",
            "“LegalGraphRAG: Multi-agent graph retrieval-augmented generation for reliable legal reasoning,” arXiv:2605.28120, 2026.",
            "“LLM agents in law: Taxonomy, applications, and challenges,” arXiv:2601.06216, 2026.",
            "“Helping Johnny make sense of privacy policies with LLMs,” arXiv:2501.16033, 2026.",
            "P. Lewis et al., “Retrieval-augmented generation for knowledge-intensive NLP tasks,” in Proc. NeurIPS, vol. 33, 2020, pp. 9459–9474.",
            "S. Wilson et al., “The creation and analysis of a website privacy policy corpus,” in Proc. ACL, 2016, pp. 1330–1340.",
            "H. Harkous et al., “Polisis: Automated analysis and presentation of privacy policies using deep learning,” in Proc. USENIX Security, 2018, pp. 531–548.",
            "A. Ravichander et al., “Question answering for privacy policies: Combining computational and legal perspectives,” in Proc. EMNLP-IJCNLP, 2019, pp. 4947–4958.",
            "O. Amaral et al., “AI-enabled automation for completeness checking of privacy policies,” IEEE Trans. Softw. Eng., vol. 48, no. 11, pp. 4647–4674, 2022.",
            "M. Dahl, V. Magesh, M. Suzgun and D. E. Ho, “Large legal fictions: Profiling legal hallucinations in large language models,” J. Legal Anal., vol. 16, no. 1, pp. 64–93, 2024.",
            "V. Magesh et al., “Hallucination-free? Assessing the reliability of leading AI legal research tools,” J. Empirical Legal Stud., vol. 22, no. 2, pp. 216–242, 2025.",
            "Y. Lv and C. Zhai, “Lower-bounding term frequency normalization,” in Proc. CIKM, 2011, pp. 7–16.",
            "N. Reimers and I. Gurevych, “Sentence-BERT: Sentence embeddings using Siamese BERT-networks,” in Proc. EMNLP-IJCNLP, 2019, pp. 3982–3992.",
            "G. V. Cormack, C. L. A. Clarke and S. Buettcher, “Reciprocal rank fusion outperforms Condorcet and individual rank learning methods,” in Proc. SIGIR, 2009, pp. 758–759.",
            "R. Nogueira and K. Cho, “Passage re-ranking with BERT,” arXiv:1901.04085, 2019.",
            "S. Es et al., “RAGAS: Automated evaluation of retrieval augmented generation,” in Proc. EACL (Demos), 2024, pp. 150–158.",
            "J. Cohen, “A coefficient of agreement for nominal scales,” Educ. Psychol. Meas., vol. 20, no. 1, pp. 37–46, 1960.",
            "OpenAI, “gpt-oss-120b & gpt-oss-20b model card,” arXiv:2508.10925, 2025.",
            "R. A. Nikam, A. S. Patil, V. R. Mhetar, S. S. Rajurkar, S. S. Jasuja and D. R. Patil, “DPDP Compass: Citation-enforced hybrid retrieval and guardrailed agents for auditing privacy policies against India's DPDP Act, 2023,” [[venue / status of publication]]."]
    for i, r in enumerate(refs, 1):
        P(f"[{i}] {r}")
    H("9.3 Legal Sources, Online Documentation and Websites", 2)
    Bl(["The Digital Personal Data Protection Act, 2023 (No. 22 of 2023), Gazette of India, Extraordinary, Part II, Sec. 1, 11 Aug. 2023.",
        "The Digital Personal Data Protection Rules, 2025, G.S.R. 846(E); corrigendum G.S.R. 892(E); commencement notification G.S.R. 843(E), Ministry of Electronics and Information Technology, https://www.meity.gov.in, Accessed: 4 August 2026.",
        "FastAPI Documentation, https://fastapi.tiangolo.com/, Accessed: 25 July 2026.",
        "LangGraph Documentation, https://langchain-ai.github.io/langgraph/, Accessed: 25 July 2026.",
        "React Documentation, https://react.dev/, Accessed: 25 July 2026.",
        "Qdrant Documentation, https://qdrant.tech/documentation/, Accessed: 10 August 2026.",
        "Sentence-Transformers Documentation, https://www.sbert.net/, Accessed: 10 August 2026.",
        "Groq API Documentation, https://console.groq.com/docs, Accessed: 29 September 2026.",
        "RAGAS Documentation, https://docs.ragas.io/, Accessed: 4 August 2026."])
    H("9.4 Tools, Frameworks, and Libraries", 2)
    Bl(["React, TypeScript, Vite, Tailwind CSS, Radix UI, React Router – frontend framework, language, build tool, styling, accessible components, routing.",
        "Python, FastAPI, Uvicorn, Pydantic – backend language, web framework, server and validation.",
        "LangGraph – multi-agent orchestration; sentence-transformers, rank-bm25, Qdrant – retrieval.",
        "PyMuPDF, pypdf, python-docx – PDF parsing and document export; SQLite – persistence.",
        "pytest, Playwright, ESLint – testing and linting; Visual Studio Code, Git and GitHub, Docker – development, version control, deployment."])
    PB()

    # ═════ 10 Repository & links ═════
    H("10 Project Repository and Demo Links", 1)
    P("The following project-related links are provided for reference and verification:")
    Tb("Project links", ["Type of link", "URL / link", "Description"], [
        ("Source code repository", "[[GitHub repository URL]]", "Complete source code of the frontend, backend, evaluation and documentation"),
        ("Demo video", "[[Demo video URL]]", "Walkthrough of the audit, generator and citizen desk"),
        ("Deployed application", "[[Deployed application URL]]", "Running instance of DPDP Compass"),
        ("Research paper", "[[Paper URL / DOI]]", "DPDP Compass paper (IEEE format)")], [4.0, 5.0, 6.5])
    PB()

    # ═════ 11 Papers / certificates ═════
    H("11 Copies of Papers Published / Certificates", 1)
    P("This chapter includes copies of the research paper prepared from this project and any certificates of participation or awards.")
    H("11.1 Published Papers", 2)
    P(f"The project group prepared a research paper in IEEE format titled “DPDP Compass: Citation-Enforced Hybrid Retrieval and Guardrailed Agents for "
      f"Auditing Privacy Policies against India's DPDP Act, 2023” under the guidance of {a['GUIDE']}. The authors are " + ", ".join(n for n, _, _ in a["TEAM"]) +
      ". Publication status: [[journal / conference name and status]]. A copy of the paper is included on the following pages.")
    for i in range(1, 9):
        F(S / "bb" / f"paperhi{i}.png", f"Research paper, page {i} of 8", 14.5, 21.5)
    H("11.2 Certificates and Awards", 2)
    a["placeholder_box"]("Insert certificate of participation / award (scan)", 9)
    a["caption"]("Figure", "Certificate of participation / award")



WD_LEFT = __import__("docx").enum.text.WD_ALIGN_PARAGRAPH.LEFT
