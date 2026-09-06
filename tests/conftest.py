import os

import pytest_asyncio

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["AI_PROVIDER"] = "mock"
os.environ["NEWS_PROVIDER"] = "mock"
os.environ["MARKET_DATA_PROVIDER"] = "mock"

from app.db import models  # noqa: E402, F401
from app.db.base import Base  # noqa: E402
from app.db.bootstrap import seed_demo_data  # noqa: E402
from app.db.session import engine  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def reset_database():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    await seed_demo_data()
    yield
