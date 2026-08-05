"""Test fixtures for Nexa backend."""
import os
import sys
import pytest
from fastapi.testclient import TestClient

# Switch to SQLite for tests
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["STORAGE_PATH"] = "./test_storage"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import Base, engine
from database.session import SessionLocal


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Clean up test files
    for f in ["test.db", "test_storage"]:
        if os.path.exists(f):
            if os.path.isdir(f):
                import shutil; shutil.rmtree(f, ignore_errors=True)
            else:
                os.remove(f)


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
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def project_id(client, auth_headers):
    resp = client.post("/api/projects", json={"name": "Test Project"}, headers=auth_headers)
    return resp.json()["id"]
