from app.ingestion.loader import load_policy_documents
from app.ingestion.clause_splitter import clause_based_splitter
from app.retriever.embeddings import load_embedding_model
from app.retriever.retriever import ClaimLensRetriever
from app.evaluation.evaluator import RetrievalEvaluator

import json


print("Loading Documents...")

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

def choose_docs(choice:str):
    mapping = {
        "niva": docs_niva,
        "icici": docs_icici,
        "both": docs_icici + docs_niva
    }

    try:
        return mapping[choice.lower()]
    except KeyError:
            raise ValueError("Invalid option. Choose: icici, niva, or both.")

docs = choose_docs("both")


print("Splitting Into Clauses...")
clauses = clause_based_splitter(docs)


print("Loading Embedding Model...")
embedding_model = load_embedding_model()


print("Building Retriever...")
retriever = ClaimLensRetriever(
    clause_documents=clauses,
    embedding_model=embedding_model,
    index_path="faiss_claimlens_index",
    dense_top_k=40,
    use_reranker=True
)


print("Loading Evaluation Queries from JSON...")
with open("data/evaluation_queries.json", "r") as f:
    evaluation_queries = json.load(f)


print("Running Evaluation...")
evaluator = RetrievalEvaluator()
results = evaluator.evaluate(retriever, evaluation_queries)


print("\nEvaluation Results")
print("=" * 40)
for metric, value in results.items():
    print(f"{metric}: {value:.4f}")