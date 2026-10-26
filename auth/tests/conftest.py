"""Фикстуры тестов сервиса авторизации (интеграция через API-шлюз)."""
import os

import pytest
import requests

GATEWAY = os.environ.get("HR_GATEWAY", "http://localhost:8090")

IVAN = "Иван Петров"    # top, username ivan / ivan123
ALEXEY = "Алексей Ким"  # head, username alexey / kim123


@pytest.fixture
def gateway():
    return GATEWAY


@pytest.fixture
def backend():
    return GATEWAY


@pytest.fixture
def auth_session():
    """Логин и возврат сессии (requests.Session с cookie hr_session)."""
    def _login(username: str, password: str):
        s = requests.Session()
        r = s.post(f"{GATEWAY}/api/auth/login", json={"username": username, "password": password})
        return s, r
    return _login
