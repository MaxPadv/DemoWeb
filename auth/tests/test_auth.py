"""Тесты сервиса авторизации: login (верный/неверный пароль), me по cookie, logout."""
import requests


def test_login_valid(auth_session):
    s, r = auth_session("ivan", "ivan123")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Иван Петров"
    assert body["role"] == "top"
    assert "hr_session" in s.cookies


def test_login_valid_head(auth_session):
    s, r = auth_session("alexey", "kim123")
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "head"


def test_login_wrong_password(auth_session):
    _, r = auth_session("ivan", "wrongpass")
    assert r.status_code == 401


def test_login_unknown_user(auth_session):
    _, r = auth_session("nobody", "x")
    assert r.status_code == 401


def test_me_by_cookie(auth_session, gateway):
    s, _ = auth_session("alexey", "kim123")
    r = s.get(f"{gateway}/api/auth/me")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Алексей Ким"
    assert body["role"] == "head"
    assert "department" in body


def test_me_no_cookie(gateway):
    r = requests.get(f"{gateway}/api/auth/me")
    assert r.status_code == 401


def test_logout_clears_session(auth_session, gateway):
    s, _ = auth_session("ivan", "ivan123")
    r = s.post(f"{gateway}/api/auth/logout")
    assert r.status_code == 200
    r2 = s.get(f"{gateway}/api/auth/me")
    assert r2.status_code == 401
