"""
CloudSage Test Configuration and Fixtures.
Provides isolated in-memory SQLite database session and test data helpers.
"""

import sys
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Append project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.core.database import Base


@pytest.fixture(scope="session")
def engine():
    """Create in-memory SQLite engine with thread safety for FastAPI TestClient."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )


@pytest.fixture(scope="function")
def db_session(engine):
    """Yield isolated database session for each test function."""
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)
