# ClaimLens Architecture Decisions

## 1. Ingestion Layer (loader.py)

### 1.1 Document Granularity
- Initial ingestion is page-level.
- Each page becomes one `Document` object.

### 1.2 Metadata Schema
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

### 1.3 Design Principles
- Business-aware metadata over raw PDF metadata.
- Keep only useful technical fields: `creation_date`, `total_pages`.
- No execution logic inside ingestion module.

---

## 2. Clause Splitting Strategy (clause_splitter.py)

### 2.1 Global Processing
- Pages are merged in order before clause detection.
- Clause detection is performed across the entire document.

### 2.1.1 Strict Input Validation
- The splitter raises an explicit `ValueError` if:
  - The input `policy_documents` list is empty.
  - No valid documents are found after sorting.
- This prevents silent failures and ensures ingestion errors are surfaced early in the pipeline.
- The system is designed to fail fast rather than propagate empty clause outputs downstream.

### 2.2 Heading Detection Rules

We use a hierarchical detection order:

1. Section detection (executed before clause detection)
2. Numbered clause detection

Section detection supports multiple strict structural patterns:

- Full uppercase lines  
  - EXCLUSIONS  
  - GENERAL CONDITIONS  

- Capital letter prefix  
  - A. Basic Cover  
  - B. Exclusions  

- Roman numeral prefix  
  - I. General Conditions  
  - II. Exclusions  

- SECTION prefix format  
  - SECTION A – DEFINITIONS  
  - Section B – General Conditions  

All detected section titles are normalized:
- Prefixes (A., I., SECTION A –) are removed.
- Titles are converted to consistent Title Case.
- The cleaned title is stored in metadata.

### 2.2.2 Modular Validation Architecture

The clause splitter uses modular helper functions to isolate structural responsibilities:

- `_normalize_section()`  
  Responsible for cleaning and standardizing detected section headings.

- `_is_valid_heading()`  
  Applies strict validation rules to candidate numbered headings before accepting them as structural clauses.

- `_save_clause()`  
  Handles clause persistence and bullet-aware splitting logic.

Rationale:
- Keeps the main splitter loop readable.
- Makes structural rules testable in isolation.
- Prevents deeply nested logic in the core iteration loop.
- Encourages controlled future extensibility (e.g., hybrid splitting strategies).

The architecture favors deterministic structural parsing over heuristic-heavy post-processing.

### 2.2.1 Strict Numbered Clause Pattern

Numbered clause detection requires a trailing dot after the numeric hierarchy.

Accepted formats:
- 1.
- 1.1.
- 4.2.8.

Rejected formats:
- 24 hours
- 250 wellness points
- 30 days

This prevents accidental detection of numeric quantities as structural clauses.

The enforced regex pattern:
- ^(\d+(?:\.\d+)*\.)\s+(.+)$

Rationale:
- Ensures only true structural headings create clause chunks.
- Eliminates numeric body text pollution at detection stage instead of filtering later.

### 2.3 Section Handling Decision
- Section detection occurs before clause detection to preserve hierarchical integrity (Section > Clause > Subclause).
- The detected section persists across clauses until a new section heading is encountered.

Note:
Section detection is intentionally strict but may still detect visual headers depending on PDF formatting. Structural clause detection remains the primary authority for chunk creation.

Uppercase headings are treated as:
- Structural metadata only.
- NOT separate clause chunks.

They update:
- `section` field in metadata.

### 2.4 Clause Handling Decision
Numbered headings create clause-level chunks.

Each clause chunk includes:
- The heading
- All text until the next detected heading

No token-based splitting at this stage.

### 2.4.2 Bullet-Level Splitting (Current Implementation)

The splitter performs bullet-aware splitting inside a clause when structural bullet patterns are detected.

Currently supported bullet formats:

- Symbol bullets: •
- Hyphen bullets: -

Detection pattern:
- ^\s*[•\-]\s+

If bullet patterns are detected within a clause:

- Each bullet block becomes an independent retrievable chunk.
- All lines from the bullet start until the next bullet are grouped together.
- Each chunk inherits the parent clause metadata.
- `chunk_type` is set to `"clause_bullet_level"`.

If no bullet structure is detected:
- The entire clause is stored as a single `"clause_level"` chunk.

Design Notes:
- Bullet splitting is deterministic and regex-driven.
- Alphabetical bullets (a), b)) and roman bullets (i., ii.) are not yet structurally split.
- No semantic merging of cross-bullet explanatory text is currently performed.
- Splitting remains structurally safe and predictable.

### 2.4.1 Heading Quality Hardening

In addition to structural numbering, clause headings must pass quality validation before being accepted.

A heading is rejected if:
- It exceeds 12 words.
- It starts with sentence-style phrases such as:
  - "The "
  - "If "
  - "In case "
  - "Further "
  - "However "
  - "Where "
  - "Provided "
  - "Subject to "
- It ends with a period.
- It contains forbidden unit tokens (hours, days, lac, points, inr, %, rs, per).
- Fewer than 50% of words start with uppercase letters.

Rationale:
- Prevents sentence-style body lines from being misclassified as structural clauses.
- Reduces embedding noise.
- Improves retrieval precision without over-fragmenting legal text.

### 2.5 Subsection Hierarchy Decision
We store numbering in a structured but simplified format:

- section
- clause_number (e.g., "1.1.1")
- clause_title (text without numbering)

We do NOT store multi-level hierarchy fields separately.

### 2.6 Clause-Level Metadata
For clause chunks:

- chunk_type = "clause_level"
- section
- clause_number
- clause_title
- start_page (page number where the clause begins, for traceability)


### 2.7 Alphabetical Subclause Handling Decision

In cases where a numbered clause contains alphabetical subclauses such as:

(a) Room Rent  
(b) ICU Charges  

We treat these as part of the same parent numbered clause.

They are NOT split into separate clause chunks.

Reasoning:
- Maintains legal integrity of the parent clause.
- Prevents fragmentation of related conditions.
- Ensures retrieval returns the complete logical unit.

This applies unless future architectural changes explicitly introduce deeper semantic splitting.

---

### 2.8 Table of Contents (TOC) Filtering Strategy

#### Problem Identified
Many policy PDFs contain a Table of Contents (TOC) section at the beginning that includes numbered headings (e.g., "1. Inpatient Treatment") without full clause bodies.

If not filtered, these entries:
- Create short, low-information clause chunks.
- Pollute the vector database.
- May rank higher during retrieval due to keyword density.
- Reduce answer quality during RAG inference.

#### Decision
We implement structural filtering to prevent TOC pollution before embedding.

#### Strategy (Structural Filtering Only)

We rely strictly on structural signals rather than aggressive length-based heuristics.

A clause is discarded if any of the following conditions are met:

1. Dotted leader pattern  
   - Example: `1. Inpatient Treatment........14`  
   - Detected using repeated dot patterns followed by a trailing page number.

2. Trailing page number pattern (without dots)  
   - Example: `1. Inpatient Treatment 14`  
   - Detected when a numbered heading ends with a standalone page number.

3. No body content  
   - If a detected clause contains only the heading line and no explanatory text below it, it is treated as a TOC entry and discarded.

We intentionally do NOT remove entire pages and do NOT rely on aggressive minimum-length thresholds to avoid accidentally discarding valid short legal clauses.

#### Rationale
- Preserves short but legally meaningful clauses.
- Eliminates structural TOC noise without deleting entire pages.
- Improves retrieval precision while maintaining safety.
- Prefers deterministic structural rules over heuristic length-based filtering.

---

## 3. Retrieval Philosophy

### 3.1 Recall vs Precision Strategy

In ClaimLens, the **Recall vs Precision strategy belongs to the Retrieval Stage** of the pipeline.

After completing:
1. Policy ingestion  
2. Clause-aware chunking  

the next stage is:

3. **Retriever design**

This is where we decide how clauses are fetched from the vector database in response to a user query.

Retrieval quality is governed by the balance between **Recall** and **Precision**.

Recall answers:
> Out of all relevant clauses in the policy, how many were retrieved?

Precision answers:
> Out of all retrieved clauses, how many are actually relevant?

Both are critical, but they serve different purposes specifically within the Retriever layer of the system.

---

### 3.2 Retriever Design Overview

- Use hybrid retrieval combining semantic and lexical methods.
- Semantic retrieval via dense embeddings (FAISS).
- Lexical retrieval via BM25 keyword matching.
- Candidate clauses from both are combined.
- Cross-encoder reranking refines final results.
- Structural deduplication ensures unique clause chunks.
- Retrieval parameters tuned for recall and precision balance.

---

### 3.3 Retrieval Design Decisions

- Hybrid retrieval improves recall over single-mode retrieval.
- Cross-encoder reranker boosts precision by rescoring candidates.
- Deduplication by clause_number and start_page prevents redundant chunks.
- Avoids heuristic length filtering; relies on structural TOC filtering.
- Uses deterministic regex patterns for clause detection.
- Prefers structural metadata for traceability and debugging.
- Retrieval tuning focuses on top-K recall and MRR metrics.
           
---

### 3.4 Implementation Details of Hybrid Retrieval

The `ClaimLensRetriever` class implements hybrid retrieval using the following components:

#### 1. Dense Retrieval (FAISS)

- Built using `build_or_load_vectorstore()`.
- Uses embedding model (e.g., BAAI/bge-large-en-v1.5).
- Retrieval executed via:
  - `vectorstore.as_retriever(search_type="similarity", k=dense_top_k)`
- Returns top `dense_top_k` semantically similar clauses.

#### 2. BM25 Retrieval (Lexical)

- Implemented using:
  - `langchain_community.retrievers.BM25Retriever`
- Initialized directly from `clause_documents`.
- Configured with:
  - `bm25_retriever.k = dense_top_k`
- Returns top lexical keyword matches.

#### 3. Hybrid Candidate Pool Construction

The dense and BM25 results are concatenated:

    hybrid_pool = dense_results + bm25_results

Because overlap is common, structural deduplication is applied.

Deduplication key:
- `clause_number`
- `start_page`

This ensures:
- No duplicate structural clauses enter reranking.
- Bullet-level and clause-level chunks remain uniquely identified.
- Structural traceability is preserved.

#### 4. Cross-Encoder Reranking

- Implemented via `ClauseReranker`.
- Uses cross-encoder model:
  - `BAAI/bge-reranker-base`
- Scores (query, clause) pairs directly.
- Returns top `rerank_top_k` highest-scoring clauses.

Final output:
- High recall candidate generation.
- High precision ranking refinement.

---

### 3.5 Architectural Rationale

Why simple concatenation instead of weighted hybrid merging?

Current design uses:
- Concatenation
- Structural deduplication
- Cross-encoder reranking

This is intentional because:

- Reranker learns optimal weighting implicitly.
- Score normalization across retrieval modes is avoided.
- Simplicity improves reproducibility.
- Retrieval behavior remains deterministic and interpretable.

Weighted hybrid scoring may be introduced in future iterations if evaluation metrics indicate recall imbalance.

For the current ClaimLens stage, simple hybrid + reranker is sufficient and production-aligned.

---

## 4. Guiding Principles

- Preserve legal meaning.
- Avoid arbitrary character splitting.
- Prefer structural awareness over naive chunking.
- Keep metadata clean and intentional.
- Avoid structural noise (e.g., Table of Contents pollution) before embedding.
- Prevent structural false positives at detection stage rather than filtering them after chunk creation.
- Prefer multi-granularity chunking (clause-level + bullet-level + long-split fallback).
- Increase semantic precision before attempting retrieval-stage tuning.
- Solve structural problems at ingestion time rather than compensating during reranking.

---

## 5. Evaluation Framework (retrieval_evaluator.py)

### 5.1 Purpose

Evaluation in ClaimLens focuses specifically on **retrieval quality**, not generation quality.

The objective is to measure how effectively the retriever surfaces the correct legal clauses before they are passed to the LLM.

Evaluation is performed after:
1. Ingestion
2. Clause-aware splitting
3. Hybrid retrieval (Dense + BM25 + Reranker)

This ensures structural and retrieval performance can be assessed independently of LLM reasoning.

---

### 5.2 Metrics Implemented

The `RetrievalEvaluator` class computes the following retrieval metrics:

- Recall@K
- Mean Reciprocal Rank (MRR)

These metrics are standard in information retrieval systems and legal search architectures.

---

### 5.3 Recall@K

Recall@K measures whether at least one relevant clause appears within the top K retrieved results.

Definition:
> Did the system retrieve a correct clause within the first K results?

For each query:
- If any relevant clause number appears in the top K → score = 1
- Otherwise → score = 0

We currently compute:

- Recall@5
- Recall@20

Interpretation:

- **Recall@5** evaluates ranking strength (high precision zone).
- **Recall@20** evaluates recall capacity (candidate coverage zone).

Diagnostic insight:
- High Recall@20 but low Recall@5 → Retrieval is finding relevant clauses, but ranking needs improvement.
- Low Recall@20 → Hybrid retrieval configuration or structural chunking needs refinement.

The current implementation assumes one primary relevant clause per query and uses binary recall (0 or 1).

---

### 5.4 Mean Reciprocal Rank (MRR)

MRR measures how early the first correct result appears in the ranked output.

For each query:

If the first relevant clause appears at rank R:

MRR contribution = 1 / R

Examples:
- Rank 1 → 1.0
- Rank 2 → 0.5
- Rank 5 → 0.2
- Not retrieved → 0

MRR rewards early ranking and is particularly important for legal clause retrieval where users rely heavily on top results.

---

### 5.5 Evaluation Loop

The `evaluate()` method:

1. Iterates over structured test queries.
2. Calls the retriever for each query.
3. Computes Recall@5, Recall@20, and MRR.
4. Returns averaged metrics across all queries.

Returned output format:

{
    "Recall@5": float,
    "Recall@20": float,
    "MRR": float
}

---

### 5.6 Design Philosophy

- Evaluation is clause-number based, not text-similarity based.
- Structural correctness is validated before semantic evaluation.
- Metrics isolate retrieval quality independent of LLM reasoning.
- Failures act as diagnostic signals for improving chunking, hybrid retrieval weighting, or reranking.

ClaimLens treats retrieval as a measurable engineering subsystem rather than a black-box embedding lookup.

---

This document serves as the reference architecture for ClaimLens.

---

## 6. Empirical Evaluation Results

### 6.1 Evaluation Setup

Evaluation was conducted using a manually curated set of structured test queries stored in JSON format.

Each test query contains:
- `query`: Natural language insurance question
- `relevant_clause_numbers`: Ground-truth clause numbers expected to answer the query

The evaluation pipeline executed:

1. Clause-aware retrieval
2. Hybrid candidate generation (Dense + BM25)
3. Cross-encoder reranking
4. Metric computation (Recall@K and MRR)

Model Configuration Used:
- Embedding Model: `BAAI/bge-large-en-v1.5`
- Reranker Model: `BAAI/bge-reranker-base`
- Dense Top-K: 20
- Rerank Top-K: 5

---

### 6.2 Evaluation Results (Hybrid + Reranker)

When running the evaluation on the curated test query set:

- Recall@5: **0.7500**
- Recall@20: **0.7500**
- MRR: **0.5906**

---

### 6.3 Interpretation of Results

1. Recall@5 = 0.75
   - 75% of test queries retrieved at least one correct clause within the top 5 results.
   - Indicates strong early ranking performance.

2. Recall@20 = 0.75
   - Equal to Recall@5.
   - Suggests that when a correct clause is not in the top 5, it is also not present in the top 20.
   - Indicates candidate generation limitations rather than reranking issues.

3. MRR ≈ 0.59
   - On average, the first correct clause appears around rank 1–2.
   - Confirms that the cross-encoder reranker is effectively prioritizing relevant clauses.

---

### 6.4 Engineering Insight

The evaluation indicates:

- Reranking quality is strong.
- Primary failure cases arise during candidate generation.
- Hybrid retrieval (Dense + BM25) significantly improves recall compared to single-mode retrieval.
- Structural clause splitting remains critical to maintaining retrieval precision.

Further improvements may focus on:
- Increasing dense retrieval pool size
- Adjusting BM25 recall window
- Expanding evaluation dataset size

The system demonstrates production-aligned retrieval behavior on real insurance policy documents.