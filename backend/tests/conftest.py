
from app.core.config import settings
from app.models.base import Base
from app.db.session import get_db
from app.main import app
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient
from typing import AsyncGenerator, Generator
import pytest
import asyncio
---

# Backend Tests

```python
# backend/tests/conftest.py
"""
Pytest configuration and fixtures.
"""


# Test database URL
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    settings.DATABASE_URL.split("/")[-1],
    "claimlens_test"
)

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_database():
    """Set up test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Get test database session."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Get test HTTP client."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Test user data."""
    return {
        "email": "test@example.com",
        "password": "TestPass123!",
        "full_name": "Test User"
    }


@pytest.fixture
async def authenticated_client(client: AsyncClient, test_user_data: dict):
    """Get authenticated test client."""
    # Register user
    await client.post("/api/v1/auth/register", json=test_user_data)

    # Login
    response = await client.post("/api/v1/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    })

    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    return client
