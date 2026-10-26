"""Общие фикстуры для смоук-тестов HR-портала.

pytest-playwright даёт фикстуры page/expect/base_url; здесь мы только
- задаём тайм-ауты (ничего не ждём sleep'ом),
- собираем ошибки консоли/страницы и падаем, если они были.
"""
import pytest


@pytest.fixture(scope="session")
def browser(browser_type):
    """Запускаем Chromium из образа sogaz-auto-chrome (браузер уже в сборке).
    --ignore-certificate-errors — как в референсе (browser_config.yml), т.к. при
    самоподписанных сертификатах (внутренний TLS) иначе консольная ошибка."""
    b = browser_type.launch(args=["--ignore-certificate-errors"], headless=True)
    yield b
    b.close()


@pytest.fixture(autouse=True)
def _timeouts(page):
    """Единые тайм-ауты: ждём условия, а не sleep."""
    page.set_default_timeout(15000)          # ожидание элемента/условия
    page.set_default_navigation_timeout(30000)  # навигация/загрузка remote-модулей


@pytest.fixture(autouse=True)
def _capture_console_errors(page):
    """Собираем ошибки уровня error и pageerror; падаем, если нашли."""
    errors: list[str] = []

    def on_console(msg):
        if msg.type == "error":
            errors.append(f"console.error: {msg.text}")

    page.on("console", on_console)
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))

    yield
    assert not errors, "Обнаружены ошибки консоли/страницы:\n" + "\n".join(errors)
