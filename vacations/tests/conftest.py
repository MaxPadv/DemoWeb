"""Фикстуры тестов сервиса vacations (integration через API-шлюз).

Данные только добавляются (append-only, не удаляются после теста); уникальный
comment-маркер обеспечивает изоляцию.
"""
import os
import urllib.parse
import uuid
from datetime import date, timedelta

import pytest
import requests

GATEWAY = os.environ.get("HR_GATEWAY", "http://localhost:8090")

IVAN = "Иван Петров"
MARIA = "Мария Соколова"   # руководитель (подчинённые: Алексей, Ольга)
ALEXEY = "Алексей Ким"     # рядовой, без подчинённых

LEDGER = {"vacations": []}

# модульный счётчик дефолтных дат — уникален на весь прогон (иначе тесты,
# создающие отпуска одному сотруднику, сталкиваются на проверке самопересечения).
_DATE_COUNTER = {"n": 0}


def hdr(name: str, roles: str = ""):
    return {"X-User": urllib.parse.quote(name), "X-Roles": roles}


@pytest.fixture
def gateway():
    return GATEWAY


@pytest.fixture
def backend():
    return GATEWAY


@pytest.fixture
def employees():
    return {"ivan": IVAN, "maria": MARIA, "alexey": ALEXEY}


@pytest.fixture(scope="session")
def ledger():
    return LEDGER


@pytest.fixture
def make_vacation(backend, ledger):
    created = []

    def _make(user: str, roles: str = "", comment: str | None = None, start: str | None = None, end: str | None = None):
        comment = comment or f"auto-{uuid.uuid4().hex[:10]}"
        # дефолтная дата авто-уникальна (модульный счётчик), иначе повторные create
        # одного сотрудника сталкиваются на проверке самопересечения.
        _DATE_COUNTER["n"] += 1
        s = start or (date(2027, 6, 1) + timedelta(days=_DATE_COUNTER["n"])).isoformat()
        e = end or s
        r = requests.post(
            f"{backend}/api/vacations",
            json={"start": s, "end": e, "type": "annual", "comment": comment},
            headers=hdr(user, roles),
        )
        assert r.status_code == 201, r.text
        v = r.json()
        created.append((v["id"], comment, user))
        return v, comment

    yield _make
    ledger["vacations"].extend(created)


@pytest.fixture
def decide(backend):
    def _decide(vid: int, user: str, roles: str = "", action: str = "approve"):
        return requests.post(
            f"{backend}/api/vacations/{vid}/decision",
            json={"action": action},
            headers=hdr(user, roles),
        )
    return _decide


@pytest.fixture
def list_vacations(backend):
    def _list(user: str, roles: str = ""):
        r = requests.get(f"{backend}/api/vacations", headers=hdr(user, roles))
        assert r.status_code == 200, r.text
        return r.json()
    return _list


@pytest.fixture
def auth_login(backend):
    """Логин через auth-сервис -> requests.Session с cookie hr_session."""
    def _login(username: str, password: str):
        s = requests.Session()
        r = s.post(
            f"{backend}/api/auth/login",
            json={"username": username, "password": password},
        )
        assert r.status_code == 200, r.text
        return s
    return _login
