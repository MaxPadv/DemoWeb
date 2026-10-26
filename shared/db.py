import os

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def make_pool() -> ConnectionPool:
    """Создать пул подключений к общей БД (оба бэкенда шарят одну БД hr)."""
    url = os.environ.get('DATABASE_URL', 'postgresql://hr:hr@localhost:5432/hr')
    return ConnectionPool(url, min_size=2, max_size=10, open=False, kwargs={'row_factory': dict_row})
