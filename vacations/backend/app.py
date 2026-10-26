"""HR Portal demo — бэкенд сервиса «Отпуска» (независимый сервис)."""

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI

from shared import auth, structure_data
from shared.db import make_pool

from . import vacations

pool = make_pool()
SERVICES_FILE = Path('/app/services.json')


@asynccontextmanager
async def lifespan(_: FastAPI):
    pool.open(wait=True, timeout=30)
    structure_data.init_structure(pool)
    vacations.init_vacations(pool)
    yield
    pool.close()


app = FastAPI(title='HR Vacations Service', version='0.1.0', lifespan=lifespan)
app.include_router(vacations.router)


@app.get('/api/health')
def health() -> dict:
    with pool.connection() as conn:
        conn.execute('SELECT 1')
    return {'status': 'ok', 'service': 'vacations', 'ts': datetime.now(timezone.utc).isoformat()}


@app.get('/api/me')
def me(user: auth.User = Depends(auth.current_user)) -> dict:
    return {'name': user.name, 'role': 'HR-менеджер' if user.is_hr else 'Сотрудник', 'department': ''}


@app.get('/api/services')
def services(_: auth.User = Depends(auth.current_user)) -> list[dict]:
    return json.loads(SERVICES_FILE.read_text(encoding='utf-8'))
