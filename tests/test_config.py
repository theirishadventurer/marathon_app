"""Fail-closed startup checks for production deployment.

These guard the two HIGH security findings:
  1. Hardcoded default JWT signing secret (token forgery / auth bypass).
  2. Known default login password seeded on every deploy.

In development/test (APP_ENV unset → "development") defaults are allowed so
the suite and local Docker dev keep working. In production they must raise.
"""

import pytest

from app.config import Settings


class TestSecretKeyFailClosed:
    def test_dev_default_secret_is_allowed(self):
        # Default app_env="development" — the in-repo default secret is fine.
        s = Settings()
        assert s.secret_key == "change-me-to-a-real-secret"
        assert s.is_production is False

    def test_explicit_dev_with_default_secret_ok(self):
        s = Settings(app_env="development", secret_key="change-me-to-a-real-secret")
        assert s.is_production is False

    def test_prod_with_default_secret_raises(self):
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            Settings(app_env="production", secret_key="change-me-to-a-real-secret")

    def test_prod_with_short_secret_raises(self):
        with pytest.raises(RuntimeError, match="too short"):
            Settings(app_env="production", secret_key="tooshort")

    def test_prod_with_strong_secret_ok(self):
        # 64 hex chars (== secrets.token_hex(32)) — should construct cleanly.
        strong = "a" * 64
        s = Settings(app_env="production", secret_key=strong)
        assert s.is_production is True
        assert s.secret_key == strong

    def test_prod_signal_is_case_insensitive(self):
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            Settings(app_env="PRODUCTION", secret_key="change-me-to-a-real-secret")


class TestSeedPasswordFailClosed:
    async def test_prod_default_seed_password_raises(self, db):
        from app.config import settings as live_settings
        from app.seed.load_plan import seed_plan

        # Force production for this call only, then restore.
        original = live_settings.app_env
        live_settings.app_env = "production"
        try:
            with pytest.raises(RuntimeError, match="SEED_PASSWORD"):
                await seed_plan(db, plan_path="PLAN.md", password="changeme123")
            with pytest.raises(RuntimeError, match="SEED_PASSWORD"):
                await seed_plan(db, plan_path="PLAN.md", password="")
        finally:
            live_settings.app_env = original

    async def test_dev_default_seed_password_allowed(self, db):
        # Default (development) env: seeding with any password works.
        from app.seed.load_plan import seed_plan

        counts = await seed_plan(db, plan_path="PLAN.md", password="testpass")
        assert counts["athletes"] == 1


def test_strava_config_defaults_empty():
    from app.config import Settings

    s = Settings()
    assert s.strava_client_id == ""
    assert s.strava_client_secret == ""
    assert s.strava_redirect_uri == ""
