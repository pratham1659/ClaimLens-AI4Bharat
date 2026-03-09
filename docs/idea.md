### High-level idea

**ClaimLens is a production-style RAG system for health‑insurance policy analysis.**  
It ingests raw policy PDFs + discharge summaries, turns them into **deterministic legal clauses**, and then answers user questions with an LLM that is **strictly grounded in those clauses** (no free‑form hallucinations).

The focus is: **“given messy Indian health insurance PDFs, reliably find the exact policy clauses you need, then force the LLM to reason only over those clauses.”**

---

### Problem it solves

- **Use case**:  
  - A user (claims analyst / hospital TPA / customer) asks things like:
    - “What is the waiting period for pre‑existing diseases?”
    - “Is this maternity claim admissible under this policy?”
    - “Which clauses apply for accidents vs daycare vs maternity cases?”
- **Pain point**:
  - Policies are long, inconsistent PDFs with weird headings, repeated numbering, annexures, and noisy footers.
  - Typical “dump PDF into vector DB and call GPT” RAG fails badly: wrong chunks, no traceable IDs, noisy retrieval, and lots of hallucinations.
- **Goal**:  
  - Build an **evidence‑constrained**, **evaluation‑driven** RAG pipeline that you could realistically harden into a production backend.

---

### Data & ingestion

- **Inputs** (in `data/` and `data/data2/`):
  - Multiple policy PDFs (e.g. HDFC, Niva Bupa, ICICI, etc.).
  - Discharge summaries for different scenarios (accident, daycare, maternity, waiting period, pre‑existing, etc.).
  - Evaluation query sets (`evaluation_queries.json`, `multiclause_queries.json`, `paraphrase_queries.json`) mapping realistic questions to ground‑truth clause IDs.
- **Ingestion (`app/ingestion/loader.py`)**:
  - PDFs are turned into **page‑level `Document`s**, each with rich **business metadata**:
    - insurer, policy_name, uin, policy_version_year, document_type, page, total_pages, etc.
  - At this stage: **no clause splitting**, no LLM logic, just clean, deterministic ingestion.

---

### Clause splitting = structural backbone

- **Where**: `app/ingestion/clause_splitter.py` (documented heavily in `docs/documentation.md`).
- **Idea**: instead of naive fixed‑size chunks, ClaimLens does **legal‑structure parsing**:
  - Sorts pages by `(insurer, page)` to fix random PDF order.
  - Runs a deterministic parser over the whole document to detect:
    - **Sections**: EXCLUSIONS, GENERAL CONDITIONS, SECTION A – DEFINITIONS, etc.
    - **Clauses**: numbered (1., 1.1., 2.3.4), alphabetic (A., B.), roman (i., iv.), code‑style (Code‑Excl08:), and definition lines (“Grace Period means…”).
  - Ignores preface / marketing / ToC text to avoid polluting the index.
- **Atomic clause model**:
  - Every detected structural boundary becomes a single **atomic clause chunk** (`chunk_type="atomic_clause"`).
  - No nested trees, no bullet‑level splitting – **simple, stable units** that work well for retrieval and evaluation.
- **Canonical clause IDs**:
  - Format:  
    `InsurerClean_p{Page}_{Identifier}_{OccurrenceIndex}`  
    e.g. `ICICILombard_p8_Grace_Period_1`
  - Enforced uniqueness, with fail‑fast `ValueError` on duplicates.
  - These IDs are the **backbone for evaluation and citations**.

---

### Retrieval architecture (AI/RAG core)

**Folder**: `app/retrieval/`

#### 1. Embeddings

- **File**: `embeddings.py`
- Uses **BGE embedding models**: `BAAI/bge-base-en-v1.5` by default (`large`/`small` options too).
- Auto‑detects best device: CUDA → MPS (Apple Silicon) → CPU.
- Embeddings are **normalized** for cosine similarity.

#### 2. Vector store

- **File**: `vector_store.py`
- Uses **FAISS** via LangChain:
  - `build_or_load_vectorstore(...)`:
    - If index path exists → load FAISS index.
    - Else → build from all clause `Document`s and save.
- This gives a persistent dense index over **legal clauses**, not arbitrary text chunks.

#### 3. Hybrid retriever + optional reranker

- **File**: `retriever.py` (`ClaimLensRetriever`)
- **Stage 1 – Candidate generation**:
  - **Dense retrieval** from FAISS (BGE embeddings), top‑K (e.g. 20 or 40).
  - **BM25** lexical retrieval (via `langchain_community.BM25Retriever`) over the same clause docs.
  - Merge + dedupe by `clause_id` into a **hybrid candidate pool**.
- **Stage 2 – Optional cross‑encoder reranking**:
  - **File**: `reranker.py` (`ClauseReranker`)
  - Model: `BAAI/bge-reranker-base` (or `large`) via `sentence_transformers.CrossEncoder`.
  - Scores `(query, clause_text)` pairs and sorts candidates by cross‑encoder score.
  - Returns top‑K final ranking or full ranked list; can also expose scores.
- **Design philosophy**:
  - Retrieval is **deterministic and evaluation‑first**.
  - You can get:
    - `dense`, `bm25`, `hybrid`, and `final` stages for deep debugging.
  - No LLMs involved in retrieval; no magical re‑ranking heuristics.
  - In docs, the “current production‑aligned” architecture is **Dense + Cross‑encoder**, with hybrid BM25 kept as an extension path.

---

### Reasoning layer (LLM, prompts, schema, grounding)

**Folder**: `app/reasoning/`

#### 1. Output schema = structural firewall

- **File**: `output_schema.py`
- Defines **strict Pydantic models**:
  - `Citation`:
    - `clause_id: str`
    - `start_page: int`
  - `RAGResponse`:
    - `answer: str`
    - `found: bool`
    - `citations: List[Citation]`
    - `confidence: Literal["high","medium","low"]`
- Validation rules:
  - Max 3 citations, no duplicate clause_ids.
  - If `found == False`:
    - `citations` must be empty.
    - `answer` must equal the canonical:  
      `"Answer not found in provided policy context."`
- This turns the LLM into a **strict JSON emitter** with **grounded citations** or a standardized “not found” response.

#### 2. Prompt layer

- **File**: `prompt_templates.py`
- Uses LangChain’s `ChatPromptTemplate` with separated **system** and **human** messages.
- System message enforces:
  - Use only provided clauses.
  - No external knowledge or guessing.
  - Max 3 citations.
  - Output **valid JSON only**, no extra prose.
- Human message:
  - Injects formatted retrieved clauses (`formatted_clauses`) + user query (`user_query`).
  - Shows the required JSON schema + an explicit example of the “not found” response.
- This gives **deterministic prompts** for the reasoner, with clear role separation.

#### 3. Reasoner orchestration + retries + grounding

- **File**: `reasoner.py` (`ClaimLensReasoner`)
- Backend LLM:
  - Uses **Groq** via `langchain_groq.ChatGroq`.
  - Default `model_name="openai/gpt-oss-20b"`, `temperature=0.0` for deterministic legal reasoning.
- Flow when you call `answer(query, retrieved_clauses)`:
  1. Format clauses for the prompt.
  2. Collect valid `clause_id`s from retrieved docs.
  3. Build messages via `ChatPromptTemplate`.
  4. Invoke Groq LLM.
  5. Parse raw output strictly with `json.loads` (no regex/magic repair).
  6. Validate using `RAGResponse` schema.
  7. Enforce **citation grounding**:
     - Every citation’s `clause_id` must be in the retrieved set, or it raises `ReasoningValidationError`.
  8. If JSON/schema/grounding fails:
     - Retry up to `max_retries` times.
- **Custom exceptions** in `exceptions.py`:
  - `ClaimLensReasoningError` / `ReasoningValidationError` make reasoning failures **explicit and catchable** in higher layers.

---

### Pipeline orchestration

- **File**: `app/pipeline.py` (`ClaimLensPipeline`)
- This is the **clean backend entrypoint** for the RAG system.
- Injected dependencies:
  - `retriever` (anything with `.retrieve(query)`).
  - `reasoner` (`ClaimLensReasoner`).
- `invoke(query)`:
  - Calls `retriever.retrieve(query)` → list of `Document`s.
  - Enforces not‑empty; fails fast if nothing retrieved.
  - Truncates to `top_k` clauses (controls context size for LLM).
  - Logs query + clause IDs for observability.
  - Calls `reasoner.answer(...)` and returns **a validated `RAGResponse` object**.
- Result: a **single, strongly‑typed RAG boundary** you can wire into a REST API or CLI.

---

### Evaluation framework (retrieval‑only metrics)

**Folder**: `app/evaluation/` + `scripts/run_evaluation.py`

- **Evaluation schema** (`schema.py`):
  - `EvaluationQuery(query: str, relevant_clause_ids: List[str])`.
  - All evaluation JSONs are validated into this schema first.
- **Evaluator** (`evaluator.py`):
  - Multiple modes:
    - **Stage‑wise**:
      - Measures Dense Recall@K, Hybrid Recall@K, Final Recall@K, and Final MRR to see **where** the pipeline fails (candidate generation vs reranking).
    - **Single‑clause evaluation**:
      - For questions with exactly one correct clause.
    - **Multi‑clause evaluation**:
      - For multi‑hop/compound queries, tracks Clause Coverage@20, Full Recall@20, and MRR.
  - Optional diagnostics flag prints:
    - Query, PASS/FAIL, coverage, rank, missing clause IDs, etc.
- **Scripts**:
  - `scripts/run_evaluation.py`:
    - Loads evaluation queries from `data/.../evaluation_queries*.json`.
    - Runs the retriever in stage‑wise mode.
    - Prints metrics to compare experiments.
- Key philosophy: **evaluate retrieval first, completely independent from the LLM**.

---

### Execution / demo scripts

- **File**: `scripts/run_pipeline.py`
  - Hackathon‑friendly CLI that wires:
    - Loader → Clause splitter → Embeddings → (Hybrid) retriever → Reasoner → Pipeline.
  - Handles:
    - `.env` / `GROQ_API_KEY`.
    - Index paths (`INDEX_DIR`), creating FAISS index if missing.
  - Invokes pipeline and prints:
    - Answer, found flag, citations, confidence.
- Additional helpers:
  - `scripts/test_retrieval.py` – local debugging for retrieval.
  - `scripts/export_clauses.py` – export clause set for inspection.
  - `scripts/main.py` – general entrypoint wiring, depending on version.

---

### Tech stack

- **RAG plumbing**: LangChain (documents, FAISS vectorstore, BM25 retriever).
- **Embeddings**: `BAAI/bge-*-en-v1.5` via `langchain_huggingface.HuggingFaceEmbeddings`.
- **Reranking**: `BAAI/bge-reranker-*` via `sentence_transformers.CrossEncoder`.
- **LLM**: Groq (`langchain_groq.ChatGroq`), default `openai/gpt-oss-20b`, temperature 0.0.
- **Validation**: Pydantic models for both evaluation inputs and RAG outputs.
- **Storage**: Local FAISS index for dense vectors.

---

### How this RAG is “different” (good bullets for Reddit)

- **Clause‑aware, not chunk‑aware**:  
  - Uses deterministic parsing to align chunks with legal clauses and gives them **canonical IDs**, instead of arbitrary 512‑token windows.
- **Evaluation‑first**:  
  - Separate evaluation framework with **clause‑ID–based ground truth**, stage‑wise metrics, and multi‑clause metrics.
- **Strictly grounded reasoning**:  
  - Citations must map to retrieved clauses; invalid or hallucinated IDs are rejected.
- **Fail‑fast everywhere**:  
  - Duplicate IDs, empty retrieval, malformed evaluation JSON, invalid LLM outputs – all raise hard errors instead of silently passing.
- **Separation of concerns**:  
  - Clear layers: ingestion → structural parsing → retrieval → evaluation → reasoning → pipeline → execution.
- **Production‑oriented design**:  
  - Dependency injection for retriever/reasoner, top‑K control, observability hooks, and a clean `ClaimLensPipeline` you can drop behind a FastAPI endpoint.

---

### TL;DR (one‑paragraph Reddit summary you can copy)

> ClaimLens is a production‑style RAG system for Indian health‑insurance policies. Instead of blindly chunking PDFs, it deterministically parses policies into canonical legal clauses with stable IDs, builds a dense+BM25 (optionally cross‑encoder) retriever over those clauses, and then runs a Groq‑hosted LLM that’s strictly forced to answer in a validated JSON schema with grounded citations only. The project ships a full evaluation framework (single‑clause, multi‑clause, stage‑wise) using clause‑ID ground truth, plus a clean `ClaimLensPipeline` abstraction that wires retriever + reasoner into a backend‑ready RAG service. The whole thing is engineered for determinism, fail‑fast behavior, and evidence‑constrained reasoning rather than “just vector search + GPT.”