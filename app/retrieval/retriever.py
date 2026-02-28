from langchain_community.retrievers import BM25Retriever
from app.retrieval.vector_store import build_or_load_vectorstore
from app.retrieval.reranker import ClauseReranker

class ClaimLensRetriever:
    """
    Hybrid Retrieval System (Evaluation-Ready)

    Stage 1: Candidate Generation
        - Dense retrieval (FAISS)
        - BM25 retrieval
        - Merge + Deduplicate

    Stage 2 (Optional):
        - Cross-Encoder Reranking

    IMPORTANT:
        - No truncation happens inside retriever.
        - Evaluator decides Recall@K.
        - Can return all intermediate stages.
    """

    def __init__(
        self,
        clause_documents,
        embedding_model,
        index_path: str,
        dense_top_k: int = 20,
        use_reranker: bool = False
    ):
        self.dense_top_k = dense_top_k
        self.use_reranker = use_reranker

        self.vectorstore = build_or_load_vectorstore(
            clause_documents,
            embedding_model,
            index_path
        )

        self.bm25_retriever = BM25Retriever.from_documents(
            clause_documents
        )
        self.bm25_retriever.k = dense_top_k

        if self.use_reranker:
            self.reranker = ClauseReranker()
        else:
            self.reranker = None

    def retrieve(self, query: str, return_stages: bool = False):
        """
        Retrieve ranked clauses.

        If return_stages=True:
            returns dict with dense, bm25, hybrid, final stages.
        Otherwise:
            returns final ranking only.
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
            clause_id = doc.metadata.get("clause_id")
            if clause_id not in seen:
                seen.add(clause_id)
                unique_hybrid_clauses.append(doc)

        if self.use_reranker:
            final_ranking = self.reranker.rerank(
                query=query,
                candidate_clauses=unique_hybrid_clauses,
                top_k=len(unique_hybrid_clauses)  # full ranking
            )
        else:
            final_ranking = unique_hybrid_clauses

        if return_stages:
            return {
                "dense": dense_results,
                "bm25": bm25_results,
                "hybrid": unique_hybrid_clauses,
                "final": final_ranking
            }

        return final_ranking