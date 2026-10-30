from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "postgres"
    redis_url: str
    qdrant_url: str
    anthropic_api_key: str = ""


settings = Settings()