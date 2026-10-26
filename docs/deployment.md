# Регламент деплоя и независимости сервисов HR-портала

Статус: **документация** (целевая архитектура вне пилота). Основа для будущего CI/CD.

## Ключевое решение: сервисы независимы, в т.ч. по бэкенду

Каждый HR-сервис («Структура компании», «Отпуска» и будущие) — **полноценная независимая
единица**: свои фронтенд (микрофронтенд-remote), свой **бэкенд** (API), своя схема/данные,
свой **version** и свой **деплой/пайплайн**. Это соответствует лучшей практике для
микросервисов/Module Federation — независимое развёртывание и версионирование каждого сервиса.

### Бэкенд: отдельный на сервис (решение)

- **Не один общий бэкенд.** У каждого сервиса — **свой бэкенд-сервис** (отдельный деплой,
  своя версия, своя схема/БД или выделенный namespace/схема), свой API-контракт под `/api/<key>/*`.
- Общими остаются только **платформенные** компоненты: API-шлюз (nginx/Kong), SSO/auth (Keycloak),
  реестр сервисов (`services.json` → ConfigMap), мониторинг. Это не бизнес-логика сервисов.
- Бэкенд каждого сервиса сейчас — **отдельный FastAPI-контейнер** (`services/<svc>/backend`),
  общая логика — в `shared/` (auth, db, overlap, structure_data). Это соответствует целевой
  архитектуре «бэкенд на сервис» в рамках пилот-репо.

## Архитектура (целевая)

```
панель (shell, React 18, агрегатор, без бизнес-логики)
   │  реестр services.json (ConfigMap) — подхватывает remotes и бэкенд-маршруты в рантайме
   ├── /mf/structure/  → remote «Структура»  +  /api/structure/* → бэкенд structure
   ├── /mf/vacations/  → remote «Отпуска»    +  /api/vacations/* → бэкенд vacations
   └── ... (новые сервисы подключаются реестром, shell не пересобирается)
шлюз (nginx/Kong) маршрутизирует /api/<key>/* → бэкенд сервиса; /.mf → статика remote
```

- **Shell** — только агрегатор: навигация, SSO-заглушка/Keycloak, ErrorBoundary, загрузка remotes
  по реестру. НЕ содержит бизнес-логики, пересобирается только при изменении оболочки.
- **Каждый remote** — независимый артефакт: свой build (`/mf/<service>/` статика), **свой version**,
  свой деплой. Изменение сервиса → пересборка/деплой **только этого** remote (+его бэкенд).
- **Каждый бэкенд** — независимый деплой и version; контракт `/api/<key>/*`.

## Версионирование и отображение версий (для CI/CD)

- **Свой version (semver) у каждого сервиса** (frontend-remote и его бэкенд).
- Версия отображается **внутри страницы самого сервиса** (заголовок сервиса: «Запланировать
  отпуск vacations@0.1.0», «Структура» — своя). Это маркер развёрнутой версии сервиса.
- Версия **НЕ** отображается в общих/переходных местах: левое меню сервисов (nav), экран выбора
  сервисов «Отпуска», «← К выбору сервиса». Т.к. во вкладках может быть несколько микрофронтов —
  версия каждой подписывается у конкретного сервиса, а не на общих панелях.
- Бейдж версии вычисляется/подставляется из версии артефакта сервиса (в CI/CD — из тега/версии
  образа/артефакта), не хардкодится в разметке.

## CI/CD (перспектива, отдельный пайплайн на сервис)

- На **каждый сервис** — свой пайплайн: сборка frontend-remote (статика → /mf/<service>/, артефакт
  в Nexus/Harbor) + сборка бэкенда (образ). Свой version/тег, свои автотесты (pytest + e2e).
- Shell — свой пайплайн; пересобирается редко.
- Канареечный/поэтапный деплой бэкендов, независимый rollback по сервису.
- Хранилище артефактов: образы — Harbor (Nexus-прокси для npm/pip), статика — Nexus raw/object storage.
- Окружения: dev → stg → prod; конфигурация через ConfigMap/секреты (SERVICES_FILE, DSN, SSO).

## Прод-контур (для нагрузки 10k+)

k8s + HPA для каждого бэкенда, Kong/APISIX шлюз, Keycloak OIDC SSO, БД-на-сервис (или общая БД с
отдельными схемами), Redis (кэш/сессии), observability (метрики/логи/трейсы), подача статики
remotes через CDN/nginx. Всё — по независимым сервисам.

## Текущее состояние (пилот)

Проведён **рефакторинг на независимые сервисы** (в рамках пилот-репо): каждый сервис
(«Структура», «Отпуска») — **отдельный бэкенд-контейнер** (`services/<svc>/backend`) + **отдельный
фронтенд-remote** (`services/<svc>/frontend`), общая логика — в `shared/` (auth, db, overlap,
структура). Плюс **платформенный auth-сервис** (SSO-заглушка демо): `services/auth/backend`
(логин/кука `hr_session`) и `services/auth/frontend` (экран входа, remote `/mf/auth/`).
Отдельные контейнеры: `db`, `backend-structure`, `backend-vacations`, `backend-auth`,
`frontend-shell|structure|vacations|auth`, `gateway` (nginx-шлюз маршрутизирует `/api/<key>/*` →
бэкенды, `/mf/*` → фронтенды, `/` → shell). Собираются отдельно, запускаются через `docker compose up --build -d`
(точка входа — шлюз на :8090). Функциональность и API-контракты не менялись (тесты 33/33 через шлюз).
Переход к отдельным GitLab-проектам/пайплайнам (CI/CD на сервис, свои версии/деплой) — следующие шаги.

## Как это работает и запускается (DevOps, пилот)

Модель: единый compose-стек из 9 контейнеров; каждый сервис — самостоятельная единица
(собирается отдельно, своя версия/деплой); точка входа одна — API-шлюз :8090.

### Контейнеры (docker compose up --build -d)

```
1. db                   postgres:16-alpine, общая БД hr (бэкенды шарят её)
2. backend-structure    FastAPI «Структура»  -> /api/structure*
3. backend-vacations    FastAPI «Отпуска»    -> /api/vacations* (+календарь/пересечения, /api/services, /api/health)
4. backend-auth         FastAPI auth (SSO-заглушка) -> /api/auth/login|logout, /api/me (кука hr_session)
5. frontend-shell       nginx со статикой shell (host, /)
6. frontend-structure   nginx со статикой remote /mf/structure/
7. frontend-vacations   nginx со статикой remote /mf/vacations/
8. frontend-auth        nginx со статикой remote /mf/auth/ (экран входа)
9. gateway              nginx-шлюз, единственный порт наружу 8090
```

### Маршрутизация (platform/gateway/nginx.conf)

- Все в одной сети compose; сервисные имена резолвятся через Docker DNS.
- Шлюз маршрутизирует по префиксу (`^~`, без обязательного слэша):
  /api/structure* → backend-structure:8000; /api/vacations* → backend-vacations:8000;
  /api/auth/* и /api/me → backend-auth:8000; /api/services и /api/health → backend-vacations:8000;
  /mf/structure/* → frontend-structure:80; /mf/vacations/* → frontend-vacations:80;
  /mf/auth/* → frontend-auth:80; / → frontend-shell:80.
- Для `/api/structure`, `/api/vacations`, `/api/services` шлюз дополнительно подставляет
  fallback-заголовки SSO-заглушки `X-User`/`X-Roles` (см. `map` в nginx.conf); для
  `/api/auth/*` и `/api/me` — только `Cookie` (роль/пользователь берутся из куки `hr_session`).
- Резолв upstream имён лениво: `resolver 127.0.0.11` + `set $u http://...; proxy_pass $u;`
  (иначе nginx падает при старте, пока имя не в DNS).
- Клиент ходит только на gateway:8090; отдельные контейнеры наружу не экспонируются.

### Сборка (раздельно)

- Каждый сервис — свой Dockerfile, build-контекст = корень репо (копирует shared/ + свой
  backend, или свой фронт). Бэкенды: pip через Nexus (pypi-group, --trusted-host), CMD
  uvicorn <svc>.app:app. Фронтенды: node-стадия (npm install через Nexus-прокси) + webpack для
  своего микрофронта → dist; затем nginx-стадия c `COPY --from=build` (dist создаётся в
  контейнере сборки, не на хосте).
- Общий код: `shared/` (auth, make_pool, overlap, structure_data) — импортируется обоими
  бэкендами; vacations использует структуру через shared (без HTTP-звонка между сервисами).
- Контекст сборки чистится `.dockerignore` (node_modules/, dist/, .git/), иначе Docker не
  может затарриджить host node_modules.

### Запуск/проверка

- `"$DEXE" compose up --build -d` (DEXE = Windows docker.exe), точка входа http://localhost:8090.
- Если 8090 «занят» — удалить старый `hr-main-hr-portal-1`; если шлюз пересоздался без
  маппинга — `compose up -d --force-recreate gateway`.
- Данные: при старте каждый бэкенд в lifespan инициализирует свою таблицу и сид (если пусто);
  общая БД. Проверка: `/api/health`, `/mf/vacations/remoteEntry.js` (200); pytest идут через
  шлюз :8090 (`conftest.backend` = GATEWAY).

### Что дальше по регламенту (не сделано)

Разнести в отдельные GitLab-проекты (hr-portal-shell/structure/vacations) и завести CI/CD
пайплайн НА СЕРВИС: каждый — своя сборка, свой тег/версия, деплой отдельно (канареечно).
Сейчас всё в одном compose-стеке пилота, но каждый сервис уже умеет собираться отдельно —
основа под автономный деплой.

## Общие библиотеки при разделении на отдельные репозитории

Сейчас `shared/` лежит в пилот-репо и копируется в каждый бэкенд-образ (`COPY shared/`).
При переходе к отдельным репозиториям сервисов общая логика НЕ остаётся в пилоте —
она выносится в **отдельный версионируемый пакет**:

- Python (auth, db-пул, overlap, structure_data) → пакет `hr-portal-shared`, публикуется в
  **Nexus pypi** с semver-версией.
- Фронтенд-утилиты (если появятся) → npm-пакет `@hr/shared`, публикуется в Nexus npm.

Каждый сервис-репозиторий при сборке берёт **зафиксированную версию** shared-пакета
(`pip install hr-portal-shared==X`, `npm i @hr/shared@X`) из Nexus → свои тесты → свой образ →
Harbor → деплой. Свой `.gitlab-ci.yml`, свой тег/версия.

Проверка по `structure_data` (логика структуры используется и vacations): вариант 1 — общий
пакет (pragmaтично, DRY, без сетевых вызовов); вариант 2 — чистые микросервисы: vacations
вызывает API сервиса структуры по контракту (`/api/structure/subordinates`), не импортируя его
логику (независимость, но внутренний HTTP-вызов + контракт + деградация при недоступности).
Решение для ближнего шага — **общий версионируемый пакет**; переход на сервисный вызов — при росте.

## DevOps-замечания (проверено на ревизии, демо)

Найденные расхождения/риски по сборке и деплою (не критично для демо, но стоит зафиксировать):

- **Состав/маршрутизация в доке устарели** — исправлено: добавлены auth-сервис
  (`backend-auth`, `frontend-auth`), маршруты `/api/auth/*`, `/api/me`, `/mf/auth/*`.
- **Версии базовых образов не зафиксированы** (плавающие теги, без digest): `python:3.12-slim`,
  `node:20-alpine`, `nginx:alpine` (Dockerfile), `postgres:16-alpine`, `nginx:alpine` (compose),
  `nexus.sogaz.ru/sogaz-auto-chrome:1.6` (e2e). Для воспроизводимости — пин по digest.
- **Python-зависимости бэкендов не зафиксированы**: `fastapi`, `uvicorn[standard]`,
  `psycopg[binary]`, `psycopg-pool`, `pydantic` ставятся без версий (последние на каждый сбор).
  Нужен `==X.Y.Z` (или `pip freeze` → requirements.txt). npm-зависимости в `package.json`
  зафиксированы, но ставится через `npm install` (не `npm ci` — не строго по lockfile).
- **Nexus URL расходятся**: `.npmrc` → `https://nexus.sogaz.ru/npm/`, а в Dockerfile
  `--registry=https://nexus.sogaz.ru/repository/npm-proxy-registry.npmjs.org/`. Привести к одному.
- **Нет non-root пользователя** ни в одном образе (бэкенды `python:3.12-slim` и nginx-стадии
  работают от root) и **нет `HEALTHCHECK`** ни в одном Dockerfile (здоровье только у `db` в compose).
- **Нет restart-политик** в docker-compose; `depends_on` для gateway — только plain
  (порядок старта без условия health), healthcheck есть только у `db` (conditional для бэкендов).
- **Секреты в plaintext**: `DATABASE_URL` (`hr:hr`) и `AUTH_SECRET` `hr-auth-secret-change-me`
  захардкожены в `docker-compose.yml` — для демо ок, для боевого контура вынести в env/секреты.
- **Шлюз доверяет клиентским заголовкам**: `map ... default $http_x_user` — если клиент передаст
  `X-User`/`X-Roles`, они пройдут дальше (для демо это и есть SSO-заглушка; при реальном SSO
  заголовки должны срезаться на шлюзе и заменяться на доверенные).
- **Хардкод путей в скриптах**: `scripts/cleanup_test_data.sh` и `e2e/run.sh` жёстко
  прописывают `.../AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe`,
  `DB_CONTAINER=hr-main-db-1`, `--network hr-main_default`. Перенести в env (DEXE, DB_CONTAINER,
  NETWORK) с дефолтом.
- **`services/auth/frontend` не в npm-workspaces корневого `package.json`**
  (только shell, vacations, structure), хотя собирается как отдельный remote. Работает, т.к.
  зависимости идентичны hoisted-депсам; стоит добавить в workspaces для единообразия.
