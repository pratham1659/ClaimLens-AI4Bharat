# ClaimLens Backend Implementation Log

This document records the backend engineering changes completed so far for ClaimLens.

## 1) FastAPI Backend Foundation

### Added
- App factory and startup wiring in `app/main.py`
- Request trace middleware in `app/core/middleware.py`
- Environment-driven config in `app/core/settings.py`
- Versioned API router in `app/api/v1/router.py`

### Endpoints scaffolded
- `GET /v1/health`
- `POST /v1/documents/upload`
- `GET /v1/documents/{document_id}`
- `POST /v1/policies/upload`
- `GET /v1/policies`
- `POST /v1/claims/analyze`
- `GET /v1/claims/{claim_id}`
- `POST /v1/evaluation/run`
- `GET /v1/evaluation/jobs/{job_id}`

## 2) API Contracts (Pydantic Schemas)

### Added schema modules
- `app/schemas/common.py`
- `app/schemas/documents.py`
- `app/schemas/policies.py`
- `app/schemas/claims.py`
- `app/schemas/evaluation.py`

### Key contract guarantees
- Typed request/response models for all v1 routes
- Confidence range guardrails (`0.0 <= confidence <= 1.0`)
- Structured citations in claim responses
- Async evaluation job tracking response model

## 3) Persistence Layer (MySQL-compatible via SQLAlchemy)

### Added
- SQLAlchemy base/session:
  - `app/db/base.py`
  - `app/db/session.py`
- DB model declarations:
  - `app/db/models.py`
- Startup table creation hook:
  - `app/db/init_db.py`

### Current tables
- `documents`
- `policies`
- `clauses`
- `claims`
- `jobs`
- `dead_letters`

## 4) Real Pipeline Wiring

### Policy indexing pipeline (asynchronous)
`policy upload -> load_policy_documents -> clause_based_splitter -> clause persistence -> FAISS build`

Implemented in:
- `app/services/policy_service.py`
- uses existing modules:
  - `app/ingestion/loader.py`
  - `app/ingestion/clause_splitter.py`
  - `app/retriever/retriever.py`

### Claim analysis pipeline
`load indexed clauses -> instantiate retriever (FAISS + BM25 + optional reranker) -> top results -> citations`

Implemented in:
- `app/services/claim_service.py`

### Evaluation pipeline
`create evaluation job -> async execute evaluator -> persist metrics/result status`

Implemented in:
- `app/services/evaluation_service.py`
- uses existing evaluator in `app/evaluation/evaluator.py`

## 5) Async Job Execution Evolution

### Phase 1
- FastAPI `BackgroundTasks` used for async processing

### Phase 2 (current)
- Replaced with durable Redis + RQ queues
- API process only enqueues; worker executes jobs
- Jobs survive API restart

Queue modules:
- `app/jobs/queue.py`
- `app/jobs/tasks.py`
- worker entrypoint: `scripts/worker.py`

## 6) RQ Reliability Hardening (Retry + Backoff + Dead Letter)

### Implemented behavior
- Retry policy on enqueue for async jobs
- Exponential backoff intervals from env (`RQ_RETRY_INTERVALS`, default `1,2,4`)
- Max retry count from env (`RQ_RETRY_MAX`, default `3`)
- On exhausted failure:
  - move to dead-letter queue (`RQ_DEAD_LETTER_QUEUE`)
  - persist dead-letter record in `dead_letters`
  - update domain status where possible (`documents`, `policies`, `jobs`)

### Worker modes
- default queue: `python scripts/worker.py`
- dead-letter queue: `python scripts/worker.py --queue dead_letter`
- both queues: `python scripts/worker.py --queue both`

## 7) Operational Config Added

In `.env.example`:
- `DATABASE_URL`
- `STORAGE_DIR`
- `FAISS_INDEX_ROOT`
- `REDIS_URL`
- `RQ_DEFAULT_QUEUE`
- `RQ_DEAD_LETTER_QUEUE`
- `RQ_RETRY_MAX`
- `RQ_RETRY_INTERVALS`

## 8) Runtime Dependencies Added

`requirements.txt` updated with backend/runtime deps, including:
- `fastapi`
- `uvicorn`
- `python-multipart`
- `PyMySQL`
- `redis`
- `rq`

## 9) Current Known Runtime Constraints

1. If Redis is unavailable, enqueue operations fail gracefully and statuses are marked failed.
2. Retrieval/evaluation heavy tasks require ML stack (notably `torch`) installed in runtime.
3. Python 3.14 emits pydantic-v1 compatibility warnings from dependency stack; app still runs but production should prefer a tested Python version for LangChain ecosystem.

## 10) Recommended Next Steps

1. Add Alembic migrations (replace create-all strategy).
2. Add centralized error envelope + exception handlers for all routes.
3. Add authenticated job introspection endpoints for dead letters and retries.
4. Add re-drive endpoint to replay dead-lettered jobs after remediation.
5. Add worker metrics (queue depth, retry count, DLQ growth) and alerts.

## 11) Admin Dead-Letter Operations

Production-grade admin APIs were added to support dead-letter operations:

- `GET /v1/admin/dead-letters` for paginated DLQ record listing
- `POST /v1/admin/dead-letters/{dead_letter_id}/redrive` to re-drive a failed item back to default queue

Implementation:
- Route: `app/api/v1/routes/admin.py`
- Service: `app/services/admin_service.py`
- Schemas: `app/schemas/admin.py`

Current re-drive behavior:
- Re-enqueues original task with retry policy
- Deletes dead-letter row after successful requeue
- Returns new queued RQ job id to caller

## 12) API Reference (Detailed)

This section captures API-level details that are implemented but were not fully enumerated above.

### Base, Versioning, and Docs

- API prefix: `/v1`
- OpenAPI: `/openapi.json`
- Swagger UI: `/docs`
- Redoc: `/redoc`

### Request Tracing

- Middleware generates/propagates `X-Trace-Id` for every request.
- If client sends `X-Trace-Id`, it is reused; otherwise a UUID is generated.
- Response always includes `X-Trace-Id` header.
- Many response bodies persist/return `trace_id` for correlation.

### Endpoint Contracts

### Endpoint Purpose Quick Guide

#### `GET /v1/health`
- Quick liveness probe for API uptime and routing.
- Use this first to verify app startup before testing other endpoints.

#### `POST /v1/documents/upload`
- Ingests a discharge summary or policy file and creates a tracked document record.
- Triggers asynchronous processing through the queue so upload remains fast.

#### `GET /v1/documents/{document_id}`
- Fetches processing state and metadata for a previously uploaded document.
- Use this to monitor queued/processed/failed transitions.

#### `POST /v1/policies/upload`
- Registers a policy PDF and starts indexing for retrieval and claim reasoning.
- The indexing pipeline runs asynchronously and updates policy status over time.

#### `GET /v1/policies`
- Lists all known policies with indexing status and clause counts.
- Helps confirm whether a policy is ready (`active`) for claim analysis.

#### `POST /v1/claims/analyze`
- Runs claim reasoning against indexed policy clauses and returns an explainable decision.
- Produces confidence, citations, and traceable rationale for downstream workflows.

#### `GET /v1/claims/{claim_id}`
- Retrieves a previously generated claim analysis result by id.
- Useful for audit trails and UI refresh without re-running analysis.

#### `POST /v1/evaluation/run`
- Starts asynchronous retrieval evaluation over benchmark query sets.
- Returns a job id immediately so long-running evaluation does not block the API.

#### `GET /v1/evaluation/jobs/{job_id}`
- Returns current state and results/errors of an evaluation job.
- Use polling from UI or scripts to detect completion and read metrics.

#### `GET /v1/admin/dead-letters`
- Lists exhausted queue jobs moved to dead-letter storage.
- Supports debugging and operational triage of failed async tasks.

#### `POST /v1/admin/dead-letters/{dead_letter_id}/redrive`
- Requeues a dead-lettered task back to the default queue for retry.
- Used after fixing root cause (e.g., dependency outage/config issue).

#### Health
- `GET /v1/health`
  - Response: `{ "status": "ok" }`

#### Documents
- `POST /v1/documents/upload` (multipart/form-data)
  - Fields:
    - `document_type`: `policy | discharge_summary`
    - `file`: binary upload
  - Success response (`DocumentStatusResponse`):
    - `document_id`, `document_type`, `filename`, `status`, `content_hash`, `trace_id`
  - Runtime behavior:
    - Content hash dedupe is applied.
    - Queue enqueue is attempted for async processing.
    - If queue enqueue fails, record status is set to `failed` and response reflects failed status.

- `GET /v1/documents/{document_id}`
  - 200: returns `DocumentStatusResponse`
  - 404: `Document not found`

#### Policies
- `POST /v1/policies/upload` (multipart/form-data)
  - Fields:
    - `insurer`, `policy_name`, `uin`, `policy_version_year`, `file`
  - Response (`PolicyUploadResponse`):
    - `policy_id`, `insurer`, `policy_name`, `uin`, `policy_version_year`, `indexing_status`, `total_clauses`, `trace_id`
  - Runtime behavior:
    - Content hash dedupe is applied.
    - Async indexing is enqueued (`loader -> splitter -> clause persist -> FAISS build`).
    - If queue enqueue fails, policy `indexing_status` is set to `failed`.

- `GET /v1/policies`
  - Response (`PolicyListResponse`):
    - `policies[]` of `PolicySummary`
  - `PolicySummary` includes:
    - `policy_id`, `insurer`, `policy_name`, `uin`, `policy_version_year`, `indexing_status`, `total_clauses`

#### Claims
- `POST /v1/claims/analyze`
  - Request (`ClaimAnalyzeRequest`):
    - `discharge_summary_id` (required)
    - `policy_id` (required)
    - `claim_amount` (optional)
    - `notes` (optional, used as retrieval query if provided)
  - Response (`ClaimAnalyzeResponse`):
    - `claim_id`, `decision`, `confidence`, `explanation`, `citations[]`, `trace_id`
  - `decision` enum:
    - `likely_approved | likely_denied | uncertain`
  - Confidence and citation constraints:
    - `confidence` in `[0.0, 1.0]`
    - `citations[].relevance_score` in `[0.0, 1.0]`
  - Runtime behavior:
    - Uses indexed clauses and retriever path (FAISS + BM25 + reranker when available).
    - Gracefully degrades to `uncertain` when policy/discharge is missing or pipeline is unavailable.

- `GET /v1/claims/{claim_id}`
  - 200: returns `ClaimAnalyzeResponse`
  - 404: `Claim not found`

#### Evaluation
- `POST /v1/evaluation/run`
  - Request (`EvaluationRunRequest`):
    - `insurer_scope` (default `both`)
    - `use_reranker` (default `true`)
    - `dense_top_k` (default `40`)
  - Response (`EvaluationRunResponse`):
    - `status`, `job_id`, `metrics` (nullable), `trace_id`, `message`
  - Runtime behavior:
    - Creates persistent evaluation job row.
    - Enqueues worker task for async execution.
    - If enqueue fails, returns failed status/message and updates job status accordingly.

- `GET /v1/evaluation/jobs/{job_id}`
  - 200: returns `EvaluationJobStatusResponse`
    - `job_id`, `status`, `result` (nullable), `error_message` (nullable)
  - 404: `Evaluation job not found`

#### Admin Dead-Letter Operations
- `GET /v1/admin/dead-letters`
  - Query params:
    - `limit` (default `50`, min `1`, max `200`)
    - `offset` (default `0`, min `0`)
  - Response (`DeadLetterListResponse`):
    - `items[]`, `total`
  - Item fields (`DeadLetterItem`):
    - `id`, `rq_job_id`, `task_name`, `origin_queue`, `error_type`, `error_message`, `moved_to_queue`, `created_at`

- `POST /v1/admin/dead-letters/{dead_letter_id}/redrive`
  - 200: `DeadLetterRedriveResponse` with `status=requeued`, `new_job_id`
  - 404: dead-letter id not found
  - 500: re-drive attempt failed (queue/task/payload issue)
  - Runtime behavior:
    - Re-enqueues original task with standard retry/backoff policy.
    - Deletes dead-letter DB record on successful requeue.

### Error Surface (Current)

- Route-level `HTTPException` errors return FastAPI default shape: `{ "detail": ... }`.
- Validation errors use FastAPI/Pydantic default 422 format.
- Domain-specific error envelope model exists (`ErrorResponse`) but is not yet globally enforced by exception handlers.

### Async and Queue Semantics

- API endpoints enqueue, workers execute.
- Default queue settings are env-driven.
- Retry/backoff and DLQ policy are centralized in `app/jobs/queue.py`.
- Exhausted failures are persisted to `dead_letters` and optionally reflected in domain status (`documents`, `policies`, `jobs`).

#### Terminal 1 — MySQL (create DB once)

mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS claimlens;"
#### Terminal 2 — Redis

redis-server
#### Terminal 3 — API server

cd /home/naino/Desktop/personal_projects/ClaimLens-AI4Bharat
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp [.env.example](http://_vscodecontentref_/1) .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
#### Terminal 4 — Queue worker (default jobs)

cd /home/naino/Desktop/personal_projects/ClaimLens-AI4Bharat
source .venv/bin/activate
python scripts/worker.py
#### Terminal 5 — Dead-letter worker (optional)

cd /home/naino/Desktop/personal_projects/ClaimLens-AI4Bharat
source .venv/bin/activate
python [worker.py](http://_vscodecontentref_/2) --queue dead_letter
Open Swagger

xdg-open http://127.0.0.1:8000/docs
Quick check

curl -s http://127.0.0.1:8000/v1/health
