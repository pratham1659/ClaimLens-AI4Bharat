import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.loader import load_policy_documents
from app.ingestion.clause_splitter import clause_based_splitter
from app.retriever.embeddings import load_embedding_model
from app.retriever.vector_store import build_or_load_vectorstore
from app.retriever.reranker import ClauseReranker


def print_clause(clause, index):
    print(f"\n{'='*80}")
    print(f"Rank: {index}")
    print(f"Section: {clause.metadata.get('section')}")
    print(f"Clause Number: {clause.metadata.get('clause_number')}")
    print(f"Clause Title: {clause.metadata.get('clause_title')}")
    print(f"Start Page: {clause.metadata.get('start_page')}")
    print("\nPreview:")
    print(clause.page_content[:500])
    print(f"\n{'='*80}")


if __name__ == "__main__":

    query = "What is the waiting period for pre-existing diseases?"

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

    docs = docs_icici + docs_niva

    print("Splitting into clauses...")
    clause_docs = clause_based_splitter(docs)

    print(f"Total Clauses: {len(clause_docs)}")

    # print("\nSearching for 'cataract' in clauses...\n")
    # found = False
    # for clause in clause_docs:
    #     if "cataract" in clause.page_content.lower():
    #         found = True
    #         print("FOUND CATARACT CLAUSE:")
    #         print(clause.page_content[:500])
    #         print("-" * 80)

    # if not found:
    #     print("No clause contains the word 'cataract'")

    print("\nLoading embedding model...")
    embedding_model = load_embedding_model()

    print("Building or loading FAISS index...")
    vectorstore = build_or_load_vectorstore(
        clause_docs,
        embedding_model,
        index_path="faiss_claimlens_index"
    )

    print("\nRunning Dense Retrieval (Top 20)...")
    dense_retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 40},
    )

    dense_results = dense_retriever.invoke(query)

    print(f"\nDense Retrieved Clauses: {len(dense_results)}")

    print(f"Query: {query}")

    for i, clause in enumerate(dense_results, start=1):
        print_clause(clause, i)

    print("\nLoading reranker...")
    reranker = ClauseReranker()

    print("\nRunning Reranking (Top 5)...")
    reranked_results = reranker.rerank(
        query,
        dense_results,
        top_k=5
    )

    print(f"\nFinal Reranked Clauses: {len(reranked_results)}")
    print(f"Query: {query}")

    for i, clause in enumerate(reranked_results, start=1):
        print_clause(clause, i)