# Бэкенд-сервис «Отпуска» — собирается отдельно (контекст = корень репо).
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN pip install --no-cache-dir \
    --index-url https://nexus.sogaz.ru/repository/pypi-group/simple/ \
    --trusted-host nexus.sogaz.ru \
    -r /dev/stdin <<'EOF'
fastapi
uvicorn[standard]
psycopg[binary]
psycopg-pool
pydantic
EOF
COPY shared/ /app/shared/
COPY services/vacations/backend/ /app/vacations/
COPY services.json /app/services.json
WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "vacations.app:app", "--host", "0.0.0.0", "--port", "8000"]
