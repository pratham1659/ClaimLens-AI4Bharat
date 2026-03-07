import torch
from sentence_transformers import CrossEncoder


RERANKER_MODELS = {
    "base": "BAAI/bge-reranker-base",
    "large": "BAAI/bge-reranker-large",
}


def _get_device():
    """
    Automatically selects best device available.

    Priority:
        CUDA (NVIDIA GPU)
        MPS (Apple Silicon GPU)
        CPU fallback
    """
    if torch.cuda.is_available():
        return "cuda"

    if torch.backends.mps.is_available():
        return "mps"

    return "cpu"


class ClauseReranker:
    """
    Cross-encoder reranker for improving retrieval precision.

    Works as Stage 2 of hybrid retrieval:

        Query
          ↓
        Dense + BM25 retrieval
          ↓
        Candidate clauses
          ↓
        Cross-Encoder scoring
          ↓
        Top-K final ranking

    Recommended models:
        base  -> CPU / development
        large -> GPU / production
    """

    def __init__(
        self,
        model_size: str = "base",
        max_candidates: int = 40,
        batch_size: int = 16,
    ):
        """
        Parameters
        ----------
        model_size : str
            "base" or "large"

        max_candidates : int
            Safety cap to prevent reranking too many documents.

        batch_size : int
            Batch size for cross-encoder inference.
        """

        if model_size not in RERANKER_MODELS:
            raise ValueError(
                f"Invalid model_size '{model_size}'. Choose from {list(RERANKER_MODELS.keys())}"
            )

        self.device = _get_device()
        self.model_name = RERANKER_MODELS[model_size]
        self.max_candidates = max_candidates
        self.batch_size = batch_size

        print(f"Loading reranker model: {self.model_name}")
        print(f"Device: {self.device.upper()}")

        self.model = CrossEncoder(
            self.model_name,
            device=self.device
        )

    def rerank(
        self,
        query: str,
        candidate_clauses,
        top_k: int = 5,
        return_scores: bool = False,
    ):
        """
        Rerank retrieved clause candidates using cross-encoder scoring.

        Parameters
        ----------
        query : str
            User query

        candidate_clauses : List[Document]
            Candidate clauses from hybrid retrieval

        top_k : int
            Number of final clauses to return

        return_scores : bool
            If True, returns (document, score)

        Returns
        -------
        List[Document] or List[(Document, score)]
        """

        if not candidate_clauses:
            return []

        candidate_clauses = candidate_clauses[: self.max_candidates]


        pairs = [
            (query, clause.page_content)
            for clause in candidate_clauses
        ]

        scores = self.model.predict(
            pairs,
            batch_size=self.batch_size
        )


        ranked = sorted(
            zip(candidate_clauses, scores),
            key=lambda x: x[1],
            reverse=True
        )

        top_results = ranked[:top_k]

        if return_scores:
            return top_results

        return [doc for doc, _ in top_results]