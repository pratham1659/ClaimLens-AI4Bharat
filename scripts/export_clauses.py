import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.loader import load_policy_documents
from app.ingestion.clause_splitter import health_policy_splitter


def export_clauses_to_json(output_path="all_clauses.json"):

    print("Loading documents...")

    docs_icici = load_policy_documents(
        pdf_path="data/icici_complete_health.pdf",
        insurer="ICICI Lombard",
        policy_name="Complete Health Insurance",
        uin="ICIHLIP25035V082425",
        policy_version_year=2025
    )

    docs_niva = load_policy_documents(
        pdf_path="data/niva_rise.pdf",
        insurer="Niva Bupa",
        policy_name="Rise Policy",
        uin="NIVHLIPXXXX",
        policy_version_year=2025
    )

    docs_hdfc = load_policy_documents(
        pdf_path="data/HDFC optima-secure-revision-pw.pdf",
        insurer="HDFC",
        policy_name="Optima",
        uin="NIVHLIPXXXX",
        policy_version_year=2025
    )

    def choose_docs(choice: str):
        mapping = {
            "icici": docs_icici,
            "niva": docs_niva,
            "hdfc": docs_hdfc,
            "all": docs_icici + docs_niva + docs_hdfc
        }

        try:
            return mapping[choice.lower()]
        except KeyError:
            raise ValueError("Invalid option. Choose: icici, niva, or both.")
    
    docs = choose_docs("hdfc")

    print("Splitting into clauses...")
    clause_docs = health_policy_splitter(docs)

    print(f"Total clauses: {len(clause_docs)}")

    export_data = []

    for clause in clause_docs:
        export_data.append({
            "clause_id": clause.metadata.get("clause_id"),
            "insurer": clause.metadata.get("insurer"),
            "section": clause.metadata.get("section"),
            "clause_number": clause.metadata.get("clause_number"),
            "clause_title": clause.metadata.get("clause_title"),
            "start_page": clause.metadata.get("start_page"),
            "content": clause.page_content
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    print(f"Clauses exported to {output_path}")


if __name__ == "__main__":
    export_clauses_to_json()