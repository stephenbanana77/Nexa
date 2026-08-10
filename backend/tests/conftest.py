"""Test fixtures for Nexa backend."""
import os
import sys
import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DB_PATH = os.path.join(BACKEND_DIR, "test.db")
TEST_STORAGE_PATH = os.path.join(BACKEND_DIR, "test_storage")

# Switch to SQLite for tests
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["STORAGE_PATH"] = TEST_STORAGE_PATH
os.environ["ENABLE_RATE_LIMIT"] = "false"  # disable rate limiter in tests

sys.path.insert(0, BACKEND_DIR)

from main import app
from database import Base, engine
from database.session import SessionLocal


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    # Clean up test files — ignore errors (sandbox may prevent deletion)
    import shutil
    for f in [TEST_DB_PATH, TEST_STORAGE_PATH]:
        try:
            if os.path.exists(f):
                if os.path.isdir(f):
                    shutil.rmtree(f, ignore_errors=True)
                else:
                    os.remove(f)
        except OSError:
            pass


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Register + login, return headers with Bearer token."""
    client.post("/api/auth/register", json={
        "email": "test@nexa.io", "password": "test1234", "name": "Tester"
    })
    resp = client.post("/api/auth/login", json={
        "email": "test@nexa.io", "password": "test1234"
    })
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def project_id(client, auth_headers):
    resp = client.post("/api/projects", json={"name": "Test Project"}, headers=auth_headers)
    return resp.json()["id"]
