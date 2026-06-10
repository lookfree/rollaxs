import pytest
from fastapi.testclient import TestClient
from app.security import hash_password
from app.models import AdminUser


def login(client, password="pw12345"):
    return client.post("/admin/login", data={"username": "boss", "password": password})


def test_login_flow(client, db, admin_user):
    assert client.get("/admin/").status_code == 303          # 未登录跳 login
    r = login(client, "wrong")
    assert "用户名或密码错误" in r.text
    r = login(client)
    assert r.status_code == 303 and r.headers["location"] == "/admin/"
    assert client.get("/admin/").status_code == 200
    client.get("/admin/logout")
    assert client.get("/admin/").status_code == 303


def test_login_rate_limit(client, db, admin_user):
    for _ in range(11):
        r = login(client, "wrong")
    assert r.status_code == 429
