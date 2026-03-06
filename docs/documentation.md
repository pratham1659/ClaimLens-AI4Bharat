# ClaimLens Architecture Decisions (Updated)

This document defines the canonical engineering architecture for ClaimLens after structural hardening of:

- Clause Splitter
- Production Retriever (Titan + FAISS)
- API Retrieval Flow

This version supersedes earlier multi-stage hybrid references and reflects the current production-aligned system.

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

---

## 2.1 Global Processing

- Pages are sorted and merged in order.
- Clause detection runs across the entire document.
- Cross-page clauses are preserved.

Strict validation:

- Raises `ValueError` if:
  - Empty input list
  - No valid documents after sorting

The system never silently returns empty clause sets.

---

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

---

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

---

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

---

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

---

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

---

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

# 3. Retrieval Architecture

ClaimLens uses a single-stage semantic retrieval pipeline in production.

No lexical stage, no secondary reranking stage, and no weighted score merging are used in the active path.

---

## 3.1 Embedding + Index

Embedding model:

  amazon.titan-embed-text-v1

Vector store:

  FAISS (IndexFlatL2, 1536 dimensions)

Storage:

- Local index artifacts for runtime
- S3-backed persistence for index bundles

Purpose:

- Deterministic semantic retrieval
- Low operational cost
- Simple production deployment

---

## 3.2 Retrieval Flow

Process:

- Query embedding generated using Titan
- FAISS similarity search over clause embeddings
- Top-K clauses returned with metadata mapping

Output:

- Clause text
- Clause metadata (insurer, source PDF, page, clause_id)
- Similarity-ranked results

---

## 3.3 Operational Notes

Current production design:

- Semantic-only retrieval path
- No lexical stage
- No secondary ranking stage
- No score-fusion heuristics

Reason:

- Fewer moving parts
- Easier observability and debugging
- Better cost predictability

---

## 3.4 Retrieval Philosophy

- Structural correctness before semantics
- No LLM involvement in retrieval
- Retrieval is deterministic
- Evaluation-driven iteration

---

# 4. Evaluation Status

Legacy in-repo evaluation modules under `backend/app/evaluation` were removed in the production cleanup pass.

Offline evaluation can be run as a separate workflow, but it is not part of the active runtime path.

---

## 4.1 Evaluation Inputs

Each test case contains:

- query
- relevant_clause_ids (canonical IDs)

Evaluation is clause-ID based.

Not clause-number based.

Not text-similarity based.

---

## 4.2 Metrics Implemented

- Recall@5
- Recall@20
- Mean Reciprocal Rank (MRR)

---

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

---

## 4.4 Mean Reciprocal Rank (MRR)

For first relevant clause at rank R:

    1 / R

Examples:

- Rank 1 → 1.0
- Rank 2 → 0.5
- Rank 5 → 0.2
- Not retrieved → 0

MRR rewards early precision.

---

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

# 5. System-Level Engineering Interpretation

Empirical findings:

- Structural chunking quality directly affects Recall@20.
- Cross-encoder strongly improves Recall@5 and MRR.
- Failures typically originate in candidate generation, not reranking.
- Canonical clause IDs prevent evaluation drift.
- Deterministic parsing outperforms heuristic patching.

---

# 6. Guiding Principles (Finalized)

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