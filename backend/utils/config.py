"""Application configuration."""
import os


class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "nexa-dev-secret-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://nexa:nexa@localhost:5432/nexa"
    )
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./storage")
    MAX_UPLOAD_SIZE_MB: int = 100


settings = Settings()
