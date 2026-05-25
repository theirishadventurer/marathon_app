from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://marathon:marathon@db:5432/marathon"
    secret_key: str = "change-me-to-a-real-secret"
    seed_password: str = "marathon"
    anthropic_api_key: str = ""
    tz: str = "America/New_York"
    jwt_expiry_days: int = 30

    # Production additions
    web_origin: str = "*"  # locked down via Railway env in prod
    garmin_username: str = ""
    garmin_password: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Railway's Postgres plugin gives `postgresql://...`; SQLAlchemy async needs `postgresql+asyncpg://...`
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )


settings = Settings()
