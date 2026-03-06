from pathlib import Path
from typing import List

from fastapi import FastAPI, Query
from pydantic import BaseModel

from ingestion.pdf_loader import run_ingestion_pipeline
from retrieval.retriever import Retriever


class SearchResult(BaseModel):
    rank: int
    score_l2: float
    insurer: str | None = None
    clause_id: str | None = None
    text: str | None = None
    page: int | None = None
    source_pdf: str | None = None


app = FastAPI(title="ClaimLens RAG API")
retriever = Retriever(root_dir=Path(__file__).resolve().parents[1])


@app.on_event("startup")
def startup_event():
    retriever.initialize()


@app.get("/health")
def health():
    return {"status": "ok", "index_size": retriever.faiss_store.ntotal}


@app.get("/search", response_model=List[SearchResult])
def search(query: str = Query(..., min_length=2), k: int = Query(5, ge=1, le=20)):
    return retriever.search(query=query, k=k)


@app.post("/ingest")
def ingest(use_async: bool = True):
    indexed = run_ingestion_pipeline(root_dir=Path(__file__).resolve().parents[1], use_async=use_async)
    retriever.initialize()
    return {"indexed_clauses": indexed, "index_size": retriever.faiss_store.ntotal}
