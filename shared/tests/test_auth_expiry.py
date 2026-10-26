"""Юнит-тесты на проверку срока действия сессии (hr_session cookie).

Сессия должна отвергаться, если exp в прошлом (иначе cookie живёт вечно).
"""
import base64
import hmac
import json
import time

from shared import auth as A


def _cookie(exp: float, name: str = "Иван Петров") -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"name": name, "exp": exp}).encode()
    ).decode().rstrip("=")
    sig = hmac.new(A.AUTH_SECRET.encode(), payload.encode(), "sha256").hexdigest()
    return f"hr_session={payload}.{sig}"


def test_expired_session_rejected():
    """Просроченная сессия (exp в прошлом) должна быть отвергнута."""
    cookie = _cookie(time.time() - 1000)
    assert A._parse_cookie(cookie) is None


def test_future_session_accepted():
    """Сессия с exp в будущем принимается."""
    data = A._parse_cookie(_cookie(time.time() + 1000))
    assert data is not None
    assert data["name"] == "Иван Петров"
