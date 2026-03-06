# ClaimLens Project Walkthrough (V2)

This document consolidates the latest implementation state after migration to the production semantic RAG path.

---

## 1) What Changed (V2)

- Migrated retrieval strategy to semantic-first production flow centered on Titan embeddings + FAISS.
- Introduced and hardened the standalone `rag-system` pipeline for ingestion, indexing, retrieval, and API serving.
- Removed legacy/experimental backend retrieval and evaluation modules no longer used in runtime.
- Kept deterministic clause splitting logic unchanged in `rag-system/ingestion/clause_splitter.py`.
- Kept `rag-system/retrieval/retriever.py` retrieval logic intact while cleaning legacy terminology in docs/comments.

---

## 2) Current High-Level Architecture

### Runtime Components

1. **Policy Documents**
   - Source PDFs in `rag-system/documents/policies/`.

2. **Ingestion + Clause Extraction**
   - `rag-system/ingestion/pdf_loader.py`
   - `rag-system/ingestion/clause_splitter.py`

3. **Embedding Service**
   - `rag-system/ingestion/embedding_service.py`
  - Uses Amazon Titan embedding model (`amazon.titan-embed-text-v2:0`).

4. **Vector Store + Metadata**
   - `rag-system/vectorstore/faiss_store.py`
   - Persists to:
     - `rag-system/indexes/faiss.index`
     - `rag-system/indexes/metadata.pkl`

5. **S3 Index Sync**
   - `rag-system/storage/s3_client.py`
   - Upload/download bundle under `indexes/` keys in S3.

6. **Query Retrieval API**
   - `rag-system/retrieval/retriever.py`
   - `rag-system/api/server.py`
   - Endpoints:
     - `GET /health`
     - `GET /search?query=...&k=...`
     - `POST /ingest`

---

## 3) End-to-End Data Flow

### Ingestion Flow

1. Place PDFs in `rag-system/documents/policies/`.
2. Run ingestion (`POST /ingest` or direct pipeline call).
3. Pages are extracted from PDFs.
4. Clauses are split deterministically.
5. Clause text is embedded with Titan.
6. Embeddings + metadata are written to FAISS local files.
7. FAISS bundle is uploaded to S3.
8. Source policy PDFs are synced to S3 under `documents/policies/`.

### Retrieval Flow

1. `GET /search` receives query.
2. Query is embedded with Titan.
3. FAISS similarity search runs (`IndexFlatL2`, dimension `1536`).
4. Metadata is mapped back to clause payload.
5. Ranked results are returned (`rank`, `score_l2`, `clause_id`, `text`, `page`, `source_pdf`).

---

## 4) Repository State After Cleanup

### Active Production Path

- `rag-system/**` is the primary semantic retrieval production path.
- `backend/app/rag/**` remains for backend integration where applicable.

### Removed Legacy Modules

- Deleted old retriever modules:
  - `backend/app/retriever/retriever.py`
  - `backend/app/retriever/reranker.py`
  - `backend/app/retriever/vector_store.py`
- Deleted legacy evaluation package:
  - `backend/app/evaluation/`
- Deleted old scripts in previous cleanup pass:
  - `backend/scripts/test_retrieval.py`
  - `backend/scripts/run_evaluation.py`
  - `backend/scripts/build_faiss_index.py`

### Intentionally Kept

- `backend/app/retriever/embeddings.py` is retained because `backend/app/rag/embeddings.py` and `backend/app/rag/retriever.py` still import embedding adapters from it.

---

## 5) API Quick Verification

From repo root:

```bash
cd rag-system
pip install -r requirements.txt
uvicorn api.server:app --host 0.0.0.0 --port 8001
```

Test endpoints:

```bash
curl http://localhost:8001/health
curl "http://localhost:8001/search?query=waiting%20period&k=5"
curl -X POST http://localhost:8001/ingest
```

---

## 6) Operational Notes

- `rag-system` currently uses `us-east-1` and S3 bucket defaults (`claimlens-faiss-index-1`) in code.
- Ensure EC2 IAM role (or env credentials) has:
  - `bedrock:InvokeModel`
  - `s3:GetObject`
  - `s3:PutObject`
  - `s3:DeleteObject`
  - `s3:HeadBucket`
  - `s3:ListBucket`
- Keep local `indexes/` writable by the service user.

---

## 7) Backend Runtime Safeguards (Current)

- **Storage diagnostics endpoint**: `GET /api/v1/documents/storage-health`
  - validates bucket access with `head/put/get/delete` checks.
- **Policy processing fallback**:
  - if Bedrock embedding fails, policy processing falls back to local embeddings, then mock embeddings.
- **Policy-chat fallback answers**:
  - fallback responses are now query-sensitive and user-friendly, with concise answer-first phrasing and clause-grounded snippets.
- **Analysis robustness**:
  - analysis scoring includes retrieval fallback from stored embeddings when primary retrieval returns no clauses.

---

## 8) Frontend Behavior Updates

- Claim detail page now auto re-analyzes once on page load when required documents are processed, ensuring fresh approval scores.

---

## 9) Recommended Next Hardening (Optional)

- Externalize bucket/region/model IDs via env variables for all `rag-system` modules.
- Add health checks for S3 bundle presence and Bedrock reachability.
- Add CI smoke test for `/health` and `/search` on a small test index.
