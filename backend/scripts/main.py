#!/usr/bin/env python3
"""
ClaimLens Clause Extraction Demo
================================

Basic demonstration script that shows the clause-based splitting pipeline:
1. Loads a policy PDF document
2. Splits into semantic clauses using pattern-based extraction
3. Displays extracted clauses with metadata

This script is useful for:
- Understanding how clause splitting works
- Debugging clause extraction issues
- Inspecting clause boundaries and metadata
- Identifying potential TOC/index leftover content

Usage:
    cd backend && python3 scripts/main.py
    # or
    ./scripts/run_rag.sh main

Author: ClaimLens Team
"""

from app.ingestion.loader import load_policy_documents
from app.ingestion.clause_splitter import clause_based_splitter
import sys
import os

# Set up path for imports BEFORE importing app modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

# Configuration from environment
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(PROJECT_ROOT, "data"))

# Now import app modules


def print_banner():
    """Print script banner."""
    print("\n" + "=" * 70)
    print("  ClaimLens RAG - Clause Extraction Demo")
    print("=" * 70 + "\n")


def print_clause(clause, index: int):
    """
    Pretty-print an extracted clause.

    Args:
        clause: LangChain Document with metadata
        index: Clause index (0-indexed)
    """
    print("=" * 70)
    print(f"  Clause Index: {index}")
    print(f"  Section: {clause.metadata.get('section', 'N/A')}")
    print(f"  Clause Number: {clause.metadata.get('clause_number', 'N/A')}")
    print(f"  Clause Title: {clause.metadata.get('clause_title', 'N/A')}")
    print(f"  Start Page: {clause.metadata.get('start_page', 'N/A')}")
    print(f"  Content Length: {len(clause.page_content)} chars")
    print(f"\n  Preview:")
    # Show first 400 chars with proper indentation
    preview = clause.page_content[:400].replace('\n', '\n    ')
    print(f"    {preview}")
    if len(clause.page_content) > 400:
        print(f"    ...")
    print("=" * 70 + "\n")


def analyze_clauses(clauses: list):
    """
    Analyze extracted clauses for quality issues.

    Args:
        clauses: List of extracted clause documents
    """
    print("\n" + "-" * 70)
    print("  CLAUSE ANALYSIS")
    print("-" * 70)

    # Count by section
    sections = {}
    for clause in clauses:
        section = clause.metadata.get('section', 'Unknown')
        sections[section] = sections.get(section, 0) + 1

    print(f"\n  Clauses by Section:")
    for section, count in sorted(sections.items()):
        print(f"    {section}: {count}")

    # Identify potential TOC leftovers (very short clauses)
    short_clauses = [c for c in clauses if len(c.page_content.strip()) < 50]
    print(f"\n  Very Short Clauses (<50 chars): {len(short_clauses)}")

    # Identify single-line clauses (potential TOC entries)
    single_line = [c for c in clauses if len(c.page_content.splitlines()) == 1]
    print(f"  Single-line Clauses (potential TOC): {len(single_line)}")

    # Identify very long clauses
    long_clauses = [c for c in clauses if len(c.page_content) > 5000]
    print(f"  Very Long Clauses (>5000 chars): {len(long_clauses)}")

    # Content length statistics
    lengths = [len(c.page_content) for c in clauses]
    if lengths:
        avg_len = sum(lengths) / len(lengths)
        min_len = min(lengths)
        max_len = max(lengths)
        print(f"\n  Content Length Stats:")
        print(f"    Average: {avg_len:.0f} chars")
        print(f"    Min: {min_len} chars")
        print(f"    Max: {max_len} chars")

    print("-" * 70 + "\n")


def main():
    """Main entry point for clause extraction demo."""
    print_banner()

    # Load ICICI policy document
    pdf_path = os.path.join(DATA_DIR, "icici_complete_health.pdf")

    if not os.path.exists(pdf_path):
        print(f"Error: Policy document not found at {pdf_path}")
        print("\nPlease ensure the ICICI Complete Health policy PDF is in the data/ directory.")
        sys.exit(1)

    print(f"Loading: {pdf_path}")
    docs = load_policy_documents(
        pdf_path=pdf_path,
        insurer="ICICI Lombard",
        policy_name="Complete Health Insurance",
        uin="ICIHLIP25035V082425",
        policy_version_year=2025
    )
    print(f"✓ Loaded {len(docs)} pages\n")

    # Split into clauses
    print("Splitting into clauses...")
    clause_docs = clause_based_splitter(docs)
    print(f"✓ Extracted {len(clause_docs)} clauses\n")

    # Display first 10 clauses
    print("=" * 70)
    print("  SAMPLE CLAUSES (First 10)")
    print("=" * 70 + "\n")

    for i, clause in enumerate(clause_docs[:10]):
        print_clause(clause, i)

    if len(clause_docs) > 10:
        print(f"  ... and {len(clause_docs) - 10} more clauses\n")

    # Analyze clauses for quality
    analyze_clauses(clause_docs)

    print("✓ Demo complete")


if __name__ == "__main__":
    main()
