import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.loader import load_policy_documents
from app.ingestion.clause_splitter import health_policy_splitter
from app.retrieval.embeddings import load_embedding_model
from app.retrieval.retriever import ClaimLensRetriever

def print_clause(clause, index):
    print(f"\n{'='*80}")
    print(f"Rank: {index}")
    print(f"Insurer: {clause.metadata.get('insurer')}")
    print(f"Section: {clause.metadata.get('section')}")
    print(f"Clause Number: {clause.metadata.get('clause_number')}")
    print(f"Clause Title: {clause.metadata.get('clause_title')}")
    print(f"Clause ID: {clause.metadata.get('clause_id')}")
    print(f"Start Page: {clause.metadata.get('start_page')}")
    print("\nPreview:")
    print(clause.page_content[:500])
    print(f"\n{'='*80}")

if __name__ == "__main__":

    queries = [
        'What medical expenses are covered during hospitalization?'
        # 'Information about IVF'
        # "Is cosmetic surgery covered?",
        # "Is IVF covered?",
        # "What is grace period?",
        # "What are ICU charges?",
        # "What is pre-existing disease?"
    ]

    print("\nLoading documents...")

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

    print(f"Total Clauses: {len(clause_docs)}")


    print("\nLoading embedding model...")
    embedding_model = load_embedding_model()

    print("Building Hybrid Retriever...")
    retriever = ClaimLensRetriever(
        clause_documents=clause_docs,
        embedding_model=embedding_model,
        index_path="faiss_claimlens_index",
        dense_top_k=40,
        use_reranker=False
    )

    for query in queries:

        print("\n" + "#" * 100)
        print(f"QUERY: {query}")
        print("#" * 100)

        print("\nRunning Hybrid Retrieval (Dense + BM25 + Reranker)...")

        retrieved_docs = retriever.retrieve(query)

        top_results = retrieved_docs[:5]

        print(f"\nFinal Retrieved Clauses (Top 5): {len(top_results)}")

        for i, clause in enumerate(top_results, start=1):
            print_clause(clause, i)