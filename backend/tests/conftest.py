import asyncio
import pytest
import pytest_asyncio # Import pytest_asyncio
from typing import AsyncGenerator, Generator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport # Import ASGITransport

from backend.database import Base, get_db as app_get_db # Import Base from your app
from backend.main import app # Your FastAPI app instance

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create a new SQLAlchemy engine for testing
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

# Create a new sessionmaker for testing
TestSessionLocal = sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)

# Custom event_loop fixture is removed. pytest-asyncio handles the loop.

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """
    Create tables before running tests and drop them after.
    This runs once per session.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Tables are in-memory, so they are gone when the engine is disposed.
    # If using a persistent test DB, you'd drop tables here.
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="function") # Changed to pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a transactional database session for each test function.
    Rolls back transactions by default.
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()

    async_session = TestSessionLocal(bind=connection)

    yield async_session

    await async_session.close()
    if transaction.is_active:
        await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture(scope="function") # Changed to pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provides a test client for the FastAPI application, with database session override.
    """
    # Override the get_db dependency for the FastAPI app
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[app_get_db] = override_get_db

    transport = ASGITransport(app=app) # Use imported ASGITransport
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up dependency overrides
    del app.dependency_overrides[app_get_db]
