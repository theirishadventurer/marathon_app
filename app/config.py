from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://marathon:marathon@db:5432/marathon"
    secret_key: str = "change-me-to-a-real-secret"
    seed_password: str = "marathon"
    anthropic_api_key: str = ""
    tz: str = "America/New_York"
    jwt_expiry_days: int = 30


settings = Settings()
