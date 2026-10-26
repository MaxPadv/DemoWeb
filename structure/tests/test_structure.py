"""Сервис «Структура компании»: реестр сервисов и оргструктура (интеграция через шлюз)."""
import urllib.parse

import requests


def hdr(name, roles=""):
    return {"X-User": urllib.parse.quote(name), "X-Roles": roles}


def test_health(gateway):
    r = requests.get(f"{gateway}/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_services_contains_structure(gateway):
    r = requests.get(f"{gateway}/api/services", headers=hdr("Иван Петров"))
    services = {s["key"]: s for s in r.json()}
    assert "structure" in services and "vacations" in services
    assert services["structure"]["status"] == "active"
    assert services["structure"]["remote"]["module"] == "./App"


def test_structure_tree(gateway, employees):
    r = requests.get(f"{gateway}/api/structure")
    employees_list = r.json()
    assert len(employees_list) >= 5
    by_name = {e["name"]: e for e in employees_list}
    assert by_name[employees["ivan"]]["manager_id"] is None
    assert by_name[employees["maria"]]["manager_id"] == by_name[employees["ivan"]]["id"]
    assert by_name[employees["alexey"]]["manager_id"] == by_name[employees["maria"]]["id"]


def test_structure_departments(gateway, employees):
    """Поле department отражает отдел/команду сотрудника (по иерархии-командам)."""
    r = requests.get(f"{gateway}/api/structure")
    by_name = {e["name"]: e for e in r.json()}
    assert by_name[employees["ivan"]]["department"] == "HR"
    assert by_name[employees["maria"]]["department"] == "отдел Соколовой"
    assert by_name[employees["alexey"]]["department"] == "Отдел Ким"
    assert by_name["Сергей Волков"]["department"] == "Отдел Ким"
    assert by_name["Ольга Романова"]["department"] == "отдел Соколовой"

