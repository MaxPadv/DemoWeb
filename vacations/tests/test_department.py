"""Интеграционные тесты эндпоинта отпусков отдела /api/vacations/department."""

import urllib.parse

import requests


def hdr(name: str, roles: str = ""):
    return {"X-User": urllib.parse.quote(name), "X-Roles": roles}


def test_department_vacations_includes_dept(backend, make_vacation, employees):
    # Сотрудник отдела видит отпуска всех сотрудников своего отдела (общий график).
    _, comment = make_vacation(employees["alexey"])
    r = requests.get(f"{backend}/api/vacations/department", headers=hdr(employees["maria"]))
    assert r.status_code == 200
    assert any(i["comment"] == comment for i in r.json())


def test_department_vacations_user_not_in_structure_404(backend):
    r = requests.get(f"{backend}/api/vacations/department", headers=hdr("Неизвестный"))
    assert r.status_code == 404
