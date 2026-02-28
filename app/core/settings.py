from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ClaimLens API"
    app_version: str = "0.1.0"
    environment: str = "dev"
    api_v1_prefix: str = "/v1"
    database_url: str = "mysql+pymysql://root:root@localhost:3306/claimlens"
    storage_dir: str = "storage"
    faiss_index_root: str = "faiss_indexes"
    redis_url: str = "redis://localhost:6379/0"
    rq_default_queue: str = "default"
    rq_dead_letter_queue: str = "dead_letter"
    rq_retry_max: int = 3
    rq_retry_intervals: str = "1,2,4"


@lru_cache
def get_settings() -> Settings:
    return Settings()
