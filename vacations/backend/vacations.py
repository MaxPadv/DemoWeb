"""HR Portal demo — сервис «Отпуска» (независимый бэкенд, FastAPI + PostgreSQL)."""

from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from shared import auth, overlap, structure_data

pool = None

router = APIRouter()

SCHEMA = """
CREATE TABLE IF NOT EXISTS vacations (
    id         BIGSERIAL PRIMARY KEY,
    employee   TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date   DATE NOT NULL,
    days       INTEGER NOT NULL,
    type       TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'pending',
    comment    TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS vacations_employee_idx ON vacations (employee, id DESC);
"""

SEED = [
    ("Иван Петров", "2027-01-12", "2027-01-25", 14, "annual", "approved", "Новогодние каникулы"),
    ("Мария Соколова", "2027-03-02", "2027-03-08", 7, "annual", "pending", "Весенний отпуск"),
    ("Алексей Ким", "2027-05-12", "2027-05-18", 7, "annual", "pending", "Семейные обстоятельства"),
    ("Ольга Романова", "2027-03-05", "2027-03-10", 6, "annual", "pending", "Плановый отпуск"),
    ("Сергей Волков", "2027-05-10", "2027-05-15", 6, "annual", "pending", "Отпуск Волкова"),
]

COLS = "id, employee, start_date AS start, end_date AS \"end\", days, type, status, comment, created_at"


def init_vacations(p) -> None:
    global pool
    pool = p
    with p.connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(42)")
        conn.execute(SCHEMA)
        # Ограничения целостности (идемпотентно)
        conn.execute(
            "DO $$ BEGIN "
            "  IF NOT EXISTS (SELECT 1 FROM pg_constraint "
            "                 WHERE conname='vacations_type_check' AND conrelid='vacations'::regclass) THEN "
            "    ALTER TABLE vacations ADD CONSTRAINT vacations_type_check "
            "      CHECK (type IN ('annual', 'unpaid', 'study')); "
            "  END IF; "
            "END $$;"
        )
        conn.execute(
            "DO $$ BEGIN "
            "  IF NOT EXISTS (SELECT 1 FROM pg_constraint "
            "                 WHERE conname='vacations_status_check' AND conrelid='vacations'::regclass) THEN "
            "    ALTER TABLE vacations ADD CONSTRAINT vacations_status_check "
            "      CHECK (status IN ('pending', 'approved', 'rejected')); "
            "  END IF; "
            "END $$;"
        )
        conn.execute(
            "DO $$ BEGIN "
            "  IF NOT EXISTS (SELECT 1 FROM pg_constraint "
            "                 WHERE conname='vacations_days_check' AND conrelid='vacations'::regclass) THEN "
            "    ALTER TABLE vacations ADD CONSTRAINT vacations_days_check "
            "      CHECK (days >= 1); "
            "  END IF; "
            "END $$;"
        )
        if conn.execute("SELECT 1 FROM vacations LIMIT 1").fetchone() is None:
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO vacations (employee, start_date, end_date, days, type, status, comment)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    SEED,
                )


class VacationIn(BaseModel):
    start: date
    end: date
    type: Literal["annual", "unpaid", "study"] = "annual"
    comment: str = Field(default="", max_length=200)


class DecisionIn(BaseModel):
    action: Literal["approve", "reject"]


def _list_scope(user: auth.User) -> list[str]:
    """Скоп списка заявок: top/head — свои + подчинённые (дерево), employee — только свои."""
    if user.role == 'top' or user.role == 'head':
        return [user.name, *structure_data.subordinate_tree_names(user.name)]
    return [user.name]


@router.get("/api/vacations")
def list_vacations(
    user: auth.User = Depends(auth.current_user),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    names = _list_scope(user)
    if not names:
        return []
    placeholders = ",".join(["%s"] * len(names))
    where = f"WHERE type = 'annual' AND employee IN ({placeholders})"
    with pool.connection() as conn:
        return conn.execute(
            f"SELECT {COLS} FROM vacations {where} ORDER BY id DESC LIMIT %s OFFSET %s",
            [*names, limit, offset],
        ).fetchall()


@router.post("/api/vacations", status_code=201)
def create_vacation(payload: VacationIn, user: auth.User = Depends(auth.current_user)) -> dict:
    if payload.end < payload.start:
        raise HTTPException(status_code=422, detail="Дата окончания раньше даты начала")
    if payload.start.year != 2027 or payload.end.year != 2027:
        raise HTTPException(status_code=422, detail="Отпуск оформляется только за 2027 год")
    days = (payload.end - payload.start).days + 1
    if days > 60:
        raise HTTPException(status_code=422, detail="Максимум 60 календарных дней в одной заявке")
    if not structure_data.employee_exists(user.name):
        raise HTTPException(status_code=422, detail="Сотрудник отсутствует в структуре")
    year = payload.start.year
    with pool.connection() as conn:
        existing = conn.execute(
            "SELECT COALESCE(SUM(days), 0) AS total FROM vacations"
            " WHERE employee = %s AND status != 'rejected'"
            " AND EXTRACT(YEAR FROM start_date) = %s",
            (user.name, year),
        ).fetchone()["total"]
        if existing + days > 28:
            raise HTTPException(status_code=422, detail="Превышен лимит 28 дней отпуска за год")
        overlap = conn.execute(
            "SELECT 1 FROM vacations"
            " WHERE employee = %s AND status != 'rejected'"
            " AND start_date <= %s AND end_date >= %s"
            " LIMIT 1",
            (user.name, payload.end, payload.start),
        ).fetchone()
        if overlap:
            raise HTTPException(status_code=422, detail="Период пересекается с уже существующим отпуском")
        return conn.execute(
            "INSERT INTO vacations (employee, start_date, end_date, days, type, comment)"
            f" VALUES (%s, %s, %s, %s, %s, %s) RETURNING {COLS}",
            (user.name, payload.start, payload.end, days, payload.type, payload.comment),
        ).fetchone()


def _visible_scope(user: auth.User) -> list[str]:
    """Видимость отпусков (календарь/пересечения) по иерархии-командам:
    - руководитель (есть подчинённые): свои + дерево подчинённых;
    - лист-сотрудник: свои + непосредственный руководитель (их отдел);
    - top (корень): всё дерево (= все).
    Пользователь вне структуры → 404."""
    if not structure_data.employee_exists(user.name):
        raise HTTPException(status_code=404, detail="Пользователь не найден в структуре")
    subs = structure_data.subordinate_tree_names(user.name)
    if subs:
        return [user.name, *subs]
    mgr = structure_data.manager_name(user.name)
    return [user.name, mgr] if mgr else [user.name]


@router.get("/api/vacations/department")
def department_vacations(user: auth.User = Depends(auth.current_user)) -> list[dict]:
    names = _visible_scope(user)
    if not names:
        return []
    with pool.connection() as conn:
        placeholders = ",".join(["%s"] * len(names))
        return conn.execute(
            f"SELECT {COLS} FROM vacations WHERE employee IN ({placeholders}) ORDER BY id DESC",
            names,
        ).fetchall()


@router.get("/api/vacations/department/overlaps")
def department_vacations_overlaps(user: auth.User = Depends(auth.current_user)) -> dict:
    names = _visible_scope(user)
    if not names:
        return {"vacations": [], "overlaps": []}
    with pool.connection() as conn:
        placeholders = ",".join(["%s"] * len(names))
        selected = conn.execute(
            f"SELECT {COLS} FROM vacations WHERE employee IN ({placeholders}) ORDER BY id DESC",
            names,
        ).fetchall()
    considered = [v for v in selected if v["status"] != "rejected"]
    return {"vacations": selected, "overlaps": overlap.find_overlaps(considered)}


def _add_months(d: date, months: int) -> date:
    year, month = d.year, d.month
    total = year * 12 + month + months - 1
    return date(year=total // 12, month=total % 12 + 1, day=1)


@router.get("/api/vacations/department/calendar")
def department_calendar(
    user: auth.User = Depends(auth.current_user),
    start: date = Query(..., description="Window start"),
    months: int = Query(4, ge=1, le=24, description="Number of months"),
) -> dict:
    names = _visible_scope(user)
    if not names:
        return {"days": [], "employees": [], "conflict_days": []}
    with pool.connection() as conn:
        placeholders = ",".join(["%s"] * len(names))
        rows = conn.execute(
            f"SELECT {COLS} FROM vacations WHERE employee IN ({placeholders}) AND status != 'rejected'",
            names,
        ).fetchall()

    start_date = start
    end_date = _add_months(start_date, months) - timedelta(days=1)
    days = [
        (start_date + timedelta(days=i)).isoformat()
        for i in range((end_date - start_date).days + 1)
    ]

    employees = []
    day_occupancy: dict[str, set] = {}
    for v in rows:
        v_start = overlap._as_date(v["start"])
        v_end = overlap._as_date(v["end"])
        lo = max(v_start, start_date)
        hi = min(v_end, end_date)
        if lo > hi:
            continue
        overlapping = [d for d in days if lo <= date.fromisoformat(d) <= hi]
        existing = None
        for e in employees:
            if e["name"] == v["employee"]:
                existing = e
                break
        if existing is not None:
            existing["days"].extend(overlapping)
        else:
            employees.append({"name": v["employee"], "days": overlapping})
        for d in overlapping:
            day_occupancy.setdefault(d, set()).add(v["employee"])

    for e in employees:
        e["days"] = sorted(set(e["days"]))
    conflict_days = sorted([d for d, emps in day_occupancy.items() if len(emps) >= 2])
    return {"days": days, "employees": employees, "conflict_days": conflict_days}


@router.post("/api/vacations/{vacation_id}/decision")
def decide(vacation_id: int, payload: DecisionIn, user: auth.User = Depends(auth.current_user)) -> dict:
    new_status = "approved" if payload.action == "approve" else "rejected"
    if user.role != 'top':
        subs = structure_data.subordinate_tree_names(user.name)
        if not subs:
            raise HTTPException(status_code=403, detail="Решение принимает только HR или руководитель")
        with pool.connection() as conn:
            v = conn.execute(
                "SELECT employee FROM vacations WHERE id = %s", (vacation_id,)
            ).fetchone()
        if v is None:
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        if v["employee"] not in subs:
            raise HTTPException(status_code=403, detail="Нельзя согласовать заявку не вашего подчинённого")
    with pool.connection() as conn:
        row = conn.execute(
            f"UPDATE vacations SET status = %s WHERE id = %s AND status = 'pending' RETURNING {COLS}",
            (new_status, vacation_id),
        ).fetchone()
        if row is None:
            exists = conn.execute("SELECT 1 FROM vacations WHERE id = %s", (vacation_id,)).fetchone()
            raise HTTPException(
                status_code=409 if exists else 404,
                detail="Заявка уже обработана" if exists else "Заявка не найдена",
            )
        return row
