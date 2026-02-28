# ClaimLens

AI-powered RAG system for insurance policy analysis.

Uses hybrid retrieval (FAISS + BM25) with cross-encoder reranking to extract and reason over insurance policy clauses.

## Backend API (FastAPI)

Run from project root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Before running, ensure MySQL exists and is reachable by `DATABASE_URL` in `.env`.
Example database creation:

```sql
CREATE DATABASE claimlens;
```

Also ensure Redis is running for async job queue:

```bash
redis-server
```

Tables are created automatically at API startup.

Run the queue worker in a separate terminal:

```bash
source .venv/bin/activate
python scripts/worker.py
```

Optional worker modes:

```bash
# Process dead-letter queue only
python scripts/worker.py --queue dead_letter

# Process both queues
python scripts/worker.py --queue both
```

API docs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

Initial endpoints:

- `GET /v1/health`
- `POST /v1/documents/upload`
- `GET /v1/documents/{document_id}`
- `POST /v1/policies/upload`
- `GET /v1/policies`
- `POST /v1/claims/analyze`
- `GET /v1/claims/{claim_id}`
- `POST /v1/evaluation/run`
- `GET /v1/evaluation/jobs/{job_id}`
- `GET /v1/admin/dead-letters`
- `POST /v1/admin/dead-letters/{dead_letter_id}/redrive`

Upload and evaluation pipelines are now dispatched to Redis-backed RQ jobs (durable across API restarts).

RQ reliability hardening:

- Automatic retries enabled for queued jobs
- Exponential backoff via `RQ_RETRY_INTERVALS` (default `1,2,4` seconds)
- Exhausted failures are moved to dead-letter queue `RQ_DEAD_LETTER_QUEUE`
- Dead-letter events are persisted in database table `dead_letters`
