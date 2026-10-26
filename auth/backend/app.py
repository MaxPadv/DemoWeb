"""HR Portal demo — бэкенд сервиса «Авторизация» (независимый сервис)."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from shared import auth, structure_data
from shared.db import make_pool

from . import routes

pool = make_pool()


@asynccontextmanager
async def lifespan(_: FastAPI):
    pool.open(wait=True, timeout=30)
    structure_data.init_structure(pool)
    yield
    pool.close()


app = FastAPI(title='HR Auth Service', version='0.1.0', lifespan=lifespan)
app.include_router(routes.router)

# /api/me также на auth-бэкенде (gateway маршрутизирует)
@app.get('/api/me')
def me(user: auth.User = Depends(auth.current_user)) -> dict:
    role = user.role
    dept = ''
    if structure_data.pool:
        with structure_data.pool.connection() as conn:
            d = conn.execute(
                "SELECT department FROM employees WHERE name = %s", (user.name,)
            ).fetchone()
            dept = d['department'] if d else ''
    return {'name': user.name, 'role': role, 'department': dept}
