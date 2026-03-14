#!/usr/bin/env python3
"""
ClaimLens Clause Export Script
==============================

Exports all extracted policy clauses to a JSON file for inspection,
debugging, or integration with other systems.

Output Format:
    [
        {
            "clause_id": "ICICI_S1_C1",
            "insurer": "ICICI Lombard",
            "section": "Section 1: Coverage",
            "clause_number": "1.1",
            "clause_title": "Hospitalization",
            "start_page": 5,
            "content": "Full clause text..."
        },
        ...
    ]

Output File:
    storage/clauses/all_clauses.json (default)
    
Usage:
    cd backend && python3 scripts/export_clauses.py
    cd backend && python3 scripts/export_clauses.py --output=/path/to/output.json
    # or
    ./scripts/run_rag.sh export

Author: ClaimLens Team
"""

from app.ingestion.loader import load_policy_documents
from app.ingestion.clause_splitter import clause_based_splitter
import sys
import os
import json
import argparse
from datetime import datetime

# Set up path for imports BEFORE importing app modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

# Configuration from environment
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
STORAGE_DIR = os.environ.get(
    "STORAGE_DIR", os.path.join(PROJECT_ROOT, "storage"))
CLAUSES_DIR = os.path.join(STORAGE_DIR, "clauses")

# Now import app modules


def print_banner():
    """Print script banner."""
    print("\n" + "=" * 70)
    print("  ClaimLens RAG - Clause Export")
    print("=" * 70 + "\n")


def load_documents():
    """
    Load policy documents from PDF files.

    Returns:
        list: Combined list of documents from all policies
    """
    all_docs = []

    # ICICI Complete Health Insurance
    icici_path = os.path.join(DATA_DIR, "icici_complete_health.pdf")
    if os.path.exists(icici_path):
        print("Loading ICICI Complete Health Insurance...")
        docs = load_policy_documents(
            pdf_path=icici_path,
            insurer="ICICI Lombard",
            policy_name="Complete Health Insurance",
            uin="ICIHLIP25035V082425",
            policy_version_year=2025
        )
        all_docs.extend(docs)
        print(f"  ✓ Loaded {len(docs)} pages")

    # Niva Bupa Rise
    niva_path = os.path.join(DATA_DIR, "niva_rise.pdf")
    if os.path.exists(niva_path):
        print("Loading Niva Bupa Rise Policy...")
        docs = load_policy_documents(
            pdf_path=niva_path,
            insurer="Niva Bupa",
            policy_name="Rise Policy",
            uin="NIVHLIPXXXX",
            policy_version_year=2025
        )
        all_docs.extend(docs)
        print(f"  ✓ Loaded {len(docs)} pages")

    return all_docs


def export_clauses_to_json(clauses: list, output_path: str):
    """
    Export clauses to JSON file.

    Args:
        clauses: List of LangChain Document objects
        output_path: Path to output JSON file
    """
    export_data = {
        "metadata": {
            "exported_at": datetime.utcnow().isoformat(),
            "total_clauses": len(clauses),
            "source": "ClaimLens RAG Pipeline"
        },
        "clauses": []
    }

    # Group clauses by insurer for statistics
    insurers = {}

    for clause in clauses:
        clause_data = {
            "clause_id": clause.metadata.get("clause_id", ""),
            "insurer": clause.metadata.get("insurer", ""),
            "policy_name": clause.metadata.get("policy_name", ""),
            "section": clause.metadata.get("section", ""),
            "clause_number": clause.metadata.get("clause_number", ""),
            "clause_title": clause.metadata.get("clause_title", ""),
            "start_page": clause.metadata.get("start_page", 0),
            "content_length": len(clause.page_content),
            "content": clause.page_content
        }
        export_data["clauses"].append(clause_data)

        # Track insurer statistics
        insurer = clause.metadata.get("insurer", "Unknown")
        insurers[insurer] = insurers.get(insurer, 0) + 1

    # Add insurer breakdown to metadata
    export_data["metadata"]["breakdown_by_insurer"] = insurers

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    return insurers


def main():
    """Main entry point for clause export."""
    print_banner()

    # Parse arguments
    parser = argparse.ArgumentParser(description="Export clauses to JSON")
    parser.add_argument(
        "--output", "-o",
        default=os.path.join(CLAUSES_DIR, "all_clauses.json"),
        help="Output file path"
    )
    args = parser.parse_args()

    output_path = args.output

    # Load documents
    print("Loading policy documents...")
    docs = load_documents()

    if not docs:
        print("Error: No documents loaded!")
        sys.exit(1)

    print(f"\nTotal pages loaded: {len(docs)}")

    # Split into clauses
    print("\nSplitting into clauses...")
    clause_docs = clause_based_splitter(docs)
    print(f"Total clauses extracted: {len(clause_docs)}")

    # Export to JSON
    print(f"\nExporting to {output_path}...")
    insurers = export_clauses_to_json(clause_docs, output_path)

    # Print summary
    print("\n" + "=" * 50)
    print("  EXPORT SUMMARY")
    print("=" * 50)
    print(f"  Total Clauses: {len(clause_docs)}")
    print(f"  Output File:   {output_path}")
    print(f"\n  Breakdown by Insurer:")
    for insurer, count in insurers.items():
        print(f"    - {insurer}: {count} clauses")
    print("=" * 50)

    # File size
    file_size = os.path.getsize(output_path)
    if file_size > 1024 * 1024:
        size_str = f"{file_size / (1024 * 1024):.2f} MB"
    elif file_size > 1024:
        size_str = f"{file_size / 1024:.2f} KB"
    else:
        size_str = f"{file_size} bytes"

    print(f"\n✓ Export complete ({size_str})")


if __name__ == "__main__":
    main()
