# ClaimLens Architecture Decisions (Updated)

This document defines the canonical engineering architecture for ClaimLens after structural hardening of:

- Clause Splitter
- Retriever (Dense + Cross-Encoder)
- Evaluation Framework

This version supersedes earlier hybrid BM25 references and reflects the current production-aligned system.

---

# 1. Ingestion Layer (loader.py)

## 1.1 Document Granularity

- Initial ingestion is page-level.
- Each page becomes one `Document` object.
- No clause detection occurs at ingestion time.
- Ingestion is deterministic and logic-free.

## 1.2 Metadata Schema

Each page-level document contains:

- source
- file_name
- insurer
- policy_name
- uin
- policy_id
- policy_version_year
- document_type
- creation_date
- page
- total_pages
- chunk_type ("page_level")
- section (initially None)
- subsection (initially None)
- clause_title (initially None)

## 1.3 Design Principles

- Business-aware metadata over raw PDF metadata.
- Fail-fast philosophy.
- No execution logic inside ingestion module.
- Structural correctness is enforced in clause splitter, not loader.

---

# 2. Clause Splitting Strategy (clause_splitter.py)

Clause splitting is the structural backbone of ClaimLens.

All semantic retrieval quality depends on deterministic structural parsing.

## 2.1 Global Processing

- Pages are sorted and merged in order.
- Clause detection runs across the entire document.
- Cross-page clauses are preserved.

Strict validation:

- Raises `ValueError` if:
  - Empty input list
  - No valid documents after sorting

The system never silently returns empty clause sets.

## 2.1.1 Parsing Design Rationale (Critical Engineering Decisions)

The following architectural decisions in the clause splitter are intentional and fundamental to system stability. These are documented to preserve long-term maintainability and reasoning clarity.

### Why Sorting Matters

Before parsing, documents are sorted by:

    (insurer, page)

PDF loaders do not guarantee page order. Without sorting:

- Cross-page clauses may break.
- Clause boundaries may be misinterpreted.
- Clause IDs may become unstable.
- Determinism is lost.

Sorting ensures that the parser operates as a deterministic state machine over a stable input sequence. Structural correctness depends on ordered traversal.

### Why Clause Finalization Is Isolated (`save_clause()`)

Clause parsing has two distinct phases:

1. Accumulation phase (collect lines)
2. Finalization phase (convert to structured Document)

The `save_clause()` function isolates finalization logic to:

- Avoid code duplication
- Prevent partial clause saves
- Centralize metadata construction
- Ensure consistent bullet handling

Separating accumulation from finalization makes the parser modular, readable, and less error-prone.

### Why Text Before First Clause Is Ignored

Insurance PDFs typically begin with:

- Cover pages
- Policy introductions
- Marketing text
- Table of contents

Only numbered headings define retrievable legal clauses.

Capturing preface text would:

- Pollute the vector index
- Reduce retrieval precision
- Introduce non-actionable noise

Therefore, text is accumulated only after the first valid numbered heading is detected. This is a precision-first design choice.

### Why Duplicate Clause ID Validation Exists

After splitting, all clause IDs are validated for uniqueness.

If duplicate IDs are detected, the system raises a `ValueError`.

This prevents:

- Silent vector overwrites
- Evaluation corruption
- Loss of traceability
- Debugging ambiguity

Duplicate IDs are considered catastrophic structural errors, not warnings. ClaimLens prioritizes fail-fast structural safety over silent tolerance.

### Why Bullet Splitting Happens During Finalization

Bullet splitting occurs inside `save_clause()` after a clause is fully assembled.

This preserves hierarchy:

Clause  
→ Bullet 1  
→ Bullet 2  

If bullet splitting occurred during line-by-line parsing:

- Clause continuity would break
- Metadata inheritance would become unstable
- ID generation would become inconsistent
- State management would become complex

Bullet splitting is considered structural refinement, not detection logic. Therefore it belongs in the finalization phase.

These decisions collectively ensure that the clause splitter functions as a deterministic legal-structure parser rather than a naive text segmenter.

## 2.2 Section Detection (Hierarchical Precedence)

Section detection runs BEFORE clause detection.

Supported structural formats:

- Full uppercase:
  - EXCLUSIONS
  - GENERAL CONDITIONS

- Alphabet prefix:
  - A. Basic Cover
  - B. Exclusions

- Roman prefix:
  - I. Definitions
  - II. General Conditions

- SECTION format:
  - SECTION A – DEFINITIONS

Normalization rules:

- Prefixes removed
- Converted to Title Case
- Stored in metadata only
- NEVER create chunks

Sections persist until a new section is detected.

## 2.3 Strict Numbered Clause Detection

Only headings matching:

    ^(\d+(?:\.\d+)*\.)\s+(.+)$

Examples accepted:

- 1.
- 1.1.
- 4.2.8.

Rejected:

- 24 hours
- 30 days
- 250 wellness points

This prevents numeric body pollution.

## 2.4 Heading Quality Hardening

A numbered heading is rejected if:

- More than 12 words
- Starts with:
  - The
  - If
  - In case
  - Further
  - However
  - Where
  - Provided
  - Subject to
- Ends with a period
- Contains unit tokens:
  - hours, days, lac, points, inr, %, rs, per
- Less than 50% words capitalized

Purpose:

- Eliminate sentence-style false positives
- Prevent embedding noise
- Improve retrieval precision upstream

## 2.5 Deterministic Bullet-Level Splitting

Supported bullet types:

- •
- -

Regex:

    ^\s*[•\-]\s+

If bullets detected:

- Each bullet block becomes a retrievable chunk
- Parent metadata preserved
- chunk_type = "clause_bullet_level"

If no bullets:

- Single clause chunk
- chunk_type = "clause_level"

NOT supported (intentional):

- (a), (b)
- (i), (ii)
- Nested indentation

Reason:

- Avoid over-fragmentation
- Maintain legal coherence

## 2.6 Canonical Clause ID System (Critical)

Each clause receives deterministic ID:

Format:

    {Insurer}_{Section}_{ClauseNumber}

Fallback:

    {Insurer}_{Section}_{SanitizedClauseTitle}

Examples:

- ICICILombard_TotalPremium_4.1.7
- ICICILombard_TotalPremium_GracePeriod

Properties:

- Insurer-aware
- Deterministic
- Stable across formatting changes
- Evaluation-safe
- Independent of embedding changes


Clause IDs are the backbone of:

- Retrieval evaluation
- Debugging
- Traceability

## 2.6.1 Clause ID Collision Safety (Why Occurrence Index Exists)

Real-world insurance PDFs are structurally inconsistent.

The following edge cases occur frequently:

- Duplicate headings caused by PDF extraction artifacts.
- Clause numbers repeated across annexures.
- Headings repeated across page breaks.
- Formatting inconsistencies that cause the same clause number to appear multiple times on the same page.

Because of this, the tuple:

    {Insurer}_{Section}_{ClauseNumber}

cannot be mathematically guaranteed to be globally unique.

To guarantee deterministic uniqueness, the splitter maintains an occurrence counter per:

    (insurer, page, clause_number)

If the same structural heading appears multiple times, an incremented suffix is appended internally during generation before final canonicalization.

Purpose of the counter:

- Prevent silent ID collisions
- Prevent evaluation corruption
- Prevent overwriting during vector indexing
- Ensure deterministic behavior even on malformed PDFs

Important:

The counter is NOT semantic numbering.
It is purely a collision-prevention mechanism.

ClaimLens prioritizes structural safety over assumptions about PDF cleanliness.

## 2.7 TOC Filtering (Structural)

Discarded if:

1. Dotted leader pattern
2. Trailing page number
3. No body content

No aggressive length heuristics used.

Purpose:

- Prevent TOC pollution
- Improve retrieval precision
- Preserve short but valid clauses

---

# 3. Retrieval Architecture (retriever.py)

ClaimLens uses a two-stage retrieval pipeline.

No weighted hybrid merging is used in current production.

## 3.1 Dense Retrieval (Candidate Generation)

Embedding model:

    BAAI/bge-base-en-v1.5

Vector store:

    FAISS

Configuration:

- Top-K retrieval = 40

Purpose:

- High semantic recall
- Large candidate pool
- No heuristic filtering

## 3.2 Cross-Encoder Reranking

Model:

    BAAI/bge-reranker-base

Process:

- Query paired with each top-40 candidate
- Cross-encoder scores each pair
- Top 5 highest-scoring returned

Configuration:

- Rerank Top-K = 5

Purpose:

- Improve early precision
- Boost MRR
- Reduce ranking noise

## 3.3 Why No Weighted Hybrid?

Previous documentation referenced hybrid BM25 weighting.

Current production design:

- Dense + Cross-Encoder only
- No score merging
- No manual weighting
- No normalization complexity

Reason:

- Cross-encoder implicitly learns weighting
- Simpler pipeline
- More deterministic debugging

Hybrid lexical retrieval remains future extensibility, not current implementation.

## 3.4 Retrieval Philosophy

- Structural correctness before semantics
- No LLM involvement in retrieval
- Retrieval is deterministic
- Reranking refines but does not hallucinate
- Evaluation-driven iteration

---

# 4. Evaluation Framework (evaluator.py)

Evaluation measures retrieval only.

LLM generation is not evaluated here.

## 4.1 Evaluation Inputs

Each test case contains:

- query
- relevant_clause_ids (canonical IDs)

Evaluation is clause-ID based.

Not clause-number based.

Not text-similarity based.

## 4.2 Metrics Implemented

- Recall@5
- Recall@20
- Mean Reciprocal Rank (MRR)

## 4.3 Recall@K

Binary per query:

- 1 if any relevant clause appears within top K
- 0 otherwise

Interpretation:

- Recall@5 → ranking strength
- Recall@20 → candidate coverage

Diagnostic meaning:

- High Recall@20, low Recall@5 → ranking issue
- Low Recall@20 → retrieval or chunking issue

## 4.4 Mean Reciprocal Rank (MRR)

For first relevant clause at rank R:

    1 / R

Examples:

- Rank 1 → 1.0
- Rank 2 → 0.5
- Rank 5 → 0.2
- Not retrieved → 0

MRR rewards early precision.

## 4.5 Evaluation Loop

For each query:

1. Run retriever
2. Collect returned clause_ids
3. Compute Recall@5
4. Compute Recall@20
5. Compute MRR
6. Average across queries

Output:

{
    "Recall@5": float,
    "Recall@20": float,
    "MRR": float
}

---


# 5. Reasoning Layer

## 5.1 output_schema.py

The reasoning layer enforces strict structural guarantees on LLM output.

Unlike retrieval, which is deterministic, reasoning involves probabilistic generation.  
Therefore, structural validation is mandatory.

The `output_schema.py` file defines the canonical response contract for ClaimLens.

It ensures:

- Grounded answers only
- Structured citations
- Logical consistency
- Deterministic API behavior
- Retry-safe validation

### 5.1.1 Citation Model

```python
class Citation(BaseModel):
    clause_id: str
    start_page: int
```

Each citation represents a single legal reference used to support the answer.

### Purpose

- Enforces canonical clause ID usage.
- Ensures page numbers are integers.
- Prevents malformed citation objects.
- Guarantees traceability to source clause.

### Execution in Pipeline

After LLM generates JSON output, Pydantic attempts to construct:

```python
Citation(
    clause_id="ICICILombard_BasicCover_7.1.1",
    start_page=13
)
```

If the model outputs:

```json
{
  "clause_id": 7111,
  "start_page": "thirteen"
}
```

Validation fails and raises a `ValidationError`.

This prevents corrupted references from entering the system.

### 5.1.2 RAGResponse Model

```python
class RAGResponse(BaseModel):
    answer: str
    found: bool
    citations: List[Citation]
    confidence: Literal["high", "medium", "low"]
```

This defines the complete output contract returned by the reasoning layer.

Every LLM response must conform to this structure.

### 5.1.3 Validation Flow (Under the Hood)

When the LLM returns JSON:

1. Pydantic parses the JSON.
2. Each `Citation` object is constructed.
3. Field validators run.
4. Model-level validators run.
5. Either:
   - A structured object is returned
   - A `ValidationError` is raised

This ensures deterministic enforcement of output constraints.

### 5.1.4 Citation Validation Rules

Inside `validate_citations()`:

Rules enforced:

- Maximum of 3 citations allowed.
- No duplicate `clause_id` values.

Example (Invalid):

```json
"citations": [
  {"clause_id": "A", "start_page": 13},
  {"clause_id": "A", "start_page": 13}
]
```

Raises:

    ValueError("Duplicate clause_ids in citations.")

Purpose:

- Prevent citation spam
- Maintain clarity
- Avoid redundant grounding
- Improve evaluation stability

### 5.1.5 Logical Consistency Enforcement

Inside `consistency_check()`:

If:

    found == False

Then:

- `citations` must be empty.
- `answer` must equal:

      "Answer not found in provided policy context."

### Example (Invalid)

```json
{
  "answer": "It is 36 months.",
  "found": false,
  "citations": [
    {"clause_id": "ICICILombard_BasicCover_7.1.1", "start_page": 13}
  ],
  "confidence": "high"
}
```

This raises:

    ValueError("Citations must be empty when found is False.")

Reason:

The response claims the answer was not found while providing citations.  
This is logically contradictory and rejected.

### 5.1.6 Valid Not-Found Case

```json
{
  "answer": "Answer not found in provided policy context.",
  "found": false,
  "citations": [],
  "confidence": "low"
}
```

This passes validation because:

- No citations provided
- Standardized not-found message used
- Logical consistency preserved

### 5.1.7 Why Strict Validation Exists

LLMs generate probabilistically and may:

- Produce contradictory fields
- Provide malformed citations
- Hallucinate unsupported references
- Use inconsistent not-found phrasing

The output schema acts as a structural firewall.

Only logically consistent, structurally valid, and grounded responses are accepted.

If validation fails:

1. A `ValidationError` is raised.
2. Retry logic can be triggered.
3. The LLM is re-prompted to correct format violations.

### 5.1.8 Design Philosophy

- Grounding is enforced, not assumed.
- Logical consistency is mandatory.
- Output format is deterministic.
- Schema validation precedes API response.
- Reasoning errors are caught structurally, not heuristically.

The reasoning layer transforms probabilistic generation into a controlled, production-safe subsystem.

## 5.2 prompt_templates.py

The prompt layer defines how structured retrieval context is presented to the LLM.

Unlike `output_schema.py`, which validates outputs, `prompt_templates.py` controls input structure.

It is responsible for:

- System-level behavioral contract
- Context injection (retrieved clauses)
- User query injection
- JSON output instruction enforcement
- Separation of roles (system vs human)

### 5.2.1 System Prompt (Behavior Contract)

The system message defines non-negotiable constraints:

- Use only provided clauses.
- Do not use external knowledge.
- Do not assume missing facts.
- If unsupported → return standardized not-found JSON.
- Maximum 3 citations.
- Valid JSON output only.
- No commentary outside JSON.

This message is structurally isolated from the human message.

Reason:

LLMs treat system messages with higher priority.
Separating behavioral rules from task context improves rule adherence.

### 5.2.2 Human Message Template

The human message contains:

- Formatted policy clauses
- The user question
- Required JSON schema structure
- Explicit not-found example

Variables injected:

- `formatted_clauses`
- `user_query`

No manual string concatenation is performed at execution time.
Variables are injected through `ChatPromptTemplate`.

This ensures deterministic input formatting.

### 5.2.3 Why ChatPromptTemplate Is Used

`ChatPromptTemplate` provides:

- Explicit role separation (system vs human)
- Safe variable injection
- Deterministic message structure
- Reusability across calls
- Easy extensibility (few-shot, tools, safety layers)

It does NOT execute the LLM.
It only builds structured messages.

Execution remains inside `reasoner.py`.

### 5.2.4 Execution Flow in Pipeline

For a query:

    "What is the grace period?"

Pipeline steps:

1. Retriever returns relevant clause Documents.
2. `format_clauses_for_prompt()` converts them into structured context blocks.
3. `build_chat_prompt_template()` creates a reusable template.
4. Variables are injected via:

       template.format_messages(
           formatted_clauses=...,
           user_query=...
       )

5. The resulting message list is passed to the LLM.
6. LLM returns JSON.
7. JSON is validated by `output_schema.py`.

Prompt construction and output validation are separate concerns.

### 5.2.5 Architectural Separation

Reasoning layer is divided into:

- prompt_templates.py → Input construction
- output_schema.py → Output validation
- reasoner.py → Orchestration + retry logic

This separation prevents:

- Prompt logic leaking into validation
- Validation logic leaking into prompt design
- Execution logic mixing with template design

Each module has one responsibility.

## 5.3 reasoner.py

The `reasoner.py` module is the execution core of the reasoning layer.

It orchestrates:

- Prompt construction
- LLM invocation
- JSON parsing
- Pydantic schema validation
- Citation grounding enforcement
- Retry logic
- Structured exception handling

Unlike `prompt_templates.py` and `output_schema.py`, which define static contracts, `reasoner.py` is responsible for runtime enforcement and controlled interaction with the LLM.

### 5.3.1 Why a Dedicated Reasoner Class Exists

`ClaimLensReasoner` encapsulates all reasoning behavior into a single controlled subsystem.

This prevents:

- LLM calls scattered across the codebase
- Prompt logic mixing with API code
- Validation logic leaking into retrieval
- Uncontrolled retries

The class structure enables:

- Configuration isolation (model name, temperature, retries)
- Controlled failure boundaries
- Future extensibility (logging, metrics, tracing)

### 5.3.2 Deterministic Configuration

The model is initialized with:

    temperature = 0.0

Reason:

ClaimLens is a legal reasoning system, not a creative assistant.

Low temperature ensures:

- Reduced hallucination
- More stable JSON formatting
- Higher reproducibility
- Consistent evaluation behavior

Determinism is prioritized over linguistic variety.

### 5.3.3 Execution Flow

When `answer()` is called:

1. Retrieved clauses are formatted using `format_clauses_for_prompt()`.
2. Valid clause IDs are collected into a set.
3. Prompt messages are built via `ChatPromptTemplate`.
4. The LLM is invoked.
5. Raw output is parsed strictly using `json.loads`.
6. Output is validated using `RAGResponse`.
7. Citations are verified against retrieved context.
8. If validation fails, retry logic executes.
9. If all retries fail, a structured exception is raised.

This layered enforcement ensures that probabilistic generation becomes structurally deterministic.

### 5.3.4 Strict JSON Parsing (Fail-Fast Policy)

The system uses:

    json.loads(text)

No regex repair.
No markdown stripping.
No heuristic correction.

If JSON is malformed:

- Parsing fails immediately.
- Retry logic is triggered.

Fail-fast behavior prevents silent corruption.

### 5.3.5 Citation Grounding Enforcement

After schema validation, citations are verified:

    if citation.clause_id not in retrieved_clause_ids:
        raise ReasoningValidationError(...)

This ensures:

- The LLM cannot invent clause IDs.
- Answers remain grounded strictly in retrieved evidence.
- Retrieval metrics remain meaningful.
- Hallucinated citations are rejected.

Without this step, RAG degenerates into ungrounded generation.

This enforcement transforms ClaimLens into a true evidence-constrained reasoning system.

### 5.3.6 Retry Logic

The system retries only when:

- JSON parsing fails
- Schema validation fails
- Citation grounding fails

It does NOT retry:

- Network errors
- Model unavailability
- Infrastructure failures

This controlled retry scope ensures that only formatting violations are corrected, not systemic faults.

### 5.3.7 Exception Handling Strategy

If all retries fail:

    ReasoningValidationError is raised.

This prevents:

- Raw Pydantic errors leaking to API layer
- Internal validation details surfacing to users
- Silent acceptance of corrupted output

Reasoning failures are explicitly categorized and isolated.

## 5.4 exceptions.py

The `exceptions.py` module defines structured failure boundaries for the reasoning layer.

It contains:

- `ClaimLensReasoningError` (base class)
- `ReasoningValidationError` (specialized subclass)

### 5.4.1 Why Custom Exceptions Exist

Using generic exceptions like `ValueError` would:

- Blur subsystem boundaries
- Complicate API-level error handling
- Mix reasoning failures with ingestion or retrieval failures

Custom exceptions allow upper layers to distinguish:

- Retrieval errors
- Reasoning validation errors
- Infrastructure failures

Example at API layer:

    except ClaimLensReasoningError:
        return structured_error_response

This maintains architectural clarity.

### 5.4.2 Architectural Role

The exception module ensures:

- Reasoning failures are explicit
- Validation failures are not silently ignored
- Subsystems remain decoupled
- Error handling remains scalable

Exceptions are treated as controlled failure signals, not unexpected crashes.

ClaimLens prioritizes structural safety over permissive execution.

---

# 6. Pipeline Layer (pipeline.py)

The `pipeline.py` module defines the orchestration boundary of the ClaimLens backend.

It coordinates the complete RAG execution flow while remaining strictly separated from:

- Retrieval logic
- Prompt construction logic
- Output validation logic
- API transport logic

The pipeline is not responsible for intelligence.
It is responsible for orchestration.

## 6.1 Architectural Role

The pipeline represents the backend system boundary.

Execution Flow:

    Query
        → Retriever
        → Top-K Selection
        → Reasoner
        → Validated RAGResponse

The pipeline does not:

- Inspect embedding scores
- Modify clause text
- Construct prompts
- Parse JSON
- Perform validation

It delegates all intelligence to specialized subsystems.

## 6.2 Dependency Injection (Professional Design)

The retriever and reasoner are injected into the pipeline constructor.

This ensures:

- Loose coupling
- Component swappability
- Testability
- Clear dependency graph
- No hidden instantiation of heavy components

The pipeline does not create its own retriever or reasoner.
It receives them.

This is production-grade backend architecture.

## 6.3 Top-K Context Control

Even if the retriever produces a large candidate set,
the pipeline strictly limits the number of clauses passed to the LLM.

Purpose:

- Prevent context window overflow
- Reduce hallucination risk
- Control token cost
- Improve latency

The pipeline controls reasoning context size.
Retrieval controls candidate generation.

This separation prevents uncontrolled context growth.

## 6.4 Observability and Logging

The pipeline logs retrieval metadata only.

Logged data:

- Query
- Top-K value
- Retrieved clause IDs

Not logged:

- Clause text
- Raw model output

This enables:

- Retrieval debugging
- Failure tracing
- Future monitoring dashboards

Sensitive legal text is intentionally excluded from logs.

## 6.5 Return Type Discipline

The pipeline returns a `RAGResponse` object.

It does not return:

- Raw JSON
- Dictionaries
- HTTP responses

Serialization is handled by the API layer.

This preserves:

- Business layer purity
- Transport layer separation
- Clean system boundaries

## 6.6 Fail-Fast Policy

If the retriever returns no clauses, the pipeline raises an error.

The reasoner is never invoked on empty context.

This prevents:

- Hallucinated answers without evidence
- Silent degradation
- Undefined reasoning behavior

Fail-fast behavior is enforced across the ClaimLens architecture.

The pipeline transforms ClaimLens from a collection of modules
into a coherent backend subsystem.

---

# 7. System-Level Engineering Interpretation

Empirical findings:

- Structural chunking quality directly affects Recall@20.
- Cross-encoder strongly improves Recall@5 and MRR.
- Failures typically originate in candidate generation, not reranking.
- Canonical clause IDs prevent evaluation drift.
- Deterministic parsing outperforms heuristic patching.

---

# 8. Guiding Principles (Finalized)

- Preserve legal meaning.
- Deterministic structural parsing.
- Fail fast on ingestion errors.
- Solve structural issues upstream.
- Avoid heuristic post-processing.
- Prefer semantic precision over excessive chunking.
- Retrieval is measurable, not magical.
- Canonical clause IDs are non-negotiable.
- Evaluation is insurer-aware and stable.

---

This document is the authoritative architectural reference for ClaimLens.

All future changes must preserve:

- Deterministic structural parsing
- Canonical clause ID stability
- Retrieval metric reproducibility
- Separation of ingestion, retrieval, and evaluation layers

ClaimLens treats retrieval as an engineering subsystem, not a black-box embedding lookup.

---

# 9. Execution & Demo Layer (scripts/run_pipeline.py)

The `run_pipeline.py` script represents the controlled execution entrypoint for local testing and hackathon demonstrations.

It is **not** part of the production API layer.  
It is a CLI orchestration script designed for:

- End-to-end validation
- Local debugging
- Demonstration runs
- System verification before API integration

It exercises the complete RAG pipeline from ingestion to structured reasoning.

## 9.1 Architectural Position

The execution script sits outside the `app/` package.

Its responsibility is orchestration of:

    Loader
        → Clause Splitter
        → Embeddings
        → Hybrid Retriever
        → Reasoner
        → Pipeline
        → Structured Output

It does not contain:

- Business logic
- Retrieval algorithms
- Prompt logic
- Validation logic

It simply wires components together.

## 9.2 Environment Initialization

The script performs controlled environment setup before execution:

- Loads `.env` using `load_dotenv()`
- Verifies `GROQ_API_KEY` presence
- Disables tokenizer parallelism
- Suppresses non-critical warnings
- Reduces library log verbosity

This ensures:

- Clean CLI output
- Deterministic runtime behavior
- Reduced debugging noise
- Controlled demonstration output

Environment configuration is isolated at the top of the script to prevent side-effects inside core modules.

## 9.3 Deterministic Path Resolution

The script dynamically resolves:

    BASE_DIR
    DATA_DIR
    INDEX_DIR

This avoids:

- Hard-coded absolute paths
- Machine-specific configurations
- Fragile relative imports

Indexes are created if missing.
FAISS indexes are reused if already built.

This ensures repeatable runs without rebuilding embeddings unnecessarily.

## 9.4 Hybrid Retrieval Initialization

The script initializes:

- Embedding model: `BAAI/bge-base-en-v1.5`
- Hybrid retriever:
    - Dense FAISS
    - BM25 lexical retriever
    - Optional cross-encoder reranker

The retriever is constructed externally and injected into the pipeline.

This preserves architectural separation and demonstrates dependency injection in practice.

## 9.5 Reasoner Initialization

The reasoning engine:

- Uses Groq-hosted LLM
- Runs with `temperature=0.0`
- Enforces strict JSON validation
- Enforces citation grounding
- Implements retry on formatting failures

The execution script does not modify reasoning behavior.
It relies entirely on the reasoning subsystem's internal guarantees.

## 9.6 Pipeline Invocation

The script constructs:

    ClaimLensPipeline(
        retriever=...,
        reasoner=...,
        top_k=5
    )

Then invokes:

    pipeline.invoke(query)

The pipeline:

- Limits reasoning context
- Logs retrieval metadata
- Returns validated `RAGResponse`

The execution script prints structured fields from the response:

- Answer
- Found flag
- Citations
- Confidence

It does not parse raw JSON or inspect internal state.

## 9.7 Why This Layer Exists

Without a dedicated execution script:

- Testing would require API scaffolding
- Debugging would be slower
- Hackathon demos would be noisy
- Reproducibility would decrease

The execution layer provides a clean boundary between:

Core Backend Logic (`app/`)
and
User Interaction Layer (CLI or API)

This separation ensures that production logic remains untouched while experimentation and demonstrations remain controlled.

## 9.8 Production Consideration

In production deployment:

- `run_pipeline.py` is not used.
- API layer (e.g., FastAPI) will import and use `ClaimLensPipeline`.
- Logging configuration will move to server-level settings.
- Environment configuration will be handled by deployment infrastructure.

The execution script exists purely for:

- Local verification
- Engineering validation
- Demonstration clarity

It completes the architectural stack by providing a controlled entrypoint into the system.

---

This concludes the full architectural documentation of ClaimLens.

The system now consists of:

1. Ingestion Layer
2. Structural Parsing Layer
3. Hybrid Retrieval Layer
4. Evaluation Framework
5. Reasoning Layer
6. Pipeline Orchestration Layer
7. Execution/Demo Layer

Each layer is:

- Structurally isolated
- Deterministic where required
- Validation-driven
- Architecturally separated

ClaimLens is designed as a modular, evidence-grounded RAG system suitable for production-grade legal retrieval and reasoning.

---

# 10. High-Level System Diagram

This section describes the end-to-end architectural flow of ClaimLens at a system level.

The diagram below represents logical component boundaries, not infrastructure deployment details.

## 10.1 Logical Architecture Flow

```
                ┌────────────────────┐
                │      User Query     │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │  Pipeline Layer     │
                │ (Orchestration)     │
                └─────────┬──────────┘
                          │
          ┌───────────────┴────────────────┐
          ▼                                ▼
┌────────────────────┐          ┌────────────────────┐
│   Retriever Layer   │          │   Reasoning Layer  │
│ (Dense + BM25 +     │          │  (LLM + Validation)│
│  Reranker)          │          └─────────┬──────────┘
└─────────┬──────────┘                    │
          │                                ▼
          ▼                     ┌────────────────────┐
┌────────────────────┐          │  Output Schema     │
│   Vector Store      │          │  (Pydantic Model)  │
│   + BM25 Index      │          └─────────┬──────────┘
└────────────────────┘                    │
                                           ▼
                                 ┌────────────────────┐
                                 │  Structured Answer  │
                                 │  (RAGResponse)      │
                                 └────────────────────┘
```

## 10.2 Layer Responsibilities (At a Glance)

Ingestion Layer:
- Converts raw PDF → page-level documents
- Injects structured metadata

Structural Parsing Layer:
- Converts pages → deterministic legal clauses
- Generates canonical clause IDs

Retrieval Layer:
- Generates candidate clauses (Dense + BM25)
- Reranks with cross-encoder
- Produces ranked evidence set

Reasoning Layer:
- Builds structured prompt
- Calls LLM
- Enforces strict JSON parsing
- Validates citations and logical consistency

Pipeline Layer:
- Controls Top-K context
- Enforces fail-fast policy
- Returns validated RAGResponse

Execution/API Layer:
- CLI (run_pipeline.py) or
- FastAPI backend (future deployment)

The diagram demonstrates strict separation of concerns and unidirectional data flow.

---

# 11. Deployment Roadmap

This section defines the production evolution plan for ClaimLens beyond hackathon scope.

The roadmap is structured in progressive phases.

## Phase 1 – Local Engineering Validation (Completed)

- Deterministic clause parsing
- Hybrid retrieval with reranking
- Retrieval evaluation metrics
- Structured reasoning with strict validation
- CLI execution script

Goal:
Establish architectural stability and retrieval correctness.

## Phase 2 – Backend API Layer

- Wrap `ClaimLensPipeline` inside FastAPI
- Expose endpoint:

      POST /query

- Input:

      { "query": "..." }

- Output:

      RAGResponse (JSON)

Add:
- Structured error handling
- Logging middleware
- Request tracing

Goal:
Transform ClaimLens into a deployable service.

## Phase 3 – Infrastructure & Scaling

- Containerization (Docker)
- Environment-based configuration
- Separate index storage volume
- Horizontal scaling of API layer
- Model hosting optimization (Groq or self-hosted alternative)

Optional Enhancements:
- Caching layer (Redis)
- Async retrieval execution
- Monitoring (Prometheus / Grafana)

Goal:
Production-grade scalability.

## Phase 4 – Advanced RAG Improvements

- Clause-level relevance feedback loop
- Retrieval score logging
- Hard negative mining
- Hybrid weighting experiments
- Domain-specific reranker fine-tuning

Goal:
Improve Recall@20 and MRR through data-driven iteration.

## Phase 5 – Multi-Policy & Multi-Insurer Expansion

- Multi-index routing
- Policy-level filtering
- Cross-policy comparison
- Multi-document grounding

Goal:
Scale from single-policy reasoning to enterprise-scale document intelligence.

---

ClaimLens is designed to evolve from a research-grade RAG prototype
into a production-ready legal retrieval and reasoning platform.

The architectural foundations documented above ensure that each deployment phase
can be implemented without refactoring core subsystems.