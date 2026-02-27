from typing import List, Dict
from langchain_core.documents import Document


class RetrievalEvaluator:
    """
    Computes retrieval metrics:
    - Recall@K
    - MRR
    """

    @staticmethod
    def recall_at_k(
        retrieved_docs: List[Document],
        relevant_clause_numbers: List[str],
        k: int
    ) -> float:
        top_k = retrieved_docs[:k]

        for doc in top_k:
            if doc.metadata.get("clause_number") in relevant_clause_numbers:
                return 1.0

        return 0.0

    @staticmethod
    def reciprocal_rank(
        retrieved_docs: List[Document],
        relevant_clause_numbers: List[str]
    ) -> float:
        for rank, doc in enumerate(retrieved_docs, start=1):
            if doc.metadata.get("clause_number") in relevant_clause_numbers:
                return 1.0 / rank
        return 0.0

    def evaluate(
        self,
        retriever,
        test_queries: List[Dict]
    ):
        total_recall_5 = 0
        total_recall_20 = 0
        total_mrr = 0

        for test in test_queries:
            query = test["query"]
            relevant = test["relevant_clause_numbers"]

            retrieved_docs = retriever.retrieve(query)

            total_recall_5 += self.recall_at_k(retrieved_docs, relevant, 5)
            total_recall_20 += self.recall_at_k(retrieved_docs, relevant, 20)
            total_mrr += self.reciprocal_rank(retrieved_docs, relevant)

        n = len(test_queries)

        return {
            "Recall@5": total_recall_5 / n,
            "Recall@20": total_recall_20 / n,
            "MRR": total_mrr / n,
        }