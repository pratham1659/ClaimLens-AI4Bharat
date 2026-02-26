from retriever.vector_store import build_or_load_vectorstore
from retriever.reranker import ClauseReranker

class ClaimLensRetriever:
    """
    Two-stage retrieval system:
    1. Dense retrieval (FAISS) for high recall
    2. Cross-encoder reranking for high precision
    """

    def __init__(
            self,
            clause_documents,
            embedding_model,
            index_path: str = "faiss_claimlens_index",
            dens_top_k: int = 20,
            rerank_top_k: int = 5
    ):
        self.dense_top_k = dens_top_k
        self.rerank_top_k = rerank_top_k

        self.vectorstore = build_or_load_vectorstore(
            clause_documents,
            embedding_model,
            index_path
        )

        self.reranker = ClauseReranker()
    
    def retriever(self, query: str):
        """
        Retrieve top relevant clauses for a given query.

        Returns:
            List[Document]
        """

        retriever = self.vectorstore.as_retriever(
            search_type = "similarity",
            search_kwargs = {"k": self.dense_top_k}
        )

        candidate_clauses = retriever.invoke(query)

        final_clauses = self.reranker.rerank(
            query,
            candidate_clauses,
            top_k=self.rerank_top_k
        )

        return final_clauses