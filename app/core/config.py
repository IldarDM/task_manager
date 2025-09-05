import os
from typing import Optional

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    POSTGRES_USER: str = "devuser"
    POSTGRES_PASSWORD: str = "devpass"
    POSTGRES_DB: str = "task_manager"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # Security
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int = 30

    # Rate Limiting
    rate_limit_per_minute: int = 100
    auth_rate_limit_per_minute: int = 10

    # CORS
    backend_cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # App
    app_name: str = "TaskFlow API"
    version: str = "1.0.0"
    debug: bool = False

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Email
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    emails_from_email: Optional[str] = None
    emails_from_name: Optional[str] = None

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    class Config:
        env_file = os.getenv("ENV_FILE", ".env")
        env_file_encoding = "utf-8"

settings = Settings()
