# Брендинг «SOGAZ» (корп. стиль, без логотипа) — страница входа и меню

Статус: **as-built** (реализовано субагентом, проверено ассистентом).

## As-built

Слово SOGAZ в корпоративном стиле, без логотипа:
- Страница входа: `login-card__title` → `HR Портал <span class="login-card__brand">SOGAZ</span>`
  (`.login-card__brand`: `--sogaz-brand`, `--sogaz-font-cond`, 700, letter-spacing .12em, uppercase, nowrap).
- Меню слева (сайдбар): `sidebar__sogaz` после «Портал» (`.sidebar__sogaz`: `--sogaz-blue-light`
  — читаемый на тёмном сайдбаре, 14px, nowrap; скрывается при схлопывании сайдбара в узком вью).
- Хлебные крошки topbar: `HR Портал <span class="topbar__sogaz">SOGAZ</span> / …`
  (`.topbar__sogaz`: `--sogaz-blue-light`, 13px, nowrap).

## Цель

Добавить слово **SOGAZ** в корпоративном стиле на страницу входа и в меню слева, БЕЗ логотипа
(иконку/картинку не добавляем). Надпись должна быть лаконичной по размеру и не «прыгать»
(не вызывать layout shift / перенос строки).

## Где

1. **Страница входа** (`services/auth/frontend/src/App.tsx`, `styles.css`):
   заголовок `HR Портал` → `HR Портал SOGAZ` (слово SOGAZ — стилизованный `span`)
   с классом `login-card__brand`.
2. **Меню слева** (`services/shell/src/App.tsx`, `styles.css`): бренд сайдбара
   (`sidebar__logo` "HR" + `sidebar__name` "Портал`) → добавить `SOGAZ` (`sidebar__sogaz`).
   Хлебные крошки topbar (`topbar__crumb` "HR Портал / …") → `HR Портал SOGAZ / …` (`topbar__sogaz`).

## Стиль слова SOGAZ (корп. стиль)

- Цвет: `var(--sogaz-brand)` (#002899).
- Шрифт: `var(--sogaz-font-cond, 'InterDisplay', 'Inter', system-ui, sans-serif)` (condensed),
  `font-weight: 600–700`.
- `text-transform: uppercase`, `letter-spacing: 0.12em`, размер лаконичный (в сайдбаре — меньше,
  чем заголовок; в кроншке/форме — соразмерно).
- `white-space: nowrap` — чтобы не переносилось и не «прыгало».
- Не менять JS-логику/составной текст в других местах.

## TDD-срезы

- **S0 — RED e2e:** на странице входа и в меню после логина видно "SOGAZ".
- **S1 — разметка/стили:** добавить `span` с классом + CSS (цвет/букв. интервал/nowrap).
- **S2 — тесты/верификация:** e2e зелёные (логин, topbar, сайдбар), существующие тесты и демо.

## Замечания

- Без логотипа/иконки-картинки (по решению). Только стилизованный текст SOGAZ.
- Надпись стабильна по размеру, не переносится.
