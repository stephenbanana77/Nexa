"""Application configuration."""
import os
from pathlib import Path


def _load_local_env() -> None:
    """Load root/backend .env files without adding a runtime dependency."""
    candidates = [
        Path(__file__).resolve().parents[2] / ".env",
        Path(__file__).resolve().parents[1] / ".env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_local_env()


class Settings:
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "nexa-dev-secret-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://nexa:nexa@localhost:5432/nexa"
    )

    # CORS
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")

    # Storage
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./storage")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))

    # LLM
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "deepseek").lower()
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    MOONSHOT_API_KEY: str = os.getenv("MOONSHOT_API_KEY", "")
    MOONSHOT_BASE_URL: str = os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")
    MOONSHOT_MODEL: str = os.getenv("MOONSHOT_MODEL", "kimi-k3")

    @property
    def LLM_API_KEY(self) -> str:
        if os.getenv("LLM_API_KEY"):
            return os.getenv("LLM_API_KEY", "")
        if self.LLM_PROVIDER == "moonshot":
            return self.MOONSHOT_API_KEY
        return self.DEEPSEEK_API_KEY

    @property
    def LLM_BASE_URL(self) -> str:
        if os.getenv("LLM_BASE_URL"):
            return os.getenv("LLM_BASE_URL", "")
        if self.LLM_PROVIDER == "moonshot":
            return self.MOONSHOT_BASE_URL
        return self.DEEPSEEK_BASE_URL

    @property
    def LLM_MODEL(self) -> str:
        if os.getenv("LLM_MODEL"):
            return os.getenv("LLM_MODEL", "")
        if self.LLM_PROVIDER == "moonshot":
            return self.MOONSHOT_MODEL
        return self.DEEPSEEK_MODEL
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))


settings = Settings()
