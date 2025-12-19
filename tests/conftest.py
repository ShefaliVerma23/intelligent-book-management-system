"""
Test configuration and fixtures
"""
import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.base import Base, get_db
from app.models.users import User
from app.models.books import Book
from app.models.reviews import Review

# Test database URL (SQLite for testing)
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def setup_database():
    """Set up test database - fresh for each test"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test"""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def async_client(setup_database) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        preferred_genres='["Fiction", "Science Fiction"]',
        is_active=True
    )
    user.set_password("testpassword123")
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin_user(db_session: AsyncSession) -> User:
    """Create a test admin user"""
    user = User(
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        is_active=True,
        is_admin=True
    )
    user.set_password("adminpassword123")
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_book(db_session: AsyncSession) -> Book:
    """Create a test book - matches actual Book model"""
    book = Book(
        title="Test Book",
        author="Test Author",
        genre="Fiction",
        year_published=2023,
        summary="A test book for testing purposes. This is a great book about testing."
    )
    
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    return book


@pytest_asyncio.fixture
async def test_book2(db_session: AsyncSession) -> Book:
    """Create a second test book"""
    book = Book(
        title="Another Test Book",
        author="Another Author",
        genre="Science Fiction",
        year_published=2022,
        summary="Another test book for testing recommendations."
    )
    
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    return book


@pytest_asyncio.fixture
async def test_review(db_session: AsyncSession, test_user: User, test_book: Book) -> Review:
    """Create a test review - matches actual Review model"""
    review = Review(
        book_id=test_book.id,
        user_id=test_user.id,
        rating=4.5,
        review_text="This book is really good and I enjoyed reading it."
    )
    
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)
    return review


@pytest_asyncio.fixture
async def auth_headers(async_client: AsyncClient, test_user: User) -> dict:
    """Get authentication headers for a test user"""
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "testpassword123"}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}
