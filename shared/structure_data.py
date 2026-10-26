"""Общая модель оргструктуры (employees) для бэкендов-сервисов.

Оба сервиса («Структура» и «Отпуска») используют одну БД hr и разделяют логику
структуры: схема/сид сотрудников, подчинённые, состав отдела. Отдельный сервис
выделен, чтобы при независимых бэкендах не дублировать логику.
"""

from urllib.parse import unquote
import hashlib

from fastapi import HTTPException

pool = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    position    TEXT NOT NULL DEFAULT '',
    department  TEXT NOT NULL DEFAULT '',
    manager_id  BIGINT REFERENCES employees(id),
    role        TEXT NOT NULL DEFAULT 'employee',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS employees_manager_idx ON employees (manager_id);

-- Аккаунты для входа
CREATE TABLE IF NOT EXISTS auth_users (
    id              BIGSERIAL PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    employee_id     BIGINT REFERENCES employees(id)
);
"""

# Линейная структура: глава (manager_id NULL) -> руководитель -> сотрудники.
SEED = [
    (1, "Иван Петров", "Директор по персоналу", "HR", None),
    (2, "Мария Соколова", "Руководитель отдела", "отдел Соколовой", 1),
    (3, "Алексей Ким", "HR-менеджер", "Отдел Ким", 2),
    (4, "Ольга Романова", "HR-аналитик", "отдел Соколовой", 2),
    (5, "Сергей Волков", "Специалист по кадрам", "Отдел Ким", 3),
]

# Сид ролей сотрудников
SEED_ROLES = [
    (1, "Иван Петров", "top"),
    (2, "Мария Соколова", "head"),
    (3, "Алексей Ким", "head"),
    (4, "Ольга Романова", "employee"),
    (5, "Сергей Волков", "employee"),
]

# Сид аккаунтов (username -> employee_id)
AUTH_SEED = [
    ("ivan", 1, "ivan123"),
    ("alexey", 3, "kim123"),
    ("volkov", 5, "volkov123"),
]

AUTH_SALT = b'hr-auth-v1'


def _hash_password(password: str) -> str:
    """SHA-256 + salt → hex-строка."""
    return hashlib.pbkdf2_hmac('sha256', password.encode(), AUTH_SALT, 100000).hex()


def init_structure(p) -> None:
    global pool
    pool = p
    with p.connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(43)")
        conn.execute(SCHEMA)
        # Миграция: добавляем role, если колонка отсутствует
        conn.execute(
            "DO $$ BEGIN "
            "  IF NOT EXISTS (SELECT 1 FROM information_schema.columns "
            "                 WHERE table_name='employees' AND column_name='role') THEN "
            "    ALTER TABLE employees ADD COLUMN role TEXT NOT NULL DEFAULT 'employee'; "
            "  END IF; "
            "END $$;"
        )
        # Ограничения целостности (идемпотентно)
        conn.execute(
            "DO $$ BEGIN "
            "  IF NOT EXISTS (SELECT 1 FROM pg_constraint "
            "                 WHERE conname='employees_name_key' AND conrelid='employees'::regclass) THEN "
            "    ALTER TABLE employees ADD CONSTRAINT employees_name_key UNIQUE (name); "
            "  END IF; "
            "END $$;"
        )
        conn.execute(
            "DO $$ BEGIN "
            "  IF NOT EXISTS (SELECT 1 FROM pg_constraint "
            "                 WHERE conname='employees_role_check' AND conrelid='employees'::regclass) THEN "
            "    ALTER TABLE employees ADD CONSTRAINT employees_role_check "
            "      CHECK (role IN ('top', 'head', 'employee')); "
            "  END IF; "
            "END $$;"
        )
        # Сид сотрудников (только если таблица пуста)
        if conn.execute("SELECT 1 FROM employees LIMIT 1").fetchone() is None:
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO employees (id, name, position, department, manager_id)"
                    " VALUES (%s, %s, %s, %s, %s)",
                    SEED,
                )
            conn.execute(
                "SELECT setval('employees_id_seq', (SELECT MAX(id) FROM employees))"
            )
        # Обновляем роли (идемпотентно)
        for emp_id, name, role in SEED_ROLES:
            conn.execute(
                "UPDATE employees SET role = %s WHERE id = %s",
                (role, emp_id),
            )
        # Обновляем отделы (идемпотентно; таблица может быть уже заполнена)
        for emp_id, _name, _pos, dept, _mgr in SEED:
            conn.execute(
                "UPDATE employees SET department = %s WHERE id = %s",
                (dept, emp_id),
            )
        # Сид аккаунтов (если нет)
        existing_users = conn.execute(
            "SELECT COUNT(*) AS cnt FROM auth_users"
        ).fetchone()["cnt"]
        if existing_users == 0:
            for username, employee_id, password in AUTH_SEED:
                pw_hash = _hash_password(password)
                conn.execute(
                    "INSERT INTO auth_users (username, password_hash, employee_id)"
                    " VALUES (%s, %s, %s)",
                    (username, pw_hash, employee_id),
                )


def current_name(x_user: str | None) -> str:
    if not x_user:
        raise HTTPException(status_code=401, detail="Нет данных пользователя от шлюза")
    return unquote(x_user)


def role_of(name: str) -> str:
    """Роль сотрудника по имени; по умолчанию 'employee'."""
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT role FROM employees WHERE name = %s", (name,)
        ).fetchone()
        if row is None:
            return 'employee'
        return row['role']


def manager_name(name: str) -> str | None:
    """Имя непосредственного руководителя сотрудника (или None)."""
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT e2.name FROM employees e1 JOIN employees e2 ON e1.manager_id = e2.id"
            " WHERE e1.name = %s",
            (name,),
        ).fetchone()
        return row['name'] if row else None


def employee_exists(name: str) -> bool:
    """Есть ли сотрудник с таким именем в оргструктуре."""
    with pool.connection() as conn:
        return (
            conn.execute("SELECT 1 FROM employees WHERE name = %s", (name,)).fetchone()
            is not None
        )


def employee_by_username(username: str) -> tuple | None:
    """По username → (employee_id, name, role) или None."""
    with pool.connection() as conn:
        row = conn.execute(
            """SELECT au.employee_id, e.name, e.role
               FROM auth_users au
               JOIN employees e ON e.id = au.employee_id
               WHERE au.username = %s""",
            (username,),
        ).fetchone()
        return row


def auth_user_lookup(username: str, password: str) -> dict | None:
    """Проверка учётной записи по username+password.
    Возвращает (employee_id, name, role) или None."""
    with pool.connection() as conn:
        row = conn.execute(
            """SELECT au.employee_id, e.name, e.role, au.password_hash
               FROM auth_users au
               JOIN employees e ON e.id = au.employee_id
               WHERE au.username = %s""",
            (username,),
        ).fetchone()
        if row is None:
            return None
        expected_hash = _hash_password(password)
        if row['password_hash'] != expected_hash:
            return None
        return {
            'employee_id': row['employee_id'],
            'name': row['name'],
            'role': row['role'],
        }


def subordinate_names(name: str) -> list[str]:
    """Имена непосредственных подчинённых."""
    with pool.connection() as conn:
        me = conn.execute(
            "SELECT id FROM employees WHERE name = %s", (name,)
        ).fetchone()
        if me is None:
            return []
        rows = conn.execute(
            "SELECT name FROM employees WHERE manager_id = %s", (me["id"],)
        ).fetchall()
        return [r["name"] for r in rows]


def subordinate_tree_names(name: str) -> list[str]:
    """Все подчинённые рекурсивно (по дереву manager_id).

    Вышестоящий руководитель согласует заявки не только прямых подчинённых,
    но и подчинённых «ниже» (по постановке ролевой модели).
    """
    with pool.connection() as conn:
        result: list[str] = []
        frontier = [name]
        while frontier:
            cur = frontier.pop()
            me = conn.execute(
                "SELECT id FROM employees WHERE name = %s", (cur,)
            ).fetchone()
            if me is None:
                continue
            rows = conn.execute(
                "SELECT name FROM employees WHERE manager_id = %s", (me["id"],)
            ).fetchall()
            for r in rows:
                result.append(r["name"])
                frontier.append(r["name"])
        return result


def department_names(name: str) -> list[str]:
    """Имена сотрудников отдела пользователя; 404, если пользователя нет в структуре."""
    with pool.connection() as conn:
        dept = conn.execute(
            "SELECT department FROM employees WHERE name = %s", (name,)
        ).fetchone()
        if dept is None:
            raise HTTPException(status_code=404, detail="Пользователь не найден в структуре")
        rows = conn.execute(
            "SELECT name FROM employees WHERE department = %s", (dept["department"],)
        ).fetchall()
        return [r["name"] for r in rows]


def all_employees() -> list[dict]:
    with pool.connection() as conn:
        return conn.execute(
            "SELECT id, name, position, department, manager_id FROM employees ORDER BY id"
        ).fetchall()


def subordinates_of(name: str) -> list[dict]:
    with pool.connection() as conn:
        me = conn.execute(
            "SELECT id FROM employees WHERE name = %s", (name,)
        ).fetchone()
        if me is None:
            return []
        return conn.execute(
            "SELECT id, name, position, department, manager_id FROM employees"
            " WHERE manager_id = %s ORDER BY id",
            (me["id"],),
        ).fetchall()
