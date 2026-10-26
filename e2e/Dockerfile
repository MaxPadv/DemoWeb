# E2E-образ для смоук-тестов. База — sogaz-auto-chrome (браузер уже собран в
# /root/.cache/ms-playwright). Поверх ставим только pytest-зависимости (Nexus).
# Запуск тестов — одним вызовом: ./e2e/run.sh  (см. README)
FROM nexus.sogaz.ru/sogaz-auto-chrome:1.6

COPY e2e/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir \
      --index-url https://nexus.sogaz.ru/repository/pypi-group/simple/ \
      --trusted-host nexus.sogaz.ru \
      -r /tmp/requirements.txt

# код и pytest.ini монтируются при запуске (см. e2e/run.sh)
