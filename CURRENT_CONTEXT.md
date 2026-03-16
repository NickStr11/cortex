# Current Context

## 2026-03-16 PharmOrder — страница заказов apteka.ru

**Сделано** (задеплоено на VPS, не в git):

### Backend (server.py)
- `GET /api/orders?days=N` — читает Google Sheets (spreadsheet `11LfMaert...`) через gspread, кеширует клиент 30 мин
- `POST /api/orders/sms` — отправляет SMS через smstext.app API + обновляет статус в Sheets (col 7 + col 10)
- `GET /api/orders/product-image?q=...` — парсит apteka.ru (React SPA, `window.__INITIAL_STATE__`), достаёт `images.apteka.ru` URL, серверный кеш
- `GET /orders` — отдельная тестовая страница (можно удалить)
- Зависимости на VPS: `gspread`, `google-auth`, `httpx` — установлены в `/opt/pharmorder/.venv`
- SMS ключ добавлен в `/opt/pharmorder/.env`

### Frontend (index.html)
- Заказы встроены в **центр основного сайта** (вместо "Выберите товар из списка")
- Кнопка в сайдбаре (между "Остатки" и spacer) — по клику сворачивает все боковые панели, показывает заказы
- Грид 3 карточки в ряд, фото 56x56 с apteka.ru
- Каждая карточка: номер заказа, дата, источник (Email/Браузер/Telegram), товары с фото, телефон, кнопка SMS
- Фильтр по периоду: сегодня / 2 дня / 3 дня / неделя
- Fade-анимация: открыл панель → заказы исчезают, закрыл все → появляются
- SMS кнопка → отправляет, помечает "Готово" в Sheets, карточка становится полупрозрачной

### Файлы (локальные копии)
- `C:\tmp\vps_pharmorder\src\server.py` — API (заказы с ~строки 1574)
- `C:\tmp\vps_pharmorder\src\static\index.html` — фронт (~5100 строк)
- `C:\tmp\vps_pharmorder\src\static\orders.html` — тестовая страница (можно удалить)

### Что НЕ сделано / TODO
- [ ] Фото не всегда находятся (apteka.ru SPA может не отдать данные без JS)
- [ ] Нет поиска/фильтра по имени товара внутри заказов
- [ ] Не тестировали SMS отправку live (только API готов)
- [ ] orders.html тестовая страница — удалить после финала

### Деплой
Ручной через paramiko: редактируем локально → `sftp.put()` → `systemctl restart pharmorder`

---

## 2026-03-13 PharmOrder inventory panel — СТАБИЛЕН

**Сделано** (задеплоено на VPS, не в git):
- `_refreshInvStats()` — вместо `loadInventory()` в `invQuickSet`/`invPromptEdit`. Нет гонок при параллельном вводе нескольких позиций.
- `invEditMin` — in-place DOM swap, без re-render
- Qty input: 48px (не обрезает 2+ цифры)
- Stats: `items.length` (все) + `in_stock` + `total_qty`
- Toast тексты — починены (были `????`)

**Следующий шаг**: smoke-тест — набрать qty в 2 позиции без Enter, потом blur → оба должны сохраниться

---

## 2026-03-12 PharmOrder EAN override

**Проблема**: EAN `4670033321227` (Азитромицин Вертекс 500мг/ПУЛЬС Краснодар) в pr_all.dbf имел `id_name` от Цетиризина. СКЛИ Т показывал правильно, PharmOrder — нет.

**Фикс на VPS**:
- `/opt/pharmorder/src/data/ean_overrides.json` → `{"by_ean_supplier": {"4670033321227|ПУЛЬС Краснодар": 358502}}`
- `db.py` → `apply_ean_overrides()` — читает JSON, UPDATE + FTS rebuild
- `server.py` → вызов `apply_ean_overrides()` в `api_sync_upload_db` после каждого синка

**Аудит**: 50 конфликтных EAN из 63K (0.1%) — расходники/варианты. Системной проблемы нет. Добавлять в overrides.json по мере находок.

---

## 2026-03-12 tg-pharma batch draft
- `tools/tg-pharma` now has batch mode for stacked text/voice inventory tasks.
- New chat controls: `start_batch`, `show_batch`, `apply_batch`, `clear_batch`, `stop_batch`.
- While batch is active, inventory writes (`set/add/subtract/delete/restore`) are accumulated into `ChatState.batch_items` instead of going straight into single-item pending confirm.
- `apply_batch` creates one pending snapshot and then applies entries sequentially with per-item audit log and partial-failure retention.
- Live runtime is clean on the separate bot token (`@pharmorder_ops_bot`): one `python -u main.py`, build marker `2026-03-12-batch-draft-1`, no `409 Conflict`, stderr empty.

## 2026-03-11 tg-pharma bot_refs
- `tools/tg-pharma` switched from heavy local `bot_analytics.db` to lightweight `bot_refs.db` + live VPS `sklit_cache.db`/`order_history.db`.
- New builder: `tools/tg-pharma/build_refs.py`
- New DB: `tools/tg-pharma/data/bot_refs.db`
- Current refs build: 91,335 names, 90,693 makers, 22,019 alias rows, 29.9 MB (without `HISTEAN`).
- `main.py` now uses `BotRefsClient` as the identity/alias layer; `bot_analytics.db` remains only as legacy fallback.

## 2026-03-11 Hot Update
- `tools/tg-pharma` now prefers local analytics built from `C:\Users\User\Desktop\SKLIT`.
- Local DB: `D:\code\2026\2\cortex\tools\tg-pharma\data\bot_analytics.db`
- Contents: 92,323 catalog products, 141,496 alias EAN rows, 85,733 purchase lines.
- Fallback order: local analytics SQLite -> VPS SSH history/catalog.

## Фокус
- **PharmOrder** — production на VPS (194.87.140.204:8000). Стабилен, не трогать.
- **TG Digest** — NotebookLM deep research + raw TG chat, задеплоен на VM, timer 03:00 UTC
- **Kwork Automation** — production pipeline (D:\code\2026\3\kwork). Полный цикл: discovery → filter → draft → auto-send → followup.
- **Funding Scanner** — отдельный репо (D:\code\2026\3\funding-scanner). Dashboard на VM (34.159.55.61:8080).
- **MCP Stack** — Context7 (docs), Codex CLI (websearch/code), Exa (semantic search), Playwright (browser), Sequential Thinking, Context Mode
- **Skills** — skill-forge (мета), crewai-agents, langgraph-agents, autoresearch, gsd-method, notebooklm, video, и др.

## Ближайшие шаги
- [x] Рестарт Claude Code → проверить Exa MCP + NotebookLM MCP работают
- [x] Skill Forge — мета-скилл для генерации скиллов через Exa
- [x] 4 новых скилла: crewai-agents, langgraph-agents, autoresearch, gsd-method
- [ ] Dashboard/визуализация инфраструктуры (AI Maestro / Agentlytics / custom) — идея не реализована
- [ ] PharmOrder: tg-pharma live smoke на `resolve_product` / `purchase_stats` / `set_inventory`
- [ ] Funding Scanner: сверка historical rates с оригиналом
- [ ] Перегенерить TELEGRAM_BOT_TOKEN (засвечен в чате)
- [ ] Обновить Claude Code через `winget upgrade Anthropic.ClaudeCode` (закрыть Claude перед этим)

## Ссылки
- Полная история: `DEV_CONTEXT.md`
- Funding арбитраж: `memory/funding-arb.md`
- Субагент playbook: `memory/subagents-playbook.md`
