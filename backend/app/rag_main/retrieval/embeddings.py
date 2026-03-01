import os
import torch
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

load_dotenv()

BGE_MODELS = {
    "large": "BAAI/bge-large-en-v1.5",
    "base": "BAAI/bge-base-en-v1.5",
    "small": "BAAI/bge-small-en-v1.5",
}

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
    Returns local model path if it exists,
    otherwise returns HuggingFace model name.
    """
    local_name = model_name.replace("/", "--")
    local_path = os.path.join(LOCAL_MODEL_DIR, local_name)

    if os.path.isdir(local_path):
        print(f"Using local embedding model: {local_path}")
        return local_path

    print(f"Using HuggingFace model: {model_name}")
    return model_name


def load_embedding_model(model_size: str = "base") -> HuggingFaceEmbeddings:
    """
    Loads a BGE embedding model for dense retrieval.

    Parameters:
        model_size (str):
            "small"  → fastest (dev/testing)
            "base"   → balanced (recommended)
            "large"  → best quality (GPU recommended)

    Returns:
        HuggingFaceEmbeddings instance

    Notes:
        - Automatically selects device
        - Normalizes embeddings (important for cosine similarity)
        - Supports local/offline model loading
    """

    if model_size not in BGE_MODELS:
        raise ValueError(
            f"Invalid model_size '{model_size}'. "
            f"Choose from {list(BGE_MODELS.keys())}"
        )

    model_name = BGE_MODELS[model_size]
    device = _get_device()

    if device == "cpu" and model_size == "large":
        print(
            "Warning: bge-large on CPU may be slow. "
            "Consider 'base' or 'small' for CPU environments."
        )

    print(f"Loading embedding model: {model_name} on {device.upper()}")

    resolved_path = _resolve_model_path(model_name)

    return HuggingFaceEmbeddings(
        model_name=resolved_path,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )