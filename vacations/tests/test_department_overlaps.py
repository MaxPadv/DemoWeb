"""Интеграционные тесты эндпоинта пересечений отдела /api/vacations/department/overlaps."""

import urllib.parse

import requests


def hdr(name: str, roles: str = ""):
    return {"X-User": urllib.parse.quote(name), "X-Roles": roles}


def test_department_overlaps_structure(backend, make_vacation, employees):
    # Два отпуска разных сотрудников отдела с одинаковым периодом — пересекаются.
    make_vacation(employees["ivan"], start="2027-06-01", end="2027-06-01")
    make_vacation(employees["maria"], start="2027-06-01", end="2027-06-01")
    r = requests.get(
        f"{backend}/api/vacations/department/overlaps", headers=hdr(employees["maria"])
    )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body.get("vacations"), list)
    assert isinstance(body.get("overlaps"), list)


def test_department_overlaps_finds_conflict(backend, make_vacation, employees):
    make_vacation(employees["ivan"], start="2027-06-02", end="2027-06-02")
    make_vacation(employees["maria"], start="2027-06-02", end="2027-06-02")
    # top (Иван) видит всех → пересечение Иван↔Мария находится
    r = requests.get(
        f"{backend}/api/vacations/department/overlaps", headers=hdr(employees["ivan"], roles="top")
    )
    assert r.status_code == 200
    overlaps = r.json()["overlaps"]
    names = {employees["ivan"], employees["maria"]}
    assert any(
        {o["employee_a"], o["employee_b"]} == names for o in overlaps
    )
