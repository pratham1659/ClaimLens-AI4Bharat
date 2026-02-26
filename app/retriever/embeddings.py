from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

load_dotenv()


def load_embedding_model():
    """
    Loads the BGE-large embedding model for dense retrieval.

    Configuration:
    - Model: BAAI/bge-large-en-v1.5
    - Device: CPU
    - Embeddings normalized for cosine similarity
    """

    embedding_model = HuggingFaceEmbeddings(
        model_name="BAAI/bge-large-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    return embedding_model