"""Тесты лимита 28 дней отпуска на сотрудника (суммарно за календарный год)."""

import urllib.parse

import requests


def hdr(name: str, roles: str = ""):
    return {"X-User": urllib.parse.quote(name), "X-Roles": roles}


def post_vacation(base, name, start, end, comment):
    r = requests.post(
        f"{base}/api/vacations",
        json={"start": start, "end": end, "type": "annual", "comment": comment},
        headers=hdr(name),
    )
    return r


def test_28_day_limit_per_employee_per_year(backend):
    # 30 дней + сидовые дни сотрудника -> превышение лимита 28 (422).
    r = post_vacation(backend, "Мария Соколова", "2027-05-01", "2027-05-30", "lim-1")
    assert r.status_code == 422, r.text


def test_28_day_limit_not_exceeded(backend):
    # Итого 10 дней в 2027 (< 28) -> обе заявки создаются (Ольга, даты вне других тестов).
    u = "Ольга Романова"
    r1 = post_vacation(backend, u, "2027-09-01", "2027-09-05", "lim-ok1")
    assert r1.status_code == 201, r1.text
    r2 = post_vacation(backend, u, "2027-10-01", "2027-10-05", "lim-ok2")
    assert r2.status_code == 201, r2.text
