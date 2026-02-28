import logging
from typing import List

from langchain_core.documents import Document

from app.reasoning.reasoner import ClaimLensReasoner
from app.reasoning.output_schema import RAGResponse


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

        self.retriever = retriever
        self.reasoner = reasoner
        self.top_k = top_k

    def invoke(self, query: str) -> RAGResponse:
        """
        Main system entry point.

        Returns:
            RAGResponse (validated structured response)
        """

        retrieved_clauses: List[Document] = self.retriever.retrieve(query)

        if not retrieved_clauses:
            raise ValueError("Retriever returned no clauses.")

        selected_clauses = retrieved_clauses[: self.top_k]

        retrieved_ids = [
            doc.metadata.get("clause_id")
            for doc in selected_clauses
        ]

        logger.info(
            {
                "event": "retrieval_completed",
                "query": query,
                "top_k": self.top_k,
                "retrieved_clause_ids": retrieved_ids,
            }
        )

        response: RAGResponse = self.reasoner.answer(
            query=query,
            retrieved_clauses=selected_clauses,
        )

        return response