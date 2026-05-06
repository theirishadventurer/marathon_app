import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import create_access_token, hash_password
from app.config import settings
from app.deps import get_db
from app.main import app
from app.models import Base
from app.models.athlete import Athlete


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def athlete(db: AsyncSession) -> Athlete:
    a = Athlete(
        id=uuid.uuid4(),
        name="Test Runner",
        email="test@marathon.dev",
        password_hash=hash_password("testpass"),
        hr_zones_json={"z1": [0, 130], "z2": [131, 145]},
        pace_targets_json={"easy": "12:00-13:30"},
        injury_notes_md="No current injuries",
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


@pytest.fixture
async def auth_token(athlete: Athlete) -> str:
    from app.auth import create_access_token

    token, _ = create_access_token(str(athlete.id))
    return token


@pytest.fixture
async def auth_headers(auth_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
async def seeded_db(db: AsyncSession) -> AsyncSession:
    from app.seed.load_plan import seed_plan

    await seed_plan(db, plan_path="PLAN.md", password="testpass")
    return db


@pytest.fixture
async def seeded_client(seeded_db: AsyncSession, client: AsyncClient) -> AsyncClient:
    return client


@pytest.fixture
async def athlete_token(seeded_db: AsyncSession) -> str:
    result = await seeded_db.execute(select(Athlete).limit(1))
    athlete = result.scalar_one()
    token, _ = create_access_token(str(athlete.id))
    return token


@pytest.fixture
async def seeded_auth_headers(athlete_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {athlete_token}"}
