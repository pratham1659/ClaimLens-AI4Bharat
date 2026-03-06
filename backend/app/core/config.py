# backend/app/core/config.py
"""
Application configuration management using Pydantic Settings.
Supports environment-based configuration for different deployment stages.
"""

from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All sensitive values should be provided via environment or secrets manager.
    """

    # Application
    APP_NAME: str = "ClaimLens AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = Field(default="development",
                             description="deployment environment")

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: str = "*"  # Comma-separated string
    # Comma-separated string
    CORS_ORIGINS: str = "https://claimlen.com,https://www.claimlen.com,http://localhost,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://localhost:8000"

    # Security
    SECRET_KEY: str = Field(..., description="JWT secret key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/claimlens",
        description="PostgreSQL connection string"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_ENDPOINT_URL: Optional[str] = None
    S3_ENDPOINT_URL: Optional[str] = None
    USE_LOCALSTACK: bool = False

    # S3 Configuration
    S3_BUCKET_NAME: str = Field(
        default="claimlens-faiss-index-1", description="S3 bucket for documents")
    S3_PRESIGNED_URL_EXPIRY: int = 3600

    # AWS Bedrock
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-haiku-20240307-v1:0"
    BEDROCK_EMBEDDING_MODEL_ID: str = "amazon.titan-embed-text-v1"
    BEDROCK_ENABLED: bool = True

    # RAG Configuration
    USE_MOCK_LLM: bool = False
    EMBEDDING_MODE: str = "auto"  # auto, local, bedrock, mock
    EMBEDDING_MODEL_SIZE: str = "base"  # small, base, large (for local models)
    LOCAL_MODEL_PATH: str = "/app/models"

    # FAISS Index Paths
    FAISS_INDEX_PATH: str = "faiss_claimlens_index"
    FAISS_COMBINED_INDEX_PATH: str = "faiss_claimlens_combined_index"

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: str = ".pdf,.json"  # Comma-separated string

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith(("postgresql", "postgres")):
            raise ValueError("Only PostgreSQL databases are supported")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_hosts_list(self) -> List[str]:
        """Get allowed hosts as a list."""
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]

    @property
    def allowed_file_types_list(self) -> List[str]:
        """Get allowed file types as a list."""
        return [ft.strip() for ft in self.ALLOWED_FILE_TYPES.split(",") if ft.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance to avoid repeated environment parsing.
    """
    return Settings()


settings = get_settings()
