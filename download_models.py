#!/usr/bin/env python3
"""
Download HuggingFace models for local RAG system.
Models are saved to ./models directory for offline use.
"""

import os
from huggingface_hub import snapshot_download

# Models used in the RAG system
MODELS = {
    # Embedding models (BGE)
    "embedding_base": "BAAI/bge-base-en-v1.5",
    "embedding_small": "BAAI/bge-small-en-v1.5",
    # Reranker models
    "reranker_base": "BAAI/bge-reranker-base",
}

# Output directory
MODELS_DIR = "./models"


def download_models():
    """Download all required models to local directory."""
    os.makedirs(MODELS_DIR, exist_ok=True)

    print("=" * 60)
    print("Downloading HuggingFace models for ClaimLens RAG")
    print("=" * 60)
    print(f"Output directory: {os.path.abspath(MODELS_DIR)}")
    print()

    for name, model_id in MODELS.items():
        local_dir = os.path.join(MODELS_DIR, model_id.replace("/", "--"))

        print(f"📥 Downloading: {model_id}")
        print(f"   To: {local_dir}")

        try:
            snapshot_download(
                repo_id=model_id,
                local_dir=local_dir,
                local_dir_use_symlinks=False,
            )
            print(f"   ✅ Downloaded successfully!")
        except Exception as e:
            print(f"   ❌ Error downloading {model_id}: {e}")

        print()

    print("=" * 60)
    print("✅ All models downloaded!")
    print("=" * 60)
    print()
    print("Models are stored in:", os.path.abspath(MODELS_DIR))
    print()
    print("To use local models, update your code to reference:")
    for name, model_id in MODELS.items():
        local_path = os.path.join(MODELS_DIR, model_id.replace("/", "--"))
        print(f"  {name}: {local_path}")


if __name__ == "__main__":
    download_models()
