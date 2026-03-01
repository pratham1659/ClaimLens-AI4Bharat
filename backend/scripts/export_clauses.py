#!/usr/bin/env python3
"""
ClaimLens - Clause Export Script

Exports all clause-level documents into structured JSON.

Environment Variables:
    DATA_DIR: Path to data folder (default: ./data)
    OUTPUT_PATH: Output JSON file path (default: ./exports/all_clauses.json)
    POLICY: icici / niva / both (default: icici)

Usage:
    python scripts/export_clauses.py
"""

import os
import sys
import json
from pathlib import Path

from app.rag_main.ingestion.loader import load_policy_documents
from app.rag_main.ingestion.clause_splitter import health_policy_splitter


BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", BASE_DIR / "exports" / "all_clauses.json"))
POLICY = os.environ.get("POLICY", "icici").lower()

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def print_banner():
    print("\n" + "=" * 60)
    print(" ClaimLens - Clause Export")
    print("=" * 60)
    print(f" Policy:       {POLICY}")
    print(f" Output Path:  {OUTPUT_PATH}")
    print("=" * 60 + "\n")


def load_documents():
    documents = {}

    icici_path = DATA_DIR / "icici_complete_health.pdf"
    niva_path = DATA_DIR / "niva_rise.pdf"

    if icici_path.exists():
        documents["icici"] = load_policy_documents(
            pdf_path=str(icici_path),
            insurer="ICICI Lombard",
            policy_name="Complete Health Insurance",
            uin="ICIHLIP25035V082425",
            policy_version_year=2025,
        )

    if niva_path.exists():
        documents["niva"] = load_policy_documents(
            pdf_path=str(niva_path),
            insurer="Niva Bupa",
            policy_name="Rise Policy",
            uin="NIVHLIPXXXX",
            policy_version_year=2025,
        )

    if not documents:
        print("No policy PDFs found.")
        sys.exit(1)

    return documents


def select_documents(documents: dict):
    if POLICY == "icici":
        return documents.get("icici", [])
    elif POLICY == "niva":
        return documents.get("niva", [])
    elif POLICY == "both":
        return documents.get("icici", []) + documents.get("niva", [])
    else:
        raise ValueError("POLICY must be: icici, niva, both")


def export_clauses():

    print_banner()

    print("Loading policy documents...")
    documents = load_documents()

    docs = select_documents(documents)
    print(f"✓ Total pages loaded: {len(docs)}")

    print("\nSplitting into clauses...")
    clause_docs = health_policy_splitter(docs)
    print(f"✓ Total clauses extracted: {len(clause_docs)}")

    export_data = []

    for clause in clause_docs:
        export_data.append({
            "clause_id": clause.metadata.get("clause_id"),
            "insurer": clause.metadata.get("insurer"),
            "section": clause.metadata.get("section"),
            "clause_number": clause.metadata.get("clause_number"),
            "clause_title": clause.metadata.get("clause_title"),
            "start_page": clause.metadata.get("start_page"),
            "content": clause.page_content,
        })

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Clauses exported to: {OUTPUT_PATH}\n")


if __name__ == "__main__":
    export_clauses()