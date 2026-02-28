from typing import List, Dict
from langchain_core.documents import Document


class RetrievalEvaluator:
    """
    Stage-aware retrieval evaluation.

    Computes:
        - Dense Recall@20
        - Hybrid Recall@20
        - Final Recall@5
        - Final MRR

    Uses canonical clause_id.
    """

    @staticmethod
    def recall_at_k(
        retrieved_docs: List[Document],
        relevant_clause_ids: List[str],
        k: int
    ) -> float:

        relevant_set = set(relevant_clause_ids)

        for doc in retrieved_docs[:k]:
            if doc.metadata.get("clause_id") in relevant_set:
                return 1.0

        return 0.0

    @staticmethod
    def reciprocal_rank(
        retrieved_docs: List[Document],
        relevant_clause_ids: List[str]
    ) -> float:

        relevant_set = set(relevant_clause_ids)

        for rank, doc in enumerate(retrieved_docs, start=1):
            if doc.metadata.get("clause_id") in relevant_set:
                return 1.0 / rank

        return 0.0

    def evaluate(
        self,
        retriever,
        test_queries: List[Dict]
    ):

        dense_recall_20 = 0
        hybrid_recall_20 = 0
        final_recall_5 = 0
        final_mrr = 0

        for test in test_queries:
            query = test["query"]
            relevant_ids = test.get("relevant_clause_ids", [])

            stages = retriever.retrieve(query, return_stages=True)

            dense_docs = stages["dense"]
            hybrid_docs = stages["hybrid"]
            final_docs = stages["final"]

            dense_recall_20 += self.recall_at_k(
                dense_docs, relevant_ids, 20
            )

            hybrid_recall_20 += self.recall_at_k(
                hybrid_docs, relevant_ids, 20
            )

            final_recall_5 += self.recall_at_k(
                final_docs, relevant_ids, 5
            )

            final_mrr += self.reciprocal_rank(
                final_docs, relevant_ids
            )

        n = len(test_queries)

        return {
            "Dense Recall@20": dense_recall_20 / n,
            "Hybrid Recall@20": hybrid_recall_20 / n,
            "Final Recall@5": final_recall_5 / n,
            "Final MRR": final_mrr / n,
        }