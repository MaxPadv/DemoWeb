# Смоук-тесты веб-оболочки HR-портала (Playwright, Python)

Проверяют сценарии 1–4: оболочка грузится, сервисы «Отпуска» и «Структура
компании» открываются, нет ошибок консоли. Данные не создают и не удаляют.

Основа — как в референсе `sogaz_auto/autotest-projects/site-2.0-autotests`
(и его общем шаблоне CI из `sogaz_auto/core/pipes`): тесты гоняются в образе
**`nexus.sogaz.ru/sogaz-auto-chrome:1.6`**, в котором уже собран браузер
(Chromium в `/root/.cache/ms-playwright`). Внешние CDN для скачивания браузера
не используются — браузер берём из образа (через Nexus), зависимости — через
Nexus `pypi-group`. Всё как в корпоративном контуре СОГАЗ.

## Запуск

Собрать образ (разово): браузер из `sogaz-auto-chrome` берётся из Nexus,
зависимости — из Nexus `pypi-group`.

```bash
"DEXE" build -f e2e/Dockerfile -t hr-main-e2e .   # DEXE=.../docker.exe
```

Запуск тестов (приложение должно быть поднято) — **один вызов**:

```bash
./e2e/run.sh        # = docker run ... hr-main-e2e python3 -m pytest -q --base-url http://gateway
```

Ожидаемый результат: `4 passed`.

## Почему так, а не локально

- `python -m playwright install chromium` из WSL падает — внешние CDN
  (`cdn.playwright.dev` и др.) заблокированы.
- Запуск Windows-браузера (Яндекс/Edge) из WSL-Playwright не работает
  (loopback-изоляция WSL2, канал `--remote-debugging-pipe` не проходит).
- Поэтому браузер берём из готового образа `sogaz-auto-chrome` (тот же приём,
  что в CI сайтовых автотестов СОГАЗ).

## Замечания

- `e2e/conftest.py` запускает Chromium с `--ignore-certificate-errors` — при
  самоподписанных сертификатах внутреннего контура иначе в консоль сыпется
  `ERR_CERT_AUTHORITY_INVALID` (и тест падает на ловле ошибок консоли).
- `base_url` в `pytest.ini` — `http://localhost:8090` (для локального запуска),
  при запуске в контейнере переопределяется через `--base-url http://gateway`.
