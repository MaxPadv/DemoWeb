#!/usr/bin/env bash
# Запуск e2e смоук-тестов одним вызовом (приложение должно быть поднято).
# Образ hr-main-e2e собирается заранее: docker build -f e2e/Dockerfile -t hr-main-e2e .
set -e
DEXE="/mnt/c/Users/popkov.maxim/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe"
WP="$(wslpath -w "$(pwd)")"
"$DEXE" run --rm --network hr-main_default \
  -v "$WP":/app -w /app/e2e \
  -e PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright \
  hr-main-e2e \
  python3 -m pytest smoke/test_smoke.py -q --base-url http://gateway
