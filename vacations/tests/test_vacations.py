"""Матрица прав согласования отпусков (сервис vacations, интеграция через шлюз)."""
from concurrent.futures import ThreadPoolExecutor

import urllib.parse

import requests


def hdr(name, roles=""):
    return {"X-User": urllib.parse.quote(name), "X-Roles": roles}


def test_manager_approves_subordinate(make_vacation, decide, employees):
    v, _ = make_vacation(employees["alexey"])
    r = decide(v["id"], employees["maria"])  # Мария — руководитель Алексея
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_manager_cannot_approve_foreign(make_vacation, decide, employees):
    v, _ = make_vacation(employees["ivan"])
    assert decide(v["id"], employees["maria"]).status_code == 403


def test_employee_cannot_approve(make_vacation, decide, employees):
    v, _ = make_vacation(employees["alexey"])
    assert decide(v["id"], employees["alexey"]).status_code == 403


def test_hr_approves_any(make_vacation, decide, employees):
    v, _ = make_vacation(employees["alexey"])
    assert decide(v["id"], employees["ivan"], roles="top").status_code == 200


def test_second_decision_conflict(make_vacation, decide, employees):
    v, _ = make_vacation(employees["alexey"])
    assert decide(v["id"], employees["maria"]).status_code == 200
    assert decide(v["id"], employees["maria"]).status_code == 409


def test_manager_sees_subordinates_vacations(make_vacation, list_vacations, employees):
    _, sub = make_vacation(employees["alexey"])
    _, own = make_vacation(employees["maria"])
    comments = {i["comment"] for i in list_vacations(employees["maria"], roles="head")}
    assert sub in comments
    assert own in comments


def test_manager_does_not_see_foreign_vacations(make_vacation, list_vacations, employees):
    _, foreign = make_vacation(employees["ivan"])
    comments = {i["comment"] for i in list_vacations(employees["maria"], roles="head")}
    assert foreign not in comments


def test_employee_sees_only_own(make_vacation, list_vacations, employees):
    _, own = make_vacation(employees["alexey"])
    _, other = make_vacation(employees["ivan"])
    comments = {i["comment"] for i in list_vacations(employees["alexey"], roles="head")}
    assert own in comments
    assert other not in comments


def test_decision_nonexistent_404(decide, employees):
    assert decide(999999999, employees["ivan"], roles="top").status_code == 404


def test_concurrent_hr_race(make_vacation, decide, employees):
    v, _ = make_vacation(employees["alexey"])
    with ThreadPoolExecutor(2) as ex:
        codes = sorted(
            ex.map(
                lambda a: decide(v["id"], employees["ivan"], roles="top", action=a).status_code,
                ["approve", "reject"],
            )
        )
    assert codes == [200, 409]
