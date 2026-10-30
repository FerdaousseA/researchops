from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "postgres"
    redis_url: str
    qdrant_url: str
    anthropic_api_key: str = ""
    upload_dir: str = "/data/uploads"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_cache_dir: str = "/data/models"
    qdrant_collection: str = "chunks"


settings = Settings()