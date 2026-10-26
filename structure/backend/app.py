"""HR Portal demo — бэкенд сервиса «Структура компании» (независимый сервис)."""

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI

from shared import auth, structure_data
from shared.db import make_pool

pool = make_pool()
SERVICES_FILE = Path('/app/services.json')


@asynccontextmanager
async def lifespan(_: FastAPI):
    pool.open(wait=True, timeout=30)
    structure_data.init_structure(pool)
    yield
    pool.close()


app = FastAPI(title='HR Structure Service', version='0.1.0', lifespan=lifespan)


@app.get('/api/health')
def health() -> dict:
    with pool.connection() as conn:
        conn.execute('SELECT 1')
    return {'status': 'ok', 'service': 'structure', 'ts': datetime.now(timezone.utc).isoformat()}


@app.get('/api/me')
def me(user: auth.User = Depends(auth.current_user)) -> dict:
    return {'name': user.name, 'role': 'HR-менеджер' if user.is_hr else 'Сотрудник', 'department': ''}


@app.get('/api/structure')
def list_structure(user: auth.User = Depends(auth.current_user)) -> list[dict]:
    return structure_data.all_employees()


@app.get('/api/structure/subordinates')
def subordinates(user: auth.User = Depends(auth.current_user)) -> list[dict]:
    return structure_data.subordinates_of(user.name)
