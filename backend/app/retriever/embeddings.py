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
        print(f"   Using local model: {local_path}")
        return local_path

    # Fallback to HuggingFace download
    return model_name


def _get_device() -> str:
    """
    Automatically selects the best available device:
    - CUDA (NVIDIA GPU)
    - MPS (Apple Silicon)
    - CPU (fallback)
    """
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_embedding_model(model_size: str = "base") -> HuggingFaceEmbeddings:
    """
    Loads a BGE embedding model for dense retrieval.

    Parameters:
        model_size (str): One of "large", "base", or "small".
                          Use "small" or "base" for local dev/testing.
                          Use "large" for production / GPU environments.

    Returns:
        HuggingFaceEmbeddings instance ready for encoding.

    Device selection:
        - Automatically uses CUDA > MPS > CPU
        - On CPU, prefer "base" or "small" to avoid slow query latency
    """
    if model_size not in BGE_MODELS:
        raise ValueError(
            f"Invalid model_size '{model_size}'. Choose from: {list(BGE_MODELS.keys())}"
        )

    model_name = BGE_MODELS[model_size]
    device = _get_device()

    print(f"Loading embedding model: {model_name} on {device.upper()}")

    if device == "cpu" and model_size == "large":
        print(
            "Warning: Running bge-large on CPU is slow for query-time retrieval. "
            "Consider model_size='base' or 'small' for faster inference."
        )

    # Try to use local model path if available
    model_path = _get_local_model_path(model_name)

    embedding_model = HuggingFaceEmbeddings(
        model_name=model_path,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )

    return embedding_model
