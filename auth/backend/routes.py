"""Маршруты сервиса авторизации: login, logout, me."""

import base64
import hmac
import json
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel

from shared import structure_data

router = APIRouter()
AUTH_SECRET = os.environ.get('AUTH_SECRET', 'change-me-in-production')
COOKIE_NAME = 'hr_session'
COOKIE_DOMAIN = ''
COOKIE_PATH = '/'
COOKIE_MAX_AGE = 3600 * 24 * 7  # 7 дней


class LoginPayload(BaseModel):
    username: str
    password: str


def _make_session_cookie(name: str, exp_minutes: int = COOKIE_MAX_AGE) -> dict:
    """Создаёт cookie-параметры для hr_session (HttpOnly, HMAC-подпись)."""
    payload = json.dumps({"name": name, "exp": (datetime.now(timezone.utc) + timedelta(minutes=exp_minutes)).timestamp()}, ensure_ascii=False)
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip('=')
    signature = hmac.new(AUTH_SECRET.encode(), payload_b64.encode(), 'sha256').hexdigest()
    cookie_value = f"{payload_b64}.{signature}"
    return {
        'name': COOKIE_NAME,
        'value': cookie_value,
        'httponly': True,
        'samesite': 'lax',
        'path': COOKIE_PATH,
        'domain': COOKIE_DOMAIN,
        'max_age': exp_minutes,
    }


@router.post("/api/auth/login")
def login(payload: LoginPayload, response: Response) -> dict:
    """Авторизация: проверка учётной записи, установка cookie."""
    user = structure_data.auth_user_lookup(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail='Неверное имя пользователя или пароль')
    cookie = _make_session_cookie(user['name'])
    response.set_cookie(
        key=cookie['name'],
        value=cookie['value'],
        httponly=cookie['httponly'],
        samesite=cookie['samesite'],
        path=cookie['path'],
        domain=cookie['domain'],
        max_age=cookie['max_age'],
    )
    return {'name': user['name'], 'role': user['role']}


@router.post("/api/auth/logout")
def logout(response: Response) -> dict:
    """Выход: удаление cookie сессии."""
    response.set_cookie(
        key=COOKIE_NAME,
        value='',
        httponly=True,
        samesite='lax',
        path=COOKIE_PATH,
        max_age=0,
    )
    return {'status': 'ok'}


def _parse_cookie(cookie_header: str) -> dict | None:
    """Извлекает и проверяет cookie hr_session."""
    if not cookie_header:
        return None
    parts = cookie_header.split('; ')
    hr_session = None
    for part in parts:
        if part.startswith('hr_session='):
            hr_session = part[len('hr_session='):]
            break
    if not hr_session:
        return None
    try:
        if '.' not in hr_session:
            return None
        payload_b64, signature = hr_session.rsplit('.', 1)
        expected_sig = hmac.new(
            AUTH_SECRET.encode(), payload_b64.encode(), 'sha256'
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        missing_padding = len(payload_b64) % 4
        if missing_padding:
            payload_b64 += '=' * (4 - missing_padding)
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        data = json.loads(payload_bytes)
        if 'name' not in data or 'exp' not in data:
            return None
        return data
    except Exception:
        return None


@router.get("/api/auth/me")
def me(cookie: str = Header(default='', alias='Cookie')) -> dict:
    """Текущий пользователь по cookie hr_session: name, role, department."""
    session = _parse_cookie(cookie)
    if session is None:
        raise HTTPException(status_code=401, detail='Нет активной сессии')
    name = session['name']
    role = structure_data.role_of(name)
    # department — из БД
    with structure_data.pool.connection() as conn:
        dept = conn.execute(
            "SELECT department FROM employees WHERE name = %s", (name,)
        ).fetchone()
    department = dept['department'] if dept else ''
    return {'name': name, 'role': role, 'department': department}
