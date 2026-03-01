import os
import torch
from sentence_transformers import CrossEncoder
from dotenv import load_dotenv

load_dotenv()

RERANKER_MODELS = {
    "base": "BAAI/bge-reranker-base",
    "large": "BAAI/bge-reranker-large",
}

# Optional local model directory (for Docker/offline usage)
LOCAL_MODEL_DIR = os.environ.get("LOCAL_MODEL_PATH", "./models")


def _get_device() -> str:
    """
    Automatically selects the best available device:
    CUDA > MPS > CPU
    """
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _resolve_model_path(model_name: str) -> str:
    """
    Returns local model path if available,
    otherwise returns HuggingFace model name.
    """
    local_name = model_name.replace("/", "--")
    local_path = os.path.join(LOCAL_MODEL_DIR, local_name)

    if os.path.isdir(local_path):
        print(f"Using local reranker model: {local_path}")
        return local_path

    return model_name


class ClauseReranker:
    """
    Cross-encoder reranker for improving retrieval precision.

    Model options:
        - "base"  : BAAI/bge-reranker-base
        - "large" : BAAI/bge-reranker-large

    Used as Stage 2 after dense/hybrid retrieval.
    """

    def __init__(self, model_size: str = "base", device: str | None = None):

        if model_size not in RERANKER_MODELS:
            raise ValueError(
                f"Invalid model_size '{model_size}'. "
                f"Choose from {list(RERANKER_MODELS.keys())}"
            )

        model_name = RERANKER_MODELS[model_size]

        # Auto device if not explicitly provided
        device = device or _get_device()

        if device == "cpu" and model_size == "large":
            print(
                "Warning: bge-reranker-large on CPU may be slow. "
                "Consider model_size='base' for CPU environments."
            )

        resolved_path = _resolve_model_path(model_name)

        print(f"Loading reranker model: {model_name} on {device.upper()}")

        self.model = CrossEncoder(resolved_path, device=device)

    def rerank(self, query: str, candidate_clauses, top_k: int = 5):
        """
        Rerank retrieved clause candidates using cross-encoder scoring.
        """

        if not candidate_clauses:
            return []

        pairs = [(query, clause.page_content) for clause in candidate_clauses]

        scores = self.model.predict(pairs)

        scored_clauses = sorted(
            zip(candidate_clauses, scores),
            key=lambda x: x[1],
            reverse=True,
        )

        return [clause for clause, _ in scored_clauses[:top_k]]