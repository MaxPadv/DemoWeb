"""Тесты эндпоинта календаря пересечений отдела /api/vacations/department/calendar."""

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
    assert r.status_code == 201, r.text
    return r.json()


def calendar(base, user, start, months=4):
    r = requests.get(
        f"{base}/api/vacations/department/calendar",
        params={"start": start, "months": months},
        headers=hdr(user),
    )
    return r


def test_calendar_structure(backend, employees):
    r = calendar(backend, employees["maria"], "2027-01-01", 4)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body.get("days"), list)
    assert isinstance(body.get("employees"), list)
    assert isinstance(body.get("conflict_days"), list)
    assert len(body["days"]) > 0


def test_calendar_conflict_days(backend, employees):
    # Мария 01-05.07 и Алексей 03-07.07 (2027) пересекаются 03-05.07.
    post_vacation(backend, employees["maria"], "2027-07-01", "2027-07-05", "cal-m")
    post_vacation(backend, employees["alexey"], "2027-07-03", "2027-07-07", "cal-a")
    r = calendar(backend, employees["maria"], "2027-07-01", 4)
    assert r.status_code == 200
    days = r.json()["conflict_days"]
    assert "2027-07-03" in days and "2027-07-05" in days


def test_calendar_no_conflict(backend, employees):
    # Окно без отпусков отдела (далёкий год) -> conflict_days пусто.
    r = calendar(backend, employees["maria"], "2038-01-01", 4)
    assert r.status_code == 200
    assert r.json()["conflict_days"] == []
