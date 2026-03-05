class Settings:
    # Embeddings
    EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"

    # Retrieval
    DENSE_TOP_K = 40
    USE_RERANKER = True

    # Reasoning
    LLM_MODEL = "openai/gpt-oss-20b"
    LLM_TEMPERATURE = 0.0
    MAX_RETRIES = 2

    # Pipeline
    PIPELINE_TOP_K = 5