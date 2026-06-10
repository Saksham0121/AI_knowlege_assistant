from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Gemini AI
    gemini_api_key: str

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "insightflow"

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Redis
    redis_url: str = "redis://localhost:6379"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_data"

    # File Storage
    storage_dir: str = "./storage"

    # App
    app_env: str = "development"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # Rate Limiting
    rate_limit_per_minute: int = 60

    @property
    def origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
