# HR Портал — демо-прототип (Module Federation + FastAPI)

Рабочий прототип целевой архитектуры HR-портала: единое окно (shell), в которое
HR-сервисы подключаются как независимые микросервисы (Module Federation remote + FastAPI API).

## Структура (после разделения на сервисы)

Каждый сервис — независимая единица (фронтенд-remote + свой бэкенд), собирается отдельно,
запускается через `docker compose`:

```
├── services/
│   ├── shell/                # Host-оболочка (React 18 + webpack MF; свой контейнер)
│   ├── auth/                 # Сервис авторизации/аутентификации (вход, сессия hr_session)
│   │   ├── frontend/         #   Remote «Вход» (/mf/auth/)
│   │   ├── backend/          #   FastAPI /api/auth/* (login/logout/me)
│   │   └── tests/            #   тесты авторизации
│   ├── vacations/
│   │   ├── frontend/         #   Remote «Отпуска» (exposes ./App, publicPath /mf/vacations/)
│   │   ├── backend/          #   Бэкенд «Отпуска» (FastAPI /api/vacations*, пересечения)
│   │   └── tests/            #   тесты сервиса (календарь, пересечения, лимит, роли) — через шлюз
│   └── structure/
│       ├── frontend/         #   Remote «Структура компании» (/mf/structure/)
│       ├── backend/          #   Бэкенд «Структура» (/api/structure*)
│       └── tests/            #   тесты сервиса — через шлюз
├── shared/                   # общее: auth (cookie hr_session, fallback X-User), db-пул, overlap, структура-данные
│   └── tests/                #   юнит-тесты общей логики (find_overlaps)
├── e2e/                      # дымовые Playwright-смоки (в образе hr-main-e2e на базе sogaz-auto-chrome, Nexus)
├── platform/gateway/         # API-шлюз nginx: /api/<key>/* → бэкенд, /mf/* → фронт
├── services.json             # реестр сервисов (shell подхватывает remotes в рантайме)
├── docs/                     # постановки и as-built доки по фичам
└── scripts/                  # cleanup_test_data.sh — очистка накопившихся тестовых данных
```

## Запуск (Docker Desktop)

```bash
docker compose up --build -d   # db + backend-* + frontend-* + gateway, затем http://localhost:8090
```

- Все сервисы (db, backend-structure/vacations/auth, frontend-shell/structure/vacations/auth, gateway)
  собираются и запускаются отдельными контейнерами; единая точка входа — шлюз на :8090.
- Данные — volume `hr-pg`; сброс: `docker compose down -v`.
- Автотесты (pytest): `python3 -m pytest services shared/tests -q` — идут через шлюз на :8090
  (он маршрутизирует /api/* на нужный бэкенд); перед прогоном чистить накопившиеся
  тестовые данные — `./scripts/cleanup_test_data.sh`.
- Дымовые e2e-смоки: `./e2e/run.sh` (см. `e2e/README.md`) — браузер из образа `sogaz-auto-chrome` через Nexus.
- Очистка накопившихся тестовых данных: `./scripts/cleanup_test_data.sh`.

## Локальная разработка

```bash
npm install
npm run build                      # shell + vacations + structure remote
uvicorn services.vacations.backend.app:app --port 8000   # backend конкретного сервиса
```

`webpack` закреплён на 5.111.1 (`overrides` в корневом package.json): с 5.112 `@module-federation/enhanced` не собирается.

## Как подключить новый сервис

1. Скопировать `services/<template>/frontend` (напр., `vacations`): свой `name`, `exposes`,
   `publicPath: /mf/<service>/`.
2. Свой бэкенд `services/<svc>/backend` по образцу `services/vacations/backend`
   (роутер + `init_<name>(pool)` в lifespan), свой DB-модуль.
3. Добавить сервис в `docker-compose.yml` (`frontend-<svc>`, `backend-<svc>`).
4. Прописать маршруты в `platform/gateway/nginx.conf` (`/api/<svc>/*` → бэкенд, `/mf/<svc>/` → фронт).
5. Добавить запись с полем `remote` в реестр `services.json` (в k8s — ConfigMap, `SERVICES_FILE`).
   Shell подгружает remote в рантайме по этой записи — пересобирать shell не нужно.

## Выбор технологий (open source, звёзды GitHub на 2026-10-23)

Keycloak 37k · Kong 44k (альтернатива APISIX 17k) · PostgreSQL · Module Federation 2.0 (`module-federation/core` 2.7k,
поверх webpack/Rspack). Отклонены: single-spa 14k (последний коммит февраль 2026), qiankun 17k (экосистема вокруг
umi/Ant), Frappe HRMS 9k и OrangeHRM 1k (GPL-3.0, монолиты), Backstage 35k (плагины Node/TS, собираются в одно
приложение — нет независимого деплоя). Готового «HR-портала с подключаемыми микросервисами» в open source нет:
shell пишется самим, готовые — только SSO, шлюз и БД.

## Авторизация и роли (пилот)

Сервис `auth` — форма входа (`/mf/auth/`), сессия = HttpOnly cookie `hr_session` (подписанный
HMAC-токен, SameSite=lax, 7 дней), роль хранится в БД `employees.role` и читается на каждом запросе.
Роли: `top` (видит всех + управляет), `head` (свои + подчинённые, согласует дерево), `employee`
(свои заявки; в календаре — свой отдел + руководитель). При 401 оболочка редиректит на `/mf/auth/`.

Демо-аккаунты: `ivan`/`ivan123` (top), `alexey`/`kim123` (head), `volkov`/`volkov123` (employee).
Структуру видят все одинаково (вся); отделы иерархические (HR → отдел Соколовой → Отдел Ким).

## Что намеренно упрощено в демо

- SSO: вход — локальный сервис auth (cookie hr_session) вместо Keycloak; в проде роль/логин ставит
  Kong после проверки JWT Keycloak. Для автотестов/автоматизации шлюз поддерживает fallback-заголовки
  `X-User`/`X-Roles`: в `platform/gateway/nginx.conf` они маппятся (пустой `X-User` → «Иван Петров» +
  роль `hr`), а бэкенды `current_user` принимают их при отсутствии cookie.
- Отдельные контейнеры в одном compose-стеке вместо Kubernetes (HPA, PDB, Helm — фаза 0 роадмапа).
- Один Postgres на демо; в проде — БД на сервис.
- Список заявок без пагинации в UI (API отдаёт до 200 за запрос, `limit`/`offset`).
- Отпуска: планирование только ежегодные (`type='annual'`), 2027, лимит 28 дней;
  календарь — интерактивный выбор периода (клик по дню, подсветка, старт не с выходного).
