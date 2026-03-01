from typing import List, Dict
from evaluation.schema import EvaluationQuery
from langchain_core.documents import Document


class RetrievalEvaluator:
    """
    Retrieval Evaluator for ClaimLens.

    Supports:
        - Stage-wise evaluation (Dense / Hybrid / Final)
        - Single-clause recall
        - Multi-clause coverage
        - MRR
        - Diagnostic reporting
    """

    @staticmethod
    def _get_retrieved_ids(
        retrieved_docs: List[Document],
        k: int
    ) -> set:
        return {
            doc.metadata.get("clause_id")
            for doc in retrieved_docs[:k]
            if doc.metadata.get("clause_id") is not None
        }

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

    def evaluate_stagewise(
        self,
        retriever,
        test_queries: List[EvaluationQuery],
        k_dense: int = 20,
        k_final: int = 5
    ) -> Dict[str, float]:

        dense_recall = 0.0
        hybrid_recall = 0.0
        final_recall = 0.0
        final_mrr = 0.0

        for test in test_queries:

            stages = retriever.retrieve(
                test.query,
                return_stages=True
            )

            dense_docs = stages["dense"]
            hybrid_docs = stages["hybrid"]
            final_docs = stages["final"]

            dense_recall += self.recall_at_k(
                dense_docs, test.relevant_clause_ids, k_dense
            )

            hybrid_recall += self.recall_at_k(
                hybrid_docs, test.relevant_clause_ids, k_dense
            )

            final_recall += self.recall_at_k(
                final_docs, test.relevant_clause_ids, k_final
            )

            final_mrr += self.reciprocal_rank(
                final_docs,
                test.relevant_clause_ids
            )

        n = len(test_queries)

        return {
            f"Dense Recall@{k_dense}": dense_recall / n,
            f"Hybrid Recall@{k_dense}": hybrid_recall / n,
            f"Final Recall@{k_final}": final_recall / n,
            "Final MRR": final_mrr / n,
        }

    def evaluate_single_clause(
        self,
        retriever,
        test_queries: List[EvaluationQuery],
        k: int = 20
    ) -> Dict[str, float]:

        recall = 0.0
        mrr = 0.0

        for test in test_queries:

            stages = retriever.retrieve(
                test.query,
                return_stages=True
            )

            final_docs = stages["final"]

            recall += self.recall_at_k(
                final_docs,
                test.relevant_clause_ids,
                k
            )

            mrr += self.reciprocal_rank(
                final_docs,
                test.relevant_clause_ids
            )

        n = len(test_queries)

        return {
            f"Recall@{k}": recall / n,
            "MRR": mrr / n
        }

    def evaluate_multi_clause(
        self,
        retriever,
        test_queries: List[EvaluationQuery],
        diagnostics: bool = False
    ) -> Dict[str, float]:

        if not test_queries:
            raise ValueError("test_queries cannot be empty.")

        coverage_at_20 = 0.0
        full_recall_at_20 = 0
        mrr = 0.0

        for idx, test in enumerate(test_queries, start=1):

            stages = retriever.retrieve(
                test.query,
                return_stages=True
            )

            final_docs = stages["final"]

            retrieved_ids = self._get_retrieved_ids(final_docs, 20)
            relevant_ids = set(test.relevant_clause_ids)

            if not relevant_ids:
                continue

            intersection = retrieved_ids & relevant_ids
            coverage = len(intersection) / len(relevant_ids)

            coverage_at_20 += coverage
            full_recall = coverage == 1.0
            full_recall_at_20 += int(full_recall)

            rr = self.reciprocal_rank(final_docs, test.relevant_clause_ids)
            mrr += rr

            if diagnostics:
                print("\n========================================")
                print(f"Query {idx}: {test.query}")
                print("----------------------------------------")

                print("Status:", "PASS" if full_recall else "FAIL")
                print(f"Coverage@20: {coverage:.2f}")
                print(f"Reciprocal Rank: {rr:.4f}")

                print("Relevant Clauses:")
                print(relevant_ids)

                print("Retrieved Clauses (Top 20):")
                print(retrieved_ids)

                if not full_recall:
                    missing = relevant_ids - retrieved_ids
                    print("Missing Clauses:")
                    print(missing)

                print("========================================")

        n = len(test_queries)

        return {
            "Clause Coverage@20": coverage_at_20 / n,
            "Full Recall@20": full_recall_at_20 / n,
            "MRR": mrr / n
        }