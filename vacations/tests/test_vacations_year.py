"""Тест: отпускные заявки принимаются только за 2027 год."""

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


def test_vacation_rejected_outside_2027(backend):
    # 2026 и 2028 -> 422, 2027 -> 201. Сотрудник реальный (Ольга, в структуре).
    assert post_vacation(backend, "Ольга Романова", "2026-06-01", "2026-06-10", "yr-1").status_code == 422
    assert post_vacation(backend, "Ольга Романова", "2028-06-01", "2028-06-10", "yr-2").status_code == 422
    assert post_vacation(backend, "Ольга Романова", "2027-12-01", "2027-12-02", "yr-3").status_code == 201
