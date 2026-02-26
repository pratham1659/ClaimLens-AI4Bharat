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

## 4. Guiding Principles

- Preserve legal meaning.
- Avoid arbitrary character splitting.
- Prefer structural awareness over naive chunking.
- Keep metadata clean and intentional.
- Avoid structural noise (e.g., Table of Contents pollution) before embedding.
- Prevent structural false positives at detection stage rather than filtering them after chunk creation.

---

This document serves as the reference architecture for ClaimLens.