import os
from sentence_transformers import CrossEncoder

RERANKER_MODELS = {
    "base": "BAAI/bge-reranker-base",
    "large": "BAAI/bge-reranker-large",
}

# Local model paths (when downloaded to ./models directory)
LOCAL_MODEL_DIR = os.environ.get("LOCAL_MODEL_PATH", "/app/models")


def _get_local_model_path(model_name: str) -> str:
    """
    Get local model path if models are downloaded locally.
    Returns the HuggingFace model name if local path doesn't exist.
    """
    # Convert model name to local directory format
    local_name = model_name.replace("/", "--")
    local_path = os.path.join(LOCAL_MODEL_DIR, local_name)

    if os.path.exists(local_path):
        print(f"   Using local reranker model: {local_path}")
        return local_path

    # Fallback to HuggingFace download
    return model_name


class ClauseReranker:
    """
    Cross-encoder reranker for improving retrieval precision.

    Model options (set via model_size):
        - "base"  : BAAI/bge-reranker-base  — recommended for CPU / dev
        - "large" : BAAI/bge-reranker-large — recommended for GPU / production

    How it works:
        Unlike bi-encoders (used in FAISS), a cross-encoder scores each
        (query, clause) pair jointly, giving much higher precision at the
        cost of speed. Used as Stage 2 after candidate generation.
    """

    def __init__(self, model_size: str = "base", device: str = "cpu"):
        """
        Parameters:
            model_size (str): "base" or "large". Defaults to "base".
            device (str): "cpu", "cuda", or "mps". Defaults to "cpu".
        """
        if model_size not in RERANKER_MODELS:
            raise ValueError(
                f"Invalid model_size '{model_size}'. Choose from: {list(RERANKER_MODELS.keys())}"
            )

        model_name = RERANKER_MODELS[model_size]
        print(f"Loading reranker model: {model_name} on {device.upper()}")

        # Try to use local model path if available
        model_path = _get_local_model_path(model_name)

        self.model = CrossEncoder(model_path, device=device)

    def rerank(self, query: str, candidate_clauses, top_k: int = 5):
        """
        Rerank retrieved clause candidates using cross-encoder scoring.

        Parameters:
            query (str): The user's search query.
            candidate_clauses (List[Document]): Candidates from hybrid retrieval.
            top_k (int): Number of top clauses to return after reranking.

        Returns:
            List[Document]: Top-k clauses sorted by relevance score (descending).
        """
        if not candidate_clauses:
            return []

        pairs = [(query, clause.page_content) for clause in candidate_clauses]

        scores = self.model.predict(pairs)

        scored_clauses = sorted(
            zip(candidate_clauses, scores),
            key=lambda x: x[1],
            reverse=True
        )

        return [clause for clause, _ in scored_clauses[:top_k]]
