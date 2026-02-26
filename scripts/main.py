from app.ingestion.loader import load_policy
from app.ingestion.clause_splitter import clause_based_splitter

if __name__ == "__main__":

    docs = load_policy(
        pdf_path="data/icici_complete_health.pdf",
        insurer="ICICI Lombard",
        policy_name="Complete Health Insurance",
        uin="ICIHLIP25035V082425",
        policy_version_year=2025
    )


    clause_docs = clause_based_splitter(docs)

    print(f"Total Number of Clauses Extracted: {len(clause_docs)}\n")

    for i, clause in enumerate(clause_docs):
        print("=" * 80)
        print(f"Clause Index: {i}")
        print(f"Section: {clause.metadata.get('section')}")
        print(f"Clause Number: {clause.metadata.get('clause_number')}")
        print(f"Clause Title: {clause.metadata.get('clause_title')}")
        print(f"Start Page: {clause.metadata.get('start_page')}")
        print(f"\nPreview:\n {clause.page_content[:400]}")
        print("=" * 80)

    toc_suspects = [
        c for c in clause_docs
        if len(c.page_content.splitlines()) == 1
    ]

    print("\nPotential TOC Leftovers (Single-line Clauses):", len(toc_suspects))