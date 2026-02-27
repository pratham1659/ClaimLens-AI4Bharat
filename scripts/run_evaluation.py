from app.ingestion.loader import load_policy_documents
from app.ingestion.clause_splitter import clause_based_splitter
from app.retriever.embeddings import load_embedding_model
from app.retriever.retriever import ClaimLensRetriever

from app.evaluation.evaluator import RetrievalEvaluator

import json

print(f"Loading Documents...")
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

print(f"Splitting Into Clauses...")
clauses = clause_based_splitter(docs)

print(f"Loading Embedding Model...")
embedding_model = load_embedding_model()

print(f"Building Retriever...")
retriever = ClaimLensRetriever(
    clause_documents=clauses,
    embedding_model=embedding_model,
    index_path="faiss_claimlens_index"
)


print(f"Loading Evaluation Queries from JSON...")
with open("data/evaluation_queries.json", "r") as f:
    evaluation_queries = json.load(f)

print(f"Running Evaluation...")
evaluator = RetrievalEvaluator()
results = evaluator.evaluate(retriever, evaluation_queries)

print(f"\nEvaluation Results")
print("=" * 40)

for metric, value in results.items():
    print(f"{metric}: {value:.4f}")