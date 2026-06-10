import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    return create_app()

@pytest.fixture()
def client(app):
    return TestClient(app)
