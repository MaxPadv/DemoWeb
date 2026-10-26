# Схема БД HR-портала (СОГАЗ, демо)

> **Важно:** этот документ описывает **фактическую** схему БД и отражает, где и как она используется.
> При **любом изменении схемы** (новая колонка/таблица/индекс/ограничение/сид) — **обновите этот файл**.
> Источник правды по схеме: `shared/structure_data.py` (employees, auth_users) и
> `services/vacations/backend/vacations.py` (vacations).

Установленные ограничения целостности (идемпотентные миграции в `init_structure`/`init_vacations`):
`employees.name` UNIQUE (`employees_name_key`), `employees.role` CHECK IN (top/head/employee),
`vacations.type` CHECK IN (annual/unpaid/study), `vacations.status` CHECK IN (pending/approved/rejected),
`vacations.days` CHECK >= 1.

## Обзор

СУБД: PostgreSQL 16 (`postgres:16-alpine`, контейнер `hr-main-db-1`), БД `hr`, пользователь `hr`.

Одна общая БД, разделяемая тремя независимыми бэкендами (`structure`, `auth`, `vacations`), каждый запускает
свою инициализацию схемы (`init_structure` / `init_vacations`) через `CREATE TABLE IF NOT EXISTS`.
Схема = 3 таблицы: `employees`, `auth_users`, `vacations`.

| Таблица | Назначение | Определена в | Создаёт |
|---|---|---|---|
| `employees` | Оргструктура (сотрудники, иерархия, роль, отдел) | `shared/structure_data.py` | `init_structure` |
| `auth_users` | Учётные записи для входа | `shared/structure_data.py` | `init_structure` |
| `vacations` | Заявки на отпуск | `services/vacations/backend/vacations.py` | `init_vacations` |

Подключение: `shared/db.py` → `make_pool()` (psycopg_pool, dict_row), пул разделяется между сервисами через
общую БД.

---

## Таблицы

### employees — сотрудники / оргструктура

| Колонка | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | bigint | PK, `nextval('employees_id_seq')` | Идентификатор сотрудника |
| `name` | text | NOT NULL | ФИО. **Не имеет UNIQUE** — фактический ключ-идентификатор по коду (см. замечания) |
| `position` | text | NOT NULL DEFAULT `''` | Должность |
| `department` | text | NOT NULL DEFAULT `''` | Отдел (текстовый, денормализован) |
| `manager_id` | bigint | FK → `employees(id)` (само-ссылка, NULL = глава) | Непосредственный руководитель (иерархия) |
| `role` | text | NOT NULL DEFAULT `'employee'` | Роль: `top` / `head` / `employee` |
| `created_at` | timestamptz | NOT NULL DEFAULT `now()` | Момент создания |

Индексы: `employees_pkey` (id), `employees_manager_idx` (manager_id).
Ограничения: `employees_manager_id_fkey` (manager_id → employees.id).

Сид (`SEED`, идемпотентный, только если таблица пуста): 5 сотрудников (Иван Петров `top` → Мария Соколова `head` → ... ).
Роли и отделы дополнительно обновляются идемпотентно из `SEED_ROLES` / `SEED`.

### auth_users — учётные записи для входа

| Колонка | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | bigint | PK, `nextval('auth_users_id_seq')` | Идентификатор записи |
| `username` | text | NOT NULL, **UNIQUE** | Логин |
| `password_hash` | text | NOT NULL | PBKDF2-HMAC-SHA256 + salt (`AUTH_SALT`), hex |
| `employee_id` | bigint | FK → `employees(id)` | Связь с сотрудником (может быть NULL) |

Индексы: `auth_users_pkey` (id), `auth_users_username_key` (username, UNIQUE).
Ограничения: `auth_users_employee_id_fkey` (employee_id → employees.id).
Сид (`AUTH_SEED`): `ivan`(→Иван Петров), `alexey`(→Алексей Ким), `volkov`(→Сергей Волков).

### vacations — заявки на отпуск

| Колонка | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | bigint | PK, `nextval('vacations_id_seq')` | Идентификатор заявки |
| `employee` | text | NOT NULL | ФИО сотрудника. **НЕ FK** на `employees` (см. замечания) |
| `start_date` | date | NOT NULL | Начало отпуска |
| `end_date` | date | NOT NULL | Конец отпуска |
| `days` | integer | NOT NULL | Число календарных дней (`end - start + 1`) |
| `type` | text | NOT NULL | Тип: `annual` / `unpaid` / `study` |
| `status` | text | NOT NULL DEFAULT `'pending'` | `pending` / `approved` / `rejected` |
| `comment` | text | NOT NULL DEFAULT `''` | Комментарий (max 200 при создании) |
| `created_at` | timestamptz | NOT NULL DEFAULT `now()` | Момент создания |

Индексы: `vacations_pkey` (id), `vacations_employee_idx` (employee, id DESC).
Сид (`SEED`, если таблица пуста): 5 заявок.

---

## Связи (ER-описание)

```
employees (само-ссылка, иерархия)
    │  manager_id ──▶ employees(id)        (голова: manager_id = NULL)
    │
    └──employee_id ◀── auth_users          (auth_users.employee_id → employees.id)
        1 : 1 (один логин на сотрудника, N-к-1 фактически)

vacations.employee ──?── employees.name     (НЕТ FK! связь только по значению/имени)
```

- **employees — само-ссылка** `manager_id → employees.id`: образует дерево оргструктуры. Глава (`Иван Петров`) имеет `manager_id = NULL`.
- **auth_users → employees**: `employee_id` → `employees.id`. Один сотрудник может иметь несколько логинов или ни одного (employee_id NULL).
- **vacations → employees**: **связи на уровне БД нет**. `vacations.employee` — текстовая копия `employees.name`, совпадение обеспечивается только прикладным кодом (`structure_data.employee_exists`, `_list_scope` и др.).

---

## Использование (кто читает / пишет)

### employees

| Где | Что делает |
|---|---|
| `structure_data.init_structure` | Создаёт таблицу, сидит сотрудников/роли/отделы (WRITE) |
| `structure_data.all_employees` | Читает всех (READ) — используется `structure/backend/app.py: /api/structure` |
| `structure_data.subordinates_of` | Прямые подчинённые (READ) — `structure: /api/structure/subordinates` |
| `structure_data.role_of(name)` | Роль сотрудника по имени (READ) — `shared/auth.py` (cookie), `auth: /me` |
| `structure_data.manager_name`, `subordinate_names`, `subordinate_tree_names`, `department_names`, `employee_exists`, `employee_by_username`, `auth_user_lookup` | Различные чтения по имени/подчинённым/отделу (READ) — используются `auth` и `vacations` |

### auth_users

| Где | Что делает |
|---|---|
| `structure_data.init_structure` | Сидит аккаунты `AUTH_SEED` (WRITE) |
| `structure_data.auth_user_lookup(username, password)` | Проверка логина/пароля при входе (READ) — `auth: /api/auth/login` |
| `structure_data.employee_by_username` | Стафф по username (READ) |

### vacations

| Где | Что делает |
|---|---|
| `vacations.init_vacations` | Создаёт таблицу, сидит заявки (WRITE) |
| `list_vacations` (`GET /api/vacations`) | Читает `annual` по скопу (READ) |
| `create_vacation` (`POST /api/vacations`) | Пишет заявку, проверяет лимит 28 дней/год и пересечения (WRITE+READ) |
| `decide` (`POST /api/vacations/{id}/decision`) | `UPDATE status` на `approved`/`rejected` только из `pending` (WRITE) |
| `department_vacations`, `department_vacations_overlaps`, `department_calendar` | Календарь/пересечения по видимости (READ) |

**Ролевая модель (определяет скоп чтения/видимости):** `role` в `employees` (`top`/`head`/`employee`) + дерево
`manager_id`. `top`/`head` видят себя + всё дерево подчинённых; `employee` — только себя (список) либо себя +
руководителя (календарь, `_visible_scope`).

---

## Замечания по модели

1. **`vacations.employee` — текст без FK.** Денормализация по `employees.name`: связь держится только значением,
   в БД нет ограничения целостности. Риск: рассинхронизация при переименовании/удалении сотрудника, «висячие»
   заявки. Исправление связывается только прикладным кодом (`employee_exists`). Оптимально: `employee_id BIGINT
   REFERENCES employees(id)` + джойн по имени.

2. **`employees.name` не UNIQUE, но используется как де-факто ключ.** Множество функций (`role_of`, `manager_name`,
   `employee_exists`, `subordinate_tree_names`, `department_names`, скопы в `vacations`) адресуют сотрудника **по
   имени**, а не по `id`. Два сотрудника с одинаковым именем сломают логику. Рекомендуется `UNIQUE(name)`.

3. **`auth_users.employee_id` и `vacations.employee` — два разных способа связать данные с сотрудником.**
   `auth_users` связывает по `id` (корректно), `vacations` — по имени (нет). Непоследовательность.

4. **`employees.department` — текстовая денормализация.** Отдел хранится строкой в каждой строке, а не справочником
   `departments`. Переименование отдела = массовое обновление. Для демо ок, для продакшена — отдельная таблица.

5. **Нет CHECK-ограничений на enum-полях.** `role` (`top/head/employee`), `vacations.type` (`annual/unpaid/study`),
   `vacations.status` (`pending/approved/rejected`) — просто `TEXT`, валидация только в коде (Pydantic `Literal` в
   `vacations.py`) и частично (FK-вид). Опечатка в БД не отловится.

6. **`vacations.days` — вычисляемое значение (`end - start + 1`), но хранится и не пересчитывается при обновлении.**
   При изменении дат (через UPDATE) `days` не пересчитывается автоматически — потенциальный рассинхрон.

7. **Хардкод на 2027 год.** `create_vacation` жёстко проверяет `start.year == 2027` (лимит 28 дней/год тоже).
   Схема не рассчитана на многолетние данные.

8. **Лимит 28 дней/год и пересечения** реализованы только в прикладном коде (`vacations.py`), без ограничений БД —
   гонки между параллельными запросами возможны (нет транзакционной изоляции/замков на этот счёт).

9. **`manager_id` без циклической защиты.** Само-ссылка допускает циклы в иерархии (A→B→A), что может зациклить
   рекурсивные обходы `subordinate_tree_names`.

---

*Документ отражает состояние схемы на момент написания. Обновляйте при изменении схемы.
Проверка фактической схемы: `docker exec hr-main-db-1 psql -U hr -d hr -c '\d <table>'`.*
