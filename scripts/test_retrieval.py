import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain_groq import ChatGroq
from dotenv import load_dotenv

from app.ingestion.loader import load_policy_documents
from app.ingestion.clause_splitter import health_policy_splitter
from app.retrieval.embeddings import load_embedding_model
from app.retrieval.retriever import ClaimLensRetriever
from app.reasoning.query_builder import ClaimLensQueryBuilder

load_dotenv()


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
        """ Hospital Discharge Summary
        Patient Information
        Patient Name: Rajesh Kumar
        Age / Gender: 52 / Male
        Hospital: Apollo Hospital, Delhi
        Admission Date: 12 Feb 2026
        Discharge Date: 15 Feb 2026
        Chief Complaint
        Patient presented with severe chest pain, sweating, and shortness of breath for the past 2 hours.
        Clinical Findings
        ECG showed ST elevation. Troponin levels were elevated.
        Diagnosis: Acute ST Elevation Myocardial Infarction (STEMI).
        Treatment Provided
        Emergency Coronary Angiography.
        Percutaneous Coronary Intervention (PCI).
        Drug-Eluting Stent placement in the Left Anterior Descending artery.
        Hospital Course
        Patient was admitted to the Cardiac ICU and stabilized with medication and intervention.
        Post-procedure recovery was uneventful.
        Discharge Medications
        Aspirin, Clopidogrel, Atorvastatin, Metoprolol.
        Discharge Condition
        Stable. Follow-up with cardiology in 7 days.
        Final Diagnosis
        Acute Myocardial Infarction treated with PCI and stent placement."""
    ]

    print("\nLoading documents...")

    docs_icici = load_policy_documents(
        pdf_path="data/policy_icici_complete_health.pdf",
        insurer="ICICI Lombard",
        policy_name="Complete Health Insurance",
        uin="ICIHLIP25035V082425",
        policy_version_year=2025
    )

    docs_niva = load_policy_documents(
        pdf_path="data/policy_niva_rise.pdf",
        insurer="Niva Bupa",
        policy_name="Rise Policy",
        uin="NIVHLIPXXXX",
        policy_version_year=2025
    )

    docs_hdfc = load_policy_documents(
        pdf_path="data/Policy_HDFC optima.pdf",
        insurer="HDFC",
        policy_name="Optima",
        uin="NIVHLIPXXXX",
        policy_version_year=2025
    )

    docs_care = load_policy_documents(
        pdf_path="data/care_policy.pdf",
        insurer="Care",
        policy_name="Care Policy",
        uin="NIVHLIPXXXX",
        policy_version_year=2025
    )

    def choose_docs(choice: str):

        mapping = {
            "icici": docs_icici,
            "niva": docs_niva,
            "hdfc": docs_hdfc,
            "care": docs_care,
            "all": docs_icici + docs_niva + docs_hdfc + docs_care
        }

        try:
            return mapping[choice.lower()]
        except KeyError:
            raise ValueError("Invalid option. Choose: icici, niva, hdfc, care, or all.")

    docs = choose_docs("care")

    print("Splitting into clauses...")
    clause_docs = health_policy_splitter(docs)

    print(f"Total Clauses: {len(clause_docs)}")

    print("\nLoading embedding model...")
    embedding_model = load_embedding_model()

    print("\nInitializing Query Builder...")

    query_llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0
    )

    query_builder = ClaimLensQueryBuilder(query_llm)

    print("\nBuilding Hybrid Retriever...")

    retriever = ClaimLensRetriever(
        clause_documents=clause_docs,
        embedding_model=embedding_model,
        index_path="faiss_claimlens_index",
        dense_top_k=40,
        use_reranker=False
    )

    for query in queries:

        print("\n" + "#" * 100)
        print("ORIGINAL QUERY:")
        print(query)
        print("#" * 100)

        print("\nBuilding retrieval query using Query Builder...")

        retrieval_query = query_builder.build_query(query)

        print("\nREWRITTEN RETRIEVAL QUERY:")
        print(retrieval_query)

        print("\nRunning Hybrid Retrieval (Dense + BM25)...")

        retrieved_docs = retriever.retrieve(retrieval_query)

        top_results = retrieved_docs[:5]

        print(f"\nFinal Retrieved Clauses (Top 5): {len(top_results)}")

        for i, clause in enumerate(top_results, start=1):
            print_clause(clause, i)