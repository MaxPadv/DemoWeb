"""Смоук-тесты веб-оболочки HR-портала (Playwright, sync API).

Быстрое дымовое прогонирование по сценариям 1-4:
страница грузится / сервис открывается / нет ошибок консоли.
Никаких данных не создаём и не удаляем. Ждём только условия (expect),
без sleep. Ошибки консоли/страницы ловит фикстура в conftest.py.

Сервис авторизации включён: сначала логин (ivan/ivan123), затем сценарий.
"""
from playwright.sync_api import Page, expect
import re

BASE = "/"


def _login(page: Page):
    """Вход через auth-сервис (сразу на /mf/auth/ — без пре-логинового 401)."""
    page.goto("/mf/auth/")
    expect(page.get_by_role("button", name="Войти")).to_be_visible(timeout=15000)
    page.locator('input[autocomplete="username"]').fill("ivan")
    page.locator('input[autocomplete="current-password"]').fill("ivan123")
    page.get_by_role("button", name="Войти").click()
    # после логина — редирект на портал, главная с приветствием
    expect(page.get_by_role("heading", level=1)).to_contain_text("Добрый день", timeout=15000)


def _open_home(page: Page):
    page.goto(BASE)
    expect(page.get_by_role("heading", level=1)).to_contain_text("Добрый день")


def _open_vacations(page: Page):
    page.get_by_role("button", name="Оформить отпуск →").click()
    expect(page.get_by_role("heading", level=1, name="Отпуска")).to_be_visible()


def test_01_shell_loads(page: Page):
    """Главная оболочка грузится: приветствие, карточки сервисов видны."""
    _login(page)
    _open_home(page)
    expect(page.get_by_role("heading", name="Структура компании")).to_be_visible()
    expect(page.get_by_role("heading", name="Отпуска")).to_be_visible()


def test_02_vacations_service_selection(page: Page):
    """Переход в «Отпуска»: страница с двумя сервисами и кнопками «Открыть →»."""
    _login(page)
    _open_home(page)
    _open_vacations(page)
    expect(page.get_by_role("heading", name="Запланировать отпуск")).to_be_visible()
    expect(page.get_by_role("heading", name="Оформить отпуск")).to_be_visible()
    expect(page.get_by_role("button", name="Открыть →")).to_have_count(2)


def test_03_plan_vacation_page(page: Page):
    """«Запланировать отпуск»: форма «Новая заявка», календарь, список «Заявки»."""
    _login(page)
    _open_home(page)
    _open_vacations(page)
    plan_card = page.locator(".vc-service-card").filter(
        has=page.get_by_role("heading", name="Запланировать отпуск")
    )
    plan_card.get_by_role("button", name="Открыть →").click()

    expect(page.get_by_role("heading", name="Новая заявка")).to_be_visible()
    expect(page.get_by_role("heading", name="Календарь отпусков (отдел)")).to_be_visible()
    expect(page.locator(".pc-cal")).to_be_visible()  # календарь отрисовался
    expect(page.get_by_role("heading", name="Заявки")).to_be_visible()
    expect(page.locator(".vc-table, .vc-empty")).to_be_visible()
    expect(page.get_by_role("alert")).to_have_count(0)


def test_06_calendar_select_period(page: Page):
    """Интерактивный выбор периода на календаре: клик по рабочему дню (старт) и по дню
    (конец) — период [start,end] подсвечивается (pc-cell--sel)."""
    _login(page)
    _open_home(page)
    _open_vacations(page)
    plan_card = page.locator(".vc-service-card").filter(
        has=page.get_by_role("heading", name="Запланировать отпуск")
    )
    plan_card.get_by_role("button", name="Открыть →").click()
    expect(page.get_by_role("heading", name="Новая заявка")).to_be_visible()

    grid = page.locator(".pc-month").first  # январь 2027
    def cell(d: int):
        return grid.locator("td.pc-cell").filter(
            has=page.get_by_text(str(d), exact=True)
        ).first
    cell(11).click()  # пн — старт (не выходной, не праздник)
    cell(12).click()  # вт — конец
    expect(page.locator(".pc-cal .pc-cell--sel")).to_have_count(2, timeout=10000)


def test_07_calendar_select_not_on_weekend_start(page: Page):
    """Старт выбора нельзя начать с выходного (суббота) — клик по сб игнорируется."""
    _login(page)
    _open_home(page)
    _open_vacations(page)
    plan_card = page.locator(".vc-service-card").filter(
        has=page.get_by_role("heading", name="Запланировать отпуск")
    )
    plan_card.get_by_role("button", name="Открыть →").click()
    expect(page.get_by_role("heading", name="Новая заявка")).to_be_visible()

    grid = page.locator(".pc-month").first
    def cell(d: int):
        return grid.locator("td.pc-cell").filter(
            has=page.get_by_text(str(d), exact=True)
        ).first
    cell(2).click()  # суббота — старт нельзя
    expect(page.locator(".pc-cal .pc-cell--sel")).to_have_count(0, timeout=5000)


def test_08_calendar_start_highlight_and_reset(page: Page):
    """Старт подсвечивается сразу после первого клика; «Сбросить» очищает выбор
    (не трогая уже отправленные заявки)."""
    _login(page)
    _open_home(page)
    _open_vacations(page)
    plan_card = page.locator(".vc-service-card").filter(
        has=page.get_by_role("heading", name="Запланировать отпуск")
    )
    plan_card.get_by_role("button", name="Открыть →").click()
    expect(page.get_by_role("heading", name="Новая заявка")).to_be_visible()

    grid = page.locator(".pc-month").first
    def cell(d: int):
        return grid.locator("td.pc-cell").filter(
            has=page.get_by_text(str(d), exact=True)
        ).first
    cell(11).click()  # только старт (пн)
    expect(page.locator(".pc-cal .pc-cell--sel")).to_have_count(1, timeout=10000)

    page.get_by_role("button", name="Сбросить").click()
    expect(page.locator(".pc-cal .pc-cell--sel")).to_have_count(0, timeout=5000)


def test_09_calendar_holidays_and_weekends(page: Page):
    """Праздники — красные (pc-cell--holiday), выходные — серые (pc-cell--weekend)."""
    _login(page)
    _open_home(page)
    _open_vacations(page)
    plan_card = page.locator(".vc-service-card").filter(
        has=page.get_by_role("heading", name="Запланировать отпуск")
    )
    plan_card.get_by_role("button", name="Открыть →").click()
    expect(page.get_by_role("heading", name="Новая заявка")).to_be_visible()

    jan = page.locator(".pc-month").nth(0)
    feb = page.locator(".pc-month").nth(1)
    def cell(grid, d: int):
        return grid.locator("td.pc-cell").filter(
            has=page.get_by_text(str(d), exact=True)
        ).first
    # 1 января (пт) — новогодние каникулы -> красный
    expect(cell(jan, 1)).to_have_class(re.compile(r"pc-cell--holiday"))
    # 9 января (сб) — обычный выходной -> серый
    expect(cell(jan, 9)).to_have_class(re.compile(r"pc-cell--weekend"))
    # 23 февраля (вт) — День защитника Отечества -> красный
    expect(cell(feb, 23)).to_have_class(re.compile(r"pc-cell--holiday"))


def test_10_calendar_holiday_tooltip_and_start_block(page: Page):
    """Тултип с названием праздника при наведении; старт отпуска с праздника запрещён."""
    _login(page)
    _open_home(page)
    _open_vacations(page)
    plan_card = page.locator(".vc-service-card").filter(
        has=page.get_by_role("heading", name="Запланировать отпуск")
    )
    plan_card.get_by_role("button", name="Открыть →").click()
    expect(page.get_by_role("heading", name="Новая заявка")).to_be_visible()

    feb = page.locator(".pc-month").nth(1)
    day = feb.locator("td.pc-cell").filter(
        has=page.get_by_text("23", exact=True)
    ).first
    day.hover()
    expect(page.locator(".pc-tooltip, .pc-tooltip--holiday")).to_contain_text(
        "День защитника Отечества", timeout=10000
    )
    # старт с праздника нельзя -> выбора нет
    day.click()
    expect(page.locator(".pc-cal .pc-cell--sel")).to_have_count(0, timeout=5000)


def test_11_sogaz_branding(page: Page):
    """Слово SOGAZ в корп. стиле на странице входа и в меню (без логотипа)."""
    page.goto("/mf/auth/")
    expect(page.get_by_role("button", name="Войти")).to_be_visible(timeout=15000)
    # на странице входа — SOGAZ рядом с «HR Портал»
    expect(page.locator(".login-card__brand")).to_have_text("SOGAZ")

    page.locator('input[autocomplete="username"]').fill("ivan")
    page.locator('input[autocomplete="current-password"]').fill("ivan123")
    page.get_by_role("button", name="Войти").click()
    expect(page.get_by_role("heading", level=1)).to_contain_text("Добрый день", timeout=15000)
    # в меню слева и в хлебных крошках — SOGAZ
    expect(page.locator(".sidebar__sogaz")).to_have_text("SOGAZ")
    expect(page.locator(".topbar__sogaz")).to_have_text("SOGAZ")


def test_12_vacation_faq(page: Page):
    """Кнопка «?» рядом с «Запланировать отпуск»: по клику — подсказка FAQ."""
    _login(page)
    _open_home(page)
    _open_vacations(page)
    plan_card = page.locator(".vc-service-card").filter(
        has=page.get_by_role("heading", name="Запланировать отпуск")
    )
    plan_card.get_by_role("button", name="Открыть →").click()
    expect(page.get_by_role("heading", name="Новая заявка")).to_be_visible()

    faq = page.locator(".vc-faq")
    expect(faq).to_be_visible()
    faq.click()
    tip = page.locator(".vc-faq-tip")
    expect(tip).to_contain_text("FAQ Планирования отпусков", timeout=10000)
    expect(tip).to_contain_text("Посчитайте свои дни.")
    expect(tip).to_contain_text("Обсудите с руководителем.")
    expect(tip).to_contain_text("Решите, делить ли отпуск на части.")
    expect(tip).to_contain_text("Учтите льготы.")


def test_05_logout(page: Page):
    """Кнопка «Выйти» завершает сессию и возвращает на страницу входа."""
    _login(page)
    page.get_by_role("button", name="Выйти").click()
    # после выхода — снова форма входа
    expect(page.get_by_role("button", name="Войти")).to_be_visible(timeout=15000)


def test_04_back_and_structure(page: Page):
    """Назад к выбору, из «Отпуска» на главную, открыть «Структура компании»."""
    _login(page)
    _open_home(page)
    _open_vacations(page)
    plan_card = page.locator(".vc-service-card").filter(
        has=page.get_by_role("heading", name="Запланировать отпуск")
    )
    plan_card.get_by_role("button", name="Открыть →").click()
    expect(page.get_by_role("heading", name="Новая заявка")).to_be_visible()

    page.get_by_role("button", name="← К выбору сервиса").click()
    expect(page.get_by_role("heading", level=1, name="Отпуска")).to_be_visible()
    page.get_by_role("button", name="← На главную").click()
    expect(page.get_by_role("heading", level=1)).to_contain_text("Добрый день")

    struct_card = page.locator(".svc-card").filter(
        has=page.get_by_role("heading", name="Структура компании")
    )
    struct_card.get_by_role("button", name="Открыть →").click()
    expect(page.get_by_role("heading", name="Структура компании")).to_be_visible()
    expect(page.get_by_role("heading", name="Сотрудники")).to_be_visible()
    expect(page.locator(".st-tree, .st-empty")).to_be_visible()
    expect(page.get_by_role("alert")).to_have_count(0)
