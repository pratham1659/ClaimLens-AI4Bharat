# backend/app/core/config.py
"""
Application configuration management using Pydantic Settings.
Supports environment-based configuration for different deployment stages.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
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
    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000", "http://localhost:5173"]

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

    # S3 Configuration
    S3_BUCKET_NAME: str = Field(
        default="claimlens-documents", description="S3 bucket for documents")
    S3_PRESIGNED_URL_EXPIRY: int = 3600

    # AWS Bedrock
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-haiku-20240307-v1:0"
    BEDROCK_EMBEDDING_MODEL_ID: str = "amazon.titan-embed-text-v1"

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: List[str] = [".pdf", ".json"]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith(("postgresql", "postgres")):
            raise ValueError("Only PostgreSQL databases are supported")
        return v

    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance to avoid repeated environment parsing.
    """
    return Settings()


settings = get_settings()
