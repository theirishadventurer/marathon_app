from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token
from app.models.athlete import Athlete


@pytest.fixture
async def seeded_db(db: AsyncSession) -> AsyncSession:
    from app.seed.load_plan import seed_plan

    await seed_plan(db, plan_path="PLAN.md", password="testpass")
    return db


@pytest.fixture
async def seeded_client(seeded_db, client):
    return client


@pytest.fixture
async def seeded_auth_headers(seeded_db):
    result = await seeded_db.execute(select(Athlete).limit(1))
    athlete = result.scalar_one()
    token, _ = create_access_token(str(athlete.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_plan_today_requires_auth(seeded_client: AsyncClient):
    resp = await seeded_client.get("/plan/today")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_plan_today_returns_shape(
    seeded_client: AsyncClient, seeded_auth_headers: dict
):
    resp = await seeded_client.get("/plan/today", headers=seeded_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "date" in body
    assert isinstance(body["workouts"], list)
    assert body["coach_brief"] is None


@pytest.mark.asyncio
async def test_plan_week_returns_7_days(
    seeded_client: AsyncClient, seeded_auth_headers: dict
):
    resp = await seeded_client.get(
        "/plan/week", params={"date": "2026-10-19"}, headers=seeded_auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["days"]) == 7
    total_workouts = sum(len(d["workouts"]) for d in body["days"])
    assert total_workouts == 7


@pytest.mark.asyncio
async def test_plan_current_returns_shape(
    seeded_client: AsyncClient, seeded_auth_headers: dict
):
    resp = await seeded_client.get("/plan/current", headers=seeded_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "plan_name" in body
    assert "active_cycle" in body
