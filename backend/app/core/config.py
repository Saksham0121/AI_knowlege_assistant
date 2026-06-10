import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List

# Resolve path to .env file
# config.py is at: backend/app/core/config.py
# repo root is 3 levels up: backend/app/core/.. / .. / ..
current_dir = Path(__file__).resolve().parent
repo_root = current_dir.parent.parent.parent
root_env = repo_root / ".env"
backend_env = current_dir.parent.parent / ".env"

if root_env.exists():
    env_file_path = str(root_env)
elif backend_env.exists():
    env_file_path = str(backend_env)
else:
    env_file_path = ".env"


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
        env_file = env_file_path
        case_sensitive = False


settings = Settings()

