# Steam Sniper Dashboard

## What This Is

Персональное зеркало lis-skins.com для CS2 скинов. Полный каталог с навигацией по категориям, два персональных списка (избранное + хотелки), ценовые алерты через Telegram-бота, графики истории цен. Два пользователя (Никита + Лёша), VPS deployment, PWA для мобильного доступа.

## Core Value

Лёша открывает дашборд и видит весь каталог lis-skins как свой — с категориями, персональными списками (что есть / что хочу), ценами и алертами. Одно место для всех решений по скинам.

## Current Milestone: v2.0 Зеркало lis-skins

**Goal:** Превратить watchlist-дашборд в полное зеркало lis-skins с каталогом, категориями, двумя списками и PWA.

**Target features:**
- Полный каталог lis-skins с навигацией по категориям
- Два раздельных списка: избранное (есть) + хотелки (хочу купить)
- Кнопки добавления в списки прямо на карточках каталога
- Фильтры и меню (по категории, цене, статусу)
- Трекинг ящиков (отдельная вкладка)
- PWA manifest (ярлык на iPhone)
- Steam цены (blocked: нужен аккаунт от Лёши)
- Chrome extension для lis-skins (добавление в дашборд с сайта)

## Requirements

### Validated

- ✓ Telegram-бот — алерты, watchlist, поиск, ввод по ссылке — v1.0
- ✓ Lis-skins JSON API (публичный, 24к предметов, без ключа) — v1.0
- ✓ SQLite shared DB (WAL mode, bot + dashboard) — v1.0
- ✓ FastAPI REST API (watchlist CRUD, search, history, stats) — v1.0
- ✓ Веб-дашборд: watchlist, поиск, карточки, hero stats, activity feed — v1.0
- ✓ TradingView Lightweight Charts (24h/7d/30d/all) — v1.0
- ✓ VPS deployment (194.87.140.204:8100), systemd — v1.0
- ✓ Курс USD/RUB, автообновление каждые 5 мин — v1.0

### Active

- [ ] Полный каталог lis-skins с навигацией по категориям
- [ ] Два раздельных списка: избранное (❤️) + хотелки (⚙️)
- [ ] Кнопки добавления в списки на карточках каталога
- [ ] Фильтры/меню (категории, цена, статус, ящики, уведомления)
- [ ] Трекинг ящиков (отдельная вкладка, ~3000 предметов)
- [ ] PWA manifest (ярлык на iPhone)
- [ ] Steam цены + сравнение площадок (blocked: нужен Steam-аккаунт)
- [ ] Chrome extension для lis-skins (добавление в дашборд с сайта)

### Out of Scope

- Авторизация/логин — два пользователя, доступ по URL
- Автоприём трейдов Steam — Лёша сам решил "пока не надо"
- Кросс-маркетплейс арбитраж — один сайт (lis-skins)
- Мобильное приложение — веб достаточно
- ML-сигналы — может потом
- Бот в Макс-мессенджере — нужен ИП, оставляем Telegram

## Context

- Telegram-бот: `tools/steam-sniper/main.py` — уже в production, polling mode
- Watchlist сейчас в JSON-файле (`data/watchlist.json`) — нужна миграция в SQLite
- Lis-skins JSON: `https://lis-skins.com/market_export_json/csgo.json` — 24к предметов, price + name + url + count
- Wear/quality (Factory New, Field-Tested и т.д.) — содержится в имени предмета, парсится
- VPS: 194.87.140.204, PharmOrder на порту 8000. Дашборд на другом порту (например 8100)
- Курс USD/RUB: `https://www.cbr-xml-daily.ru/daily_json.js`

## Constraints

- **Stack**: Python (FastAPI), HTML/JS (vanilla + TradingView Lightweight Charts), SQLite
- **Hosting**: VPS 194.87.140.204, отдельный порт от PharmOrder
- **Data source**: только lis-skins.com публичный JSON (без API-ключа)
- **UX**: лаконично, тёмная тема, gaming aesthetic. Цены в рублях.
- **Shared state**: бот и дашборд читают/пишут одну SQLite базу

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Один сайт (lis-skins) | Лёша работает только с ним | — Pending |
| SQLite вместо JSON | Нужна история цен + общий доступ бот/дашборд | — Pending |
| Без авторизации | Два пользователя, приватный URL на VPS | — Pending |
| Рубли как primary currency | Пользователи думают в рублях | — Pending |
| TradingView Lightweight Charts | Бесплатная, выглядит как настоящий TradingView | — Pending |

---
*Last updated: 2026-04-13 after v2.0 milestone start*
