import pytest
from httpx import AsyncClient

from app.auth import create_access_token, decode_access_token
from app.models.athlete import Athlete


class TestLoginEndpoint:
    async def test_login_success(self, client: AsyncClient, athlete: Athlete):
        resp = await client.post(
            "/auth/login",
            json={"email": "test@marathon.dev", "password": "testpass"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert "expires_at" in data

    async def test_login_bad_password(self, client: AsyncClient, athlete: Athlete):
        resp = await client.post(
            "/auth/login",
            json={"email": "test@marathon.dev", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient, athlete: Athlete):
        resp = await client.post(
            "/auth/login",
            json={"email": "nobody@marathon.dev", "password": "testpass"},
        )
        assert resp.status_code == 401


class TestJWT:
    async def test_jwt_round_trip(self):
        athlete_id = "550e8400-e29b-41d4-a716-446655440000"
        token, expires_at = create_access_token(athlete_id)
        decoded = decode_access_token(token)
        assert decoded == athlete_id

    async def test_invalid_token_returns_none(self):
        result = decode_access_token("not.a.valid.token")
        assert result is None
