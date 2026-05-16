import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app

# Import all models so SQLAlchemy creates all tables
from app.models import (          # add this block
    Job,
    CompanyResearch,
    ReadinessAssessment,
    PrepRoadmap,
    InterviewQuestion
)

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
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    test_client = TestClient(app)
    # Set a fixed session cookie for all tests
    test_client.cookies.set("jobscribe_session", "test-session-uuid-1234")
    return TestClient(app)
