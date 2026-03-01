import logging
from typing import List

from langchain_core.documents import Document

from app.rag_main.reasoning.reasoner import ClaimLensReasoner
from app.rag_main.reasoning.output_schema import RAGResponse


logger = logging.getLogger(__name__)


class ClaimLensPipeline:
    """
    Orchestrates the full RAG flow:

        Query
            → Retriever
            → Top-K Clause Selection
            → Reasoner
            → Validated RAGResponse

    This class defines the clean backend interface for ClaimLens.
    Safe to use inside FastAPI service layer.
    """

    def __init__(
        self,
        retriever,
        reasoner: ClaimLensReasoner,
        top_k: int = 5,
    ):
        """
        Parameters:
            retriever: Retrieval component (must expose .retrieve(query))
            reasoner: ClaimLensReasoner instance
            top_k: Number of clauses to pass to reasoning layer
        """

        if top_k <= 0:
            raise ValueError("top_k must be > 0")

        self.retriever = retriever
        self.reasoner = reasoner
        self.top_k = top_k

    def invoke(self, query: str) -> RAGResponse:
        """
        Main system entry point.

        Parameters:
            query (str): User query

        Returns:
            RAGResponse: Structured validated output
        """

        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        logger.info(
            {
                "event": "pipeline_invoked",
                "query": query,
            }
        )

        retrieved_clauses: List[Document] = self.retriever.retrieve(query)

        if not retrieved_clauses:
            logger.warning(
                {
                    "event": "retrieval_empty",
                    "query": query,
                }
            )
            raise ValueError("Retriever returned no clauses.")

        selected_clauses = retrieved_clauses[: self.top_k]

        retrieved_ids = [
            doc.metadata.get("clause_id")
            for doc in selected_clauses
            if doc.metadata
        ]

        logger.info(
            {
                "event": "retrieval_completed",
                "query": query,
                "top_k": self.top_k,
                "retrieved_clause_ids": retrieved_ids,
            }
        )

        try:
            response: RAGResponse = self.reasoner.answer(
                query=query,
                retrieved_clauses=selected_clauses,
            )
        except Exception as e:
            logger.exception(
                {
                    "event": "reasoning_failed",
                    "query": query,
                    "error": str(e),
                }
            )
            raise

        logger.info(
            {
                "event": "reasoning_completed",
                "query": query,
                "found": response.found,
                "confidence": response.confidence,
            }
        )

        return response