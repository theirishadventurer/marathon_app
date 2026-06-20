from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # `extra="ignore"`: SEED_PASSWORD lives in .env but is consumed directly via
    # os.environ in app/seed/load_plan.py, not as a Settings field. Without this,
    # pydantic-settings raises extra_forbidden on that (and any future) env key.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+asyncpg://marathon:marathon@db:5432/marathon"
    secret_key: str = "change-me-to-a-real-secret"
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = ""
    garmin_ingest_token: str = ""
    garmin_ingest_athlete_email: str = ""
    tz: str = "America/New_York"
    jwt_expiry_days: int = 30

    # Deployment environment signal. Set APP_ENV=production on Railway to enable
    # fail-closed startup checks. Defaults to "development" so local Docker dev
    # and the pytest suite keep working with the in-repo defaults.
    app_env: str = "development"

    # Production additions
    web_origin: str = "*"  # locked down via Railway env in prod
    garmin_username: str = ""
    garmin_password: str = ""

    DEFAULT_SECRET_KEY: ClassVar[str] = "change-me-to-a-real-secret"

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Railway's Postgres plugin gives `postgresql://...`; SQLAlchemy async needs `postgresql+asyncpg://...`
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )

        # Fail closed in production: never sign JWTs with the publicly-known
        # in-repo default secret, and never accept a weak (<32 char) secret.
        if self.is_production:
            if self.secret_key == self.DEFAULT_SECRET_KEY:
                raise RuntimeError(
                    "SECRET_KEY is the in-repo default in production. Set a real "
                    "SECRET_KEY (e.g. `python -c \"import secrets; "
                    'print(secrets.token_hex(32))"`) in the Railway environment.'
                )
            if len(self.secret_key) < 32:
                raise RuntimeError(
                    "SECRET_KEY is too short for production (must be >= 32 chars). "
                    "Generate one with `python -c \"import secrets; "
                    'print(secrets.token_hex(32))"`.'
                )
            if not self.garmin_ingest_token:
                raise RuntimeError(
                    "GARMIN_INGEST_TOKEN is unset in production. Generate one with "
                    "`python -c \"import secrets; print(secrets.token_urlsafe(32))\"` "
                    "and set it in the Railway environment."
                )


settings = Settings()
