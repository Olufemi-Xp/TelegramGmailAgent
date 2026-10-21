from typing import Any, List, Optional, Union
import os
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = Field(default="", description="Telegram Bot API Token from @BotFather")
    BOT_MODE: str = Field(default="auto", description="Bot run mode: 'auto', 'polling', or 'webhook'")
    TELEGRAM_WEBHOOK_URL: str = Field(default="", description="Public base URL for Telegram webhook (e.g. https://my-app.vercel.app)")
    TELEGRAM_WEBHOOK_SECRET: str = Field(default="", description="Optional secret token for verifying Telegram webhook updates")
    CRON_SECRET: str = Field(default="", description="Optional secret token for verifying Vercel Cron requests")
    # NOTE: Declared as Union[str, List[int]] so pydantic-settings v2 does NOT
    # attempt to JSON-decode the raw env string before our validator runs.
    # The validator normalizes all formats (CSV string, list, int) into List[int].
    TELEGRAM_ALLOWED_USER_IDS: Union[str, List[int]] = Field(
        default_factory=list,
        description="List of authorized numeric Telegram User IDs (e.g. 12345678,98765432)"
    )

    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///storage/agent.db",
        description="Async database connection string. e.g. postgresql+asyncpg://user:pass@host:5432/dbname"
    )
    DB_ECHO: bool = Field(default=False, description="Log all SQL queries")

    # OpenRouter LLM Gateway
    OPENROUTER_API_KEY: str = Field(default="", description="OpenRouter API Key")
    OPENROUTER_BASE_URL: str = Field(default="https://openrouter.ai/api/v1", description="OpenRouter API Base URL")
    OPENROUTER_MODEL: str = Field(default="openai/gpt-oss-120b", description="Primary model identifier")
    OPENROUTER_FALLBACK_MODEL: str = Field(default="meta-llama/llama-3.3-70b-instruct", description="Fallback model identifier")
    OPENROUTER_SITE_URL: str = Field(default="https://github.com/personal-ai-assistant", description="OpenRouter referer URL")
    OPENROUTER_APP_NAME: str = Field(default="Personal AI Assistant", description="OpenRouter X-Title header")

    # Cryptography / Secrets
    ENCRYPTION_KEY: str = Field(
        default="w_9w12M7O5E-8d_f1JzB4pA6kL3sV9tX2qY5mZ7nK1o=",
        description="Fernet URL-safe base64-encoded 32-byte key for encrypting OAuth tokens"
    )

    # Search & Research Providers
    PERPLEXITY_API_KEY: str = Field(default="", description="Perplexity API Key")
    PERPLEXITY_MODEL: str = Field(default="sonar", description="Perplexity model name")
    GOOGLE_SEARCH_API_KEY: str = Field(default="", description="Google Custom Search JSON API Key")
    GOOGLE_SEARCH_ENGINE_ID: str = Field(default="", description="Google Programmable Search Engine ID (cx)")
    TAVILY_API_KEY: str = Field(default="", description="Tavily API Key")

    # Google / Gmail OAuth 2.0
    GOOGLE_CLIENT_ID: str = Field(default="", description="Google Cloud OAuth Client ID")
    GOOGLE_CLIENT_SECRET: str = Field(default="", description="Google Cloud OAuth Client Secret")
    GOOGLE_REDIRECT_URI: str = Field(
        default="http://localhost:8000/oauth/google/callback",
        description="OAuth2 Redirect URI registered in Google Cloud Console"
    )

    # Embeddings, Voice & Vision
    EMBEDDING_PROVIDER: str = Field(default="local", description="Embedding provider: 'local', 'openrouter', or 'openai'")
    EMBEDDING_MODEL: str = Field(default="all-MiniLM-L6-v2", description="Embedding model name")
    EMBEDDING_DIMENSION: int = Field(default=384, description="Embedding vector dimension")
    TRANSCRIPTION_PROVIDER: str = Field(default="auto", description="Transcription provider: 'auto', 'openrouter', 'groq', 'openai', or 'none'")
    TRANSCRIPTION_API_KEY: str = Field(default="", description="API key for transcription if different from OpenRouter/Groq")
    GROQ_API_KEY: str = Field(default="", description="Groq API Key for free Whisper speech transcription")
    VISION_MODEL: str = Field(default="openai/gpt-4o-mini", description="Vision-capable model name on OpenRouter")

    # Operational & Budgets
    APP_ENV: str = Field(default="production", description="Environment: production, staging, development, testing")
    APP_TIMEZONE: str = Field(default="Africa/Lagos", description="Default user timezone")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR")
    MAX_FILE_SIZE_MB: int = Field(default=20, description="Max uploaded file size in MB")
    MAX_TOOL_ITERATIONS: int = Field(default=6, description="Max agent reasoning/tool iterations per prompt")
    REQUEST_TIMEOUT_SECONDS: float = Field(default=60.0, description="Default external HTTP request timeout")
    DAILY_MODEL_BUDGET: float = Field(default=5.0, description="Daily USD budget for model calls")
    MONTHLY_MODEL_BUDGET: float = Field(default=50.0, description="Monthly USD budget for model calls")
    
    # Server & Storage
    HOST: str = Field(default="0.0.0.0", description="FastAPI host")
    PORT: int = Field(default=8000, description="FastAPI port")
    STORAGE_DIR: str = Field(default="./storage", description="Base local storage directory")

    @field_validator("TELEGRAM_ALLOWED_USER_IDS", mode="before")
    @classmethod
    def parse_allowed_user_ids(cls, v: Any) -> List[int]:
        """Normalizes TELEGRAM_ALLOWED_USER_IDS from all common env formats into List[int].
        Handles CSV string ('12345,67890'), JSON array ('[12345, 67890]'),
        single int, or already-parsed list.
        """
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            # Handle JSON-array string like '[12345,67890]'
            if v.startswith("["):
                import json
                try:
                    parsed = json.loads(v)
                    return [int(uid) for uid in parsed]
                except (json.JSONDecodeError, ValueError):
                    pass
            # Handle CSV string like '12345,67890' or '12345'
            return [int(uid.strip()) for uid in v.split(",") if uid.strip()]
        if isinstance(v, (int, float)):
            return [int(v)]
        if isinstance(v, list):
            return [int(uid) for uid in v]
        return []

    @property
    def allowed_user_ids(self) -> List[int]:
        """Always returns TELEGRAM_ALLOWED_USER_IDS as List[int], regardless of how it was stored."""
        v = self.TELEGRAM_ALLOWED_USER_IDS
        if isinstance(v, list):
            return [int(x) for x in v]
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("["):
                import json
                try:
                    return [int(x) for x in json.loads(v)]
                except Exception:
                    pass
            return [int(uid.strip()) for uid in v.split(",") if uid.strip()]
        return []

    @property
    def is_postgres(self) -> bool:
        return "postgres" in self.DATABASE_URL.lower()

    @property
    def has_gmail_configured(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)

    @property
    def has_search_configured(self) -> bool:
        return bool(self.PERPLEXITY_API_KEY or (self.GOOGLE_SEARCH_API_KEY and self.GOOGLE_SEARCH_ENGINE_ID) or self.TAVILY_API_KEY)

    @property
    def is_webhook_mode(self) -> bool:
        if self.BOT_MODE == "webhook":
            return True
        if self.BOT_MODE == "polling":
            return False
        return bool(os.getenv("VERCEL") or self.TELEGRAM_WEBHOOK_URL)


# Global singleton instance
settings = Settings()
