from sentence_transformers import CrossEncoder


class ClauseReranker:
    """
    Cross-encoder reranker for improving retrieval precision.
    Uses BAAI/bge-reranker-large.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-large"):
        print("Loading reranker model...")
        self.model = CrossEncoder(model_name, device="cpu")

    def rerank(self, query, candidate_clauses, top_k: int = 5):
        """
        Rerank retrieved clause candidates using cross-encoder.

        Parameters:
            query (str)
            candidate_clauses (List[Document])
            top_k (int): Number of top clauses to return

        Returns:
            List[Document]
        """

        if not candidate_clauses:
            return []

        pairs = [(query, clause.page_content) for clause in candidate_clauses]

        scores = self.model.predict(pairs)

        scored_clauses = list(zip(candidate_clauses, scores))

        scored_clauses.sort(key=lambda x: x[1], reverse=True)

        return [clause for clause, _ in scored_clauses[:top_k]]