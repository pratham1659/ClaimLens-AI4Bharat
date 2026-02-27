from langchain_community.retrievers import BM25Retriever
from app.retriever.vector_store import build_or_load_vectorstore
from app.retriever.reranker import ClauseReranker

class ClaimLensRetriever:
    """
    Hybrid retrieval system:

    Stage 1: Candidate Generation (High Recall)
        1. Dense retrieval using FAISS (semantic similarity)
        2. BM25 retrieval (lexical keyword matching)

    Stage 2: Cross-Encoder Reranking (High Precision)
        - BAAI/bge-reranker-base scores query-clause pairs
        - Top-K most relevant clauses are returned

    This design combines semantic similarity, exact keyword matching,
    and intelligent reranking to improve both recall and precision.
    """

    def __init__(
            self,
            clause_documents,
            embedding_model,
            index_path: str,
            dense_top_k: int = 20,
            rerank_top_k: int = 5
    ):
        self.dense_top_k = dense_top_k
        self.rerank_top_k = rerank_top_k

        self.vectorstore = build_or_load_vectorstore(
            clause_documents,
            embedding_model,
            index_path
        )

        self.bm25_retriever = BM25Retriever.from_documents(
            clause_documents
        )
        self.bm25_retriever.k = dense_top_k

        self.reranker = ClauseReranker()

    def retrieve(self, query: str):
        """
        Retrieve top relevant clauses for a given query.

        Returns:
            List[Document]
        """

        dense_retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": self.dense_top_k}
        )
        dense_results = dense_retriever.invoke(query)

        bm25_results = self.bm25_retriever.invoke(query)

        hybrid_pool = dense_results + bm25_results

        seen = set()
        unique_hybrid_clauses = []

        for doc in hybrid_pool:
            key = (
                doc.metadata.get("clause_number"),
                doc.metadata.get("start_page"),
            )
            if key not in seen:
                seen.add(key)
                unique_hybrid_clauses.append(doc)

        final_clauses = self.reranker.rerank(
            query=query,
            candidate_clauses=unique_hybrid_clauses,
            top_k=self.rerank_top_k
        )

        return final_clauses