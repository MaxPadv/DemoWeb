"""Общие компоненты авторизации: User с role, current_user из cookie/HMAC или X-User."""

import base64
import hmac
import json
import os
import time
from urllib.parse import unquote

from fastapi import Header, HTTPException
from pydantic import BaseModel

from . import structure_data

AUTH_SECRET = os.environ.get('AUTH_SECRET', 'change-me-in-production')


class User(BaseModel):
    name: str
    roles: list[str]
    role: str = 'employee'

    @property
    def is_hr(self) -> bool:
        return self.role == 'top'


def _parse_cookie(cookie_header: str) -> dict | None:
    """Извлекает и проверяет cookie hr_session.
    Формат: base64({name, exp}).hmac_sha256_signature"""
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
        # Формат: payload_b64.signature
        if '.' not in hr_session:
            return None
        payload_b64, signature = hr_session.rsplit('.', 1)
        # Проверяем подпись HMAC
        expected_sig = hmac.new(
            AUTH_SECRET.encode(), payload_b64.encode(), 'sha256'
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        # Декодируем payload
        try:
            # base64 url-safe padding
            missing_padding = len(payload_b64) % 4
            if missing_padding:
                payload_b64 += '=' * (4 - missing_padding)
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
        except Exception:
            return None
        data = json.loads(payload_bytes)
        if 'name' not in data or 'exp' not in data:
            return None
        # ponytail: проверяем истечение сессии (иначе просроченная cookie живёт вечно)
        if float(data['exp']) < time.time():
            return None
        return data
    except Exception:
        return None


def current_user(
    x_user: str | None = Header(default=None),
    x_roles: str = Header(default=''),
    cookie: str = Header(default='', alias='Cookie'),
) -> User:
    # Приоритет 1: cookie hr_session с HMAC
    if cookie:
        session = _parse_cookie(cookie)
        if session is not None:
            name = unquote(session['name'])
            role = structure_data.role_of(name)
            roles = [role]
            return User(name=name, roles=roles, role=role)

    # Приоритет 2: X-User/X-Roles (для автотестов)
    if x_user:
        name = unquote(x_user)
        roles = [r.strip() for r in x_roles.split(',') if r.strip()]
        role = roles[0] if roles else 'employee'
        return User(name=name, roles=roles, role=role)

    raise HTTPException(status_code=401, detail='Нет данных пользователя от шлюза')
