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
    return TestClient(app, raise_server_exceptions=False, follow_redirects=False)


@pytest.fixture()
def db(app):
    """A SQLAlchemy session that shares the same engine as the running app."""
    session = app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def admin_user(db):
    """Insert a boss admin user into the test database."""
    from app.models import AdminUser
    from app.security import hash_password
    user = AdminUser(username="boss", password_hash=hash_password("pw12345"))
    db.add(user)
    db.commit()
    return user


@pytest.fixture()
def logged_client(app, admin_user):
    """A test client that is already logged in as admin."""
    c = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
    c.post("/admin/login", data={"username": "boss", "password": "pw12345"})
    return c
