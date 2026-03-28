# tests/conftest.py
import os
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database import Base
from app.config import settings

# Import existing models so Base.metadata includes them.
# SystemConfig is added to this file in Task 2 Step 2.3a (after the model is created).
from app.models.source import Source
from app.models.content import Content
from app.models.subscriber import Subscriber
from app.models.send_log import SendLog

# Derive test DB URL: use TEST_DATABASE_URL env var if set,
# otherwise append "_test" to the production database name.
_prod_url = settings.database_url
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    _prod_url.rsplit("/", 1)[0] + "/" + _prod_url.rsplit("/", 1)[1] + "_test",
)


@pytest_asyncio.fixture
async def db():
    """Async DB session backed by a real PostgreSQL test database.
    Creates all tables before each test, drops them after — no persistent state.
    Requires TEST_DATABASE_URL to point to an existing (empty) PostgreSQL database.
    """
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
