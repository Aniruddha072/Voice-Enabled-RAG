"""Application settings, loaded from environment variables and .env.

One flat settings object instead of a config class per layer. There's
only one place to look, and pydantic-settings already validates types
and fails loudly on startup if something required is missing.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "development"
    log_level: str = "INFO"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "voicerag"


settings = Settings()
