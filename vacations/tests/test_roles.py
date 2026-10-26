"""Видимость отпусков по роли (через auth-логин + cookie).

- top (Иван) видит всех.
- head (Алексей Ким) видит свои + заявки своих подчинённых (Сергей Волков).
"""
import requests


def test_head_sees_subordinate_vacation(auth_login, make_vacation, gateway):
    """Head (Алексей) видит заявку своего подчинённого Волкова и свою."""
    make_vacation("Сергей Волков")
    s = auth_login("alexey", "kim123")
    r = s.get(f"{gateway}/api/vacations")
    assert r.status_code == 200, r.text
    names = [v["employee"] for v in r.json()]
    assert "Сергей Волков" in names  # подчинённый
    assert "Алексей Ким" in names    # своя


def test_top_sees_all(auth_login, make_vacation, gateway):
    """Top (Иван) видит заявки всех сотрудников."""
    make_vacation("Ольга Романова")
    s = auth_login("ivan", "ivan123")
    r = s.get(f"{gateway}/api/vacations")
    assert r.status_code == 200, r.text
    names = [v["employee"] for v in r.json()]
    assert "Ольга Романова" in names
    assert "Иван Петров" in names


def test_upper_head_approves_deeper_subordinate(make_vacation, decide):
    """Вышестоящий руководитель (Мария) согласует заявку подчинённого «ниже» (Волков,
    подчинённый Алексея) — по постановке ролевой модели."""
    v, _ = make_vacation("Сергей Волков")
    r = decide(v["id"], "Мария Соколова", "head")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"


def test_head_cannot_approve_foreign(make_vacation, decide):
    """Head не может согласовать заявку не своего подчинённого (Иван не в дереве Марии)."""
    v, _ = make_vacation("Иван Петров")
    r = decide(v["id"], "Мария Соколова", "head")
    assert r.status_code == 403


def test_calendar_head_only_own_and_subordinate(auth_login, make_vacation, gateway):
    """Календарь head (Алексей) — только свои + подчинённые (Волков), не все сотрудники."""
    make_vacation("Сергей Волков")
    make_vacation("Ольга Романова")  # не подчиняется Алексею
    s = auth_login("alexey", "kim123")
    r = s.get(f"{gateway}/api/vacations/department/overlaps")
    assert r.status_code == 200, r.text
    names = {v["employee"] for v in r.json()["vacations"]}
    assert "Сергей Волков" in names     # подчинённый
    assert "Алексей Ким" in names       # своя
    assert "Ольга Романова" not in names  # чужой (не в дереве Алексея)


def test_calendar_top_sees_all(auth_login, make_vacation, gateway):
    """Календарь top (Иван) — все заявки."""
    make_vacation("Ольга Романова")
    s = auth_login("ivan", "ivan123")
    r = s.get(f"{gateway}/api/vacations/department/overlaps")
    assert r.status_code == 200, r.text
    names = {v["employee"] for v in r.json()["vacations"]}
    assert "Ольга Романова" in names
    assert "Иван Петров" in names


def test_employee_list_only_own(auth_login, make_vacation, gateway):
    """Сотрудник (Волков) в списке заявок видит только свои, не руководителя."""
    make_vacation("Сергей Волков")
    make_vacation("Алексей Ким")  # руководитель Волкова
    s = auth_login("volkov", "volkov123")
    r = s.get(f"{gateway}/api/vacations")
    assert r.status_code == 200, r.text
    names = [v["employee"] for v in r.json()]
    assert "Сергей Волков" in names
    assert "Алексей Ким" not in names


def test_employee_calendar_sees_own_and_manager(auth_login, make_vacation, gateway):
    """Сотрудник (Волков) в календаре видит свои даты и руководителя (Ким) — их отдел,
    но не других сотрудников (Ольга/Мария не в команде Волкова)."""
    make_vacation("Сергей Волков")
    make_vacation("Алексей Ким")
    make_vacation("Ольга Романова")
    s = auth_login("volkov", "volkov123")
    r = s.get(f"{gateway}/api/vacations/department/overlaps")
    assert r.status_code == 200, r.text
    names = {v["employee"] for v in r.json()["vacations"]}
    assert "Сергей Волков" in names
    assert "Алексей Ким" in names       # руководитель — одного отдела
    assert "Ольга Романова" not in names  # не в команде Волкова
    assert "Мария Соколова" not in names


def test_manager_and_top_see_employee_vacation(auth_login, make_vacation, gateway):
    """Заявку Волкова видят Ким (линейный руководитель) и Петров (вышестоящий)."""
    _, comment = make_vacation("Сергей Волков")
    for username, password in (("alexey", "kim123"), ("ivan", "ivan123")):
        s = auth_login(username, password)
        r = s.get(f"{gateway}/api/vacations")
        assert r.status_code == 200, r.text
        assert comment in {v["comment"] for v in r.json()}

