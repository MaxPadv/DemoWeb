"""Юнит-тесты чистой функции пересечений отпусков (без БД)."""

import pytest

from shared.overlap import find_overlaps


def vac(eid, emp, start, end):
    return {"id": eid, "employee": emp, "start": start, "end": end}


def test_overlap_found():
    a = vac(1, "Анна", "2026-06-01", "2026-06-10")
    b = vac(2, "Борис", "2026-06-05", "2026-06-15")
    res = find_overlaps([a, b])
    assert len(res) == 1
    assert res[0]["start"] == "2026-06-05"
    assert res[0]["end"] == "2026-06-10"
    assert {res[0]["employee_a"], res[0]["employee_b"]} == {"Анна", "Борис"}


def test_no_overlap():
    a = vac(1, "Анна", "2026-06-01", "2026-06-05")
    b = vac(2, "Борис", "2026-06-06", "2026-06-10")
    assert find_overlaps([a, b]) == []


def test_touching_boundary_is_overlap():
    # end_a == start_b — inclusive: пересечение одного дня.
    a = vac(1, "Анна", "2026-06-01", "2026-06-05")
    b = vac(2, "Борис", "2026-06-05", "2026-06-10")
    res = find_overlaps([a, b])
    assert len(res) == 1
    assert res[0]["start"] == "2026-06-05"
    assert res[0]["end"] == "2026-06-05"


def test_single_no_overlap():
    assert find_overlaps([vac(1, "Анна", "2026-06-01", "2026-06-10")]) == []


def test_same_employee_not_compared():
    # Отпуска одного сотрудника друг с другом не сравниваются.
    a1 = vac(1, "Анна", "2026-06-01", "2026-06-10")
    a2 = vac(2, "Анна", "2026-06-05", "2026-06-15")
    assert find_overlaps([a1, a2]) == []


def test_empty():
    assert find_overlaps([]) == []


def test_overlap_accepts_date_objects():
    # Из БД даты приходят объектами date (не строками) — функция должна выдерживать оба.
    from datetime import date

    a = vac(1, "Анна", date(2026, 6, 1), date(2026, 6, 10))
    b = vac(2, "Борис", date(2026, 6, 5), date(2026, 6, 15))
    res = find_overlaps([a, b])
    assert len(res) == 1
    assert res[0]["start"] == "2026-06-05"
    assert res[0]["end"] == "2026-06-10"


def test_overlaps_deduped():
    # Дубликаты одинаковых (employee, start, end) не создают дублирующиеся пересечения.
    a1 = vac(1, "Анна", "2026-06-01", "2026-06-10")
    a2 = vac(2, "Анна", "2026-06-01", "2026-06-10")  # дубль Анны
    b = vac(3, "Борис", "2026-06-05", "2026-06-15")
    res = find_overlaps([a1, a2, b])
    assert len(res) == 1
