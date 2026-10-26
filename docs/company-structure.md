# Постановка: сервис «Структура компании»

Ветка: `feature/company-structure`
Тип: новый HR-сервис демо-портала, по аналогии с сервисом отпусков (`vacations`).
Цель: линейная структура сотрудников, которая пробрасывается в остальные сервисы
(руководитель видит своих подчинённых и согласовывает их отпуска).

## 1. Микрофронтенд `remotes/structure`

Копия по образцу `remotes/vacations` (Module Federation remote), изменения:
- `webpack.config.js`: `name: 'structure'`, `publicPath: '/mf/structure/'`,
  `filename: 'remoteEntry.js'`, `exposes: { './App': './src/StructureApp' }`,
  `shared: { react, react-dom }` singleton (как у vacations).
- `src/StructureApp.tsx` — отображает структуру компании: дерево/список сотрудников
  (линейная цепочка руководитель→подчинённые) с должностью и руководителем.
  Данные из `GET /api/structure`.
- `src/api.ts` — типы и fetch к `/api/structure` и `/api/structure/subordinates`.
- `src/index.ts` (standalone), `src/standalone.tsx`, `src/styles.css`, `package.json`,
  `tsconfig.json` — как у vacations (package `structure-remote`).
- Все упоминания `vacations` → `structure` / «Структура компании».

## 2. Backend (в том же FastAPI-приложении `backend/`)

Модуль `backend/structure.py` (по образцу `backend/main.py`), подключается в `backend/main.py`:
- Таблица `employees`: `id BIGSERIAL PK, name TEXT, position TEXT, department TEXT,
  manager_id BIGINT NULL REFERENCES employees(id)` (linear: у каждого один manager_id,
  у главы NULL), `created_at`.
- SEED (при старте, как у vacations): линейная структура из 3 уровней. Текущий
  демо-пользователь «Иван Петров» (`X-User` из шлюза) должен быть РУКОВОДИТЕЛЕМ,
  у которого есть подчинённые.
- Endpoints:
  - `GET /api/structure` → список сотрудников (плоский, с `manager_id`) или дерево.
  - `GET /api/structure/subordinates` → подчинённые текущего пользователя (по `X-User`).

## 3. Реестр сервисов

В `backend/services.json` добавить:
```json
{ "key": "structure", "title": "Структура компании", "description": "Оргструктура и подчинённость.", "status": "active", "version": "0.1.0", "remote": { "name": "structure", "entry": "/mf/structure/remoteEntry.js", "module": "./App" } }
```
Записи benefits/onboarding/time (planned) не трогать.

## 4. Интеграция с vacations (проброс структуры)

В `backend/main.py`, эндпоинт `POST /api/vacations/{id}/decision`:
- Пользователь с ролью `hr` — как сейчас, может принимать решение по любой заявке.
- Пользователь БЕЗ роли `hr`, но являющийся руководителем: может принимать решение
  только по заявкам своих подчинённых (из `GET /api/structure/subordinates`);
  по чужому сотруднику — `403`.
- Не ломать существующую защиту от гонки (`status='pending'`, 409).

## 5. Сборка и деплой

- `scripts/build.js`: `workspaces = ['shell', 'remotes/vacations', 'remotes/structure']`.
- Корневой `package.json` `workspaces`: добавить `remotes/structure`.
- `Dockerfile`: во runtime-стадии добавить
  `COPY --from=frontend /app/remotes/structure/dist /usr/share/nginx/html/mf/structure`.
- `nginx.conf.template`: без изменений (`/mf/*` и `/api/*` уже покрыты).
- npm-зависимости ставятся через `.npmrc` (registry nexus) — ничего менять не нужно.

## 6. Критерии приёмки

1. `docker compose up --build` поднимается без ошибок.
2. `GET /api/structure` и `GET /api/structure/subordinates` отдают JSON.
3. В shell появляется сервис «Структура компании»; клик открывает remote с деревом.
4. Руководитель согласовывает отпуск своего подчинённого; чужой сотрудник — 403
   (если не `hr`).

## Что НЕ делать

- Не пересобирать shell (подключение нового сервиса — только реестр + деплой remote).
- Не менять nginx-конфиг и другие сервисы (vacations) кроме указанной проверки в decision.
- Не трогать `package-lock.json` вручную (обновляется npm).

## Рефакторинг (выполнен после реализации)

После подключения структуры проведён рефакторинг backend и порядка вкладок:

- `backend/vacations.py` — сервис «Отпуска» вынесен из main.py в отдельный модуль
  (роутер, схема, сид, `init_vacations(pool)`), симметрично `backend/structure.py`.
- `backend/auth.py` — общий `User`/`current_user` (разбор X-User/X-Roles), используется
  и отпусками, и структурой.
- `backend/main.py` — тонкая сборка приложения: пул соединений, lifespan (вызов
  init всех сервисов), подключение роутеров, только app-level эндпоинты
  (`/api/health`, `/api/me`, `/api/services`).
- `backend/services.json` — порядок изменён: первым идёт `structure` («Структура компании»),
  вторым — `vacations`; shell рендерит вкладки в порядке реестра.
- `backend/test_api.py` — удалён как устаревший smoke-скрипт; его проверки (401 без
  заголовков, 404, гонка двух HR → 200/409) перенесены в `tests/test_api.py` (pytest).
- Автотесты в `tests/` (pytest, `python3 -m pytest tests/ -q`): 15 тестов — реестр,
  структура, матрица прав, smoke.
- Сборка: Dockerfile (two-stage, frontend build + runtime), npm через `.npmrc`
  `registry=https://nexus.sogaz.ru/npm/`, apt/pip через Nexus-прокси.
- Порты для тестов: `8000:8000` (backend напрямую, для кастомных X-User/X-Roles).
- Кодовый агент omp переведён на модель `qwen/qwen3.6-35B-A3B-AWQ-int4` (провайдер qwen)
  — DeepSeek-V4-Flash зависал на генерации кода.
