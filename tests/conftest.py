import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app

# Use a separate in-memory database for tests
# This means tests never touch your real jobscribe.db
TEST_DATABASE_URL = "sqlite:///./test_jobscribe.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def override_get_db():
    """
    Replaces the real database session with a test one.
    FastAPI's dependency override system swaps this in
    automatically for every request made during tests.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    """
    Creates all tables before each test.
    Drops all tables after each test.
    This guarantees every test starts with a clean slate.
    """
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    """
    Provides a test client that makes real HTTP requests
    to your FastAPI app without needing a running server.
    """
    return TestClient(app)