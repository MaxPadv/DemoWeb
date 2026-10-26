"""Самопересечение: нельзя создать отпуск, пересекающийся с собственным существующим
(согласованным или ожидающим). Проверка на бэкенде → 422.

Сотрудники — только из оргструктуры (заявки вне структуры запрещены), поэтому
используем реальных (Ольга/Волков) с датами вне авто-диапазона других тестов.
"""
import urllib.parse

import requests

OLGA = "Ольга Романова"
VOLKOV = "Сергей Волков"


def hdr(name, roles=""):
    return {"X-User": urllib.parse.quote(name), "X-Roles": roles}


def test_cannot_overlap_own_vacation(backend):
    r1 = requests.post(
        f"{backend}/api/vacations",
        json={"start": "2027-08-10", "end": "2027-08-10", "type": "annual", "comment": "auto-self-a"},
        headers=hdr(OLGA),
    )
    assert r1.status_code == 201, r1.text
    r2 = requests.post(
        f"{backend}/api/vacations",
        json={"start": "2027-08-10", "end": "2027-08-11", "type": "annual", "comment": "auto-self-b"},
        headers=hdr(OLGA),
    )
    assert r2.status_code == 422, r2.text


def test_can_create_non_overlapping_own(backend):
    r1 = requests.post(
        f"{backend}/api/vacations",
        json={"start": "2027-08-01", "end": "2027-08-01", "type": "annual", "comment": "auto-non-a"},
        headers=hdr(VOLKOV),
    )
    assert r1.status_code == 201, r1.text
    r2 = requests.post(
        f"{backend}/api/vacations",
        json={"start": "2027-08-05", "end": "2027-08-05", "type": "annual", "comment": "auto-non-b"},
        headers=hdr(VOLKOV),
    )
    assert r2.status_code == 201, r2.text


def test_non_structure_employee_rejected(backend):
    """Заявка на сотрудника вне структуры отклоняется (422)."""
    r = requests.post(
        f"{backend}/api/vacations",
        json={"start": "2027-09-01", "end": "2027-09-01", "type": "annual", "comment": "auto-ghost"},
        headers=hdr("Призрак Неизвестный"),
    )
    assert r.status_code == 422
