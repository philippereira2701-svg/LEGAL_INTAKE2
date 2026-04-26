from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")

    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    flask_secret_key: str = Field(alias="FLASK_SECRET_KEY")
    pii_encryption_key: str | None = Field(default=None, alias="PII_ENCRYPTION_KEY")

    app_env: str = Field(default="development", alias="APP_ENV")
    app_base_url: str = Field(default="http://localhost:5000", alias="APP_BASE_URL")


def load_settings() -> Settings:
    settings = Settings()
    if not settings.database_url.startswith("postgresql"):
        raise ValueError("DATABASE_URL must be PostgreSQL in all non-test environments.")
    return settings
