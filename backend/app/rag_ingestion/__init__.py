"""
Backend-integrated RAG ingestion package.

This module hosts the pre-indexed FAISS ingestion pipeline that was
previously implemented under the separate top-level `rag-system`
directory. It is now part of the backend application so that:

- RAG ingestion can be triggered directly from FastAPI endpoints
  without relying on an external package layout.
- The code lives alongside the main RAG retriever under `app/rag`.

The public entrypoint intentionally mirrors the original API:

- `run_ingestion_pipeline(root_dir: Path, use_async: bool = True) -> int`

so that callers such as the `/api/v1/policies/preindexed/ingest`
endpoint can invoke it without behavioral changes.
"""

