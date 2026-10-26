#!/bin/sh
# Очистка тестовых данных портала для повторного прогона pytest.
# Тесты append-only: пишут заявки с разными префиксами comment (auto-*, cal-*, lim-*,
# yr-* и пр.), а лимит 28 дней/год — не идемпотентен, поэтому накопление даёт
# ложные 422 «Превышен лимит». Удаляем ВСЁ, кроме 3 SEED-строк, — чистый baseline.
# Запуск: ./scripts/cleanup_test_data.sh   (нужен работающий docker compose)
set -e

DEXE="${DEXE:-/mnt/c/Users/popkov.maxim/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe}"
DB_CONTAINER="${DB_CONTAINER:-hr-main-db-1}"
DB_USER="${DB_USER:-hr}"
DB_NAME="${DB_NAME:-hr}"

echo "Удаляю тестовые заявки (все, кроме SEED) в контейнере $DB_CONTAINER..."
"$DEXE" exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c \
  "DELETE FROM vacations WHERE comment NOT IN ('Новогодние каникулы','Весенний отпуск','Семейные обстоятельства','Плановый отпуск','Отпуск Волкова');"

echo "OK. Осталось заявок (SEED):"
"$DEXE" exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM vacations;"
