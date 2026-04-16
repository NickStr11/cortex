# Research Summary: Steam Sniper v2.0

**Project:** Steam Sniper Dashboard — Зеркало lis-skins
**Researched:** 2026-04-13
**Confidence:** HIGH

## Executive Summary

v2.0 превращает watchlist-трекер в полное зеркало lis-skins с каталогом, категориями, персональными списками и мобильным доступом. Всё строится на **существующем стеке без новых зависимостей** — FastAPI, vanilla JS, SQLite. Каталог 24k предметов уже в памяти сервера (`_prices` dict), нужны API-эндпоинты с пагинацией и category parser.

## Stack Additions

**Ноль новых Python-пакетов.** Все фичи реализуются существующим стеком:
- Каталог: серверная пагинация по in-memory dict, category parsing из имён предметов
- Dual lists: новая таблица `user_lists` в SQLite (отдельно от `watchlist`)
- PWA: 2 статических файла (manifest.json + sw.js ~60 строк) + 3 иконки + meta-теги
- Chrome extension: 4 файла (manifest.json, content.js, background.js, styles.css), Manifest V3
- Virtual scroll: ~80 строк vanilla JS для рендера 24k предметов

**Требуется инфра:** HTTPS (nginx + Let's Encrypt) на VPS для PWA service worker на iOS.

## Feature Table Stakes

| Feature | Сложность | Приоритет | Зависимости |
|---------|-----------|-----------|-------------|
| Category parser | MEDIUM | P0 (фундамент) | Нет |
| Catalog API + пагинация | LOW | P0 | Category parser |
| Dual lists (favorites + wishlist) | LOW | P1 | Новая таблица |
| Dashboard tabs + catalog view | MEDIUM | P1 | Catalog API + Dual lists |
| Cases tab | LOW | P2 | Filtered catalog |
| PWA manifest | LOW | P2 | HTTPS |
| Chrome extension | HIGH | P3 | List API |

## Architecture

**Новые компоненты:**
- `GET /api/catalog` — пагинация, фильтр по категории, сортировка
- Таблица `user_lists` — отдельно от watchlist (разная семантика: списки vs алерты)
- Category parser — lookup dict по weapon name prefix (~15 правил → 95%+ покрытие)
- Hash router в dashboard — 5 табов (watchlist, catalog, favorites, wishlist, cases)

**Не трогаем:** watchlist таблицу, Telegram бот, алерт-логику, deploy pipeline.

## Top Pitfalls

1. **24k DOM nodes = краш браузера** → серверная пагинация (limit=50) с первого дня
2. **CS2 naming: 13+ паттернов** → lookup table по prefix, не один regex
3. **dashboard.html 1373 строки** → разбить на ES модули ДО добавления фич
4. **PWA stale cache** → network-first для HTML/API, cache-first для статики
5. **Chrome extension CORS** → background service worker для API-вызовов (content script на HTTPS не может fetch на HTTP)
6. **Dual lists ≠ watchlist** → отдельная таблица, не расширение существующей

## Suggested Build Order

| # | Фаза | Зависит от | Параллельно |
|---|------|-----------|-------------|
| 5 | Dashboard Split (ES modules) | — | — |
| 6 | Category Parser + Catalog API | Phase 5 | Phase 7 |
| 7 | Dual Lists (DB + API) | Phase 5 | Phase 6 |
| 8 | Dashboard Tabs + Catalog + Lists UI | Phases 6+7 | — |
| 9 | Cases Tab + PWA | Phase 8 | — |
| 10 | Chrome Extension | Phase 7 | — |

*Нумерация продолжает v1.0 (phases 1-4).*

## Blockers

- **HTTPS** — нужен для PWA service worker на iOS. Nginx + Let's Encrypt + домен/duckdns
- **Steam API key** — от Лёши, для Steam-цен (отложено, не в v2.0 scope)
- **Lis-skins DOM** — селекторы для Chrome extension не документированы, нужен live inspect

## Confidence

| Область | Уровень | Причина |
|---------|---------|---------|
| Backend (catalog API) | HIGH | Standard pagination, данные уже в памяти |
| Category parsing | MEDIUM | CS2 naming consistent, но 13+ edge case patterns |
| Dual lists | HIGH | Standard SQLite CRUD |
| PWA | HIGH | Well-documented standard |
| Chrome extension | MEDIUM | MV3 stable, но lis-skins DOM undocumented |
| Dashboard split | HIGH | Standard ES modules, no build step |

---
*Research completed: 2026-04-13*
*Ready for requirements: yes*
