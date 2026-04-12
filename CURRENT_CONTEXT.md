<!-- L0: Текущий фокус, активные проекты, ближайшие шаги -->
# Current Context

## Фокус
- **Steam Sniper Dashboard** — production на VPS (194.87.140.204:8100). Дашборд + TG-бот, shared SQLite. Карточки с картинками, русский поиск, TradingView графики, алерты. Итерации по фидбеку Лёши.
- **VoiceType / Cypher** — voice-to-text + голосовой ассистент (D:\code\2026\3\voice-type). whisper.cpp Vulkan GPU, server mode. Cypher: AppResolver + RapidFuzz + Gemini planner. 135 тестов.
- **PharmOrder** — production на VPS (194.87.140.204:8000). Стабилен.
- **Klink** — продуктовые видео-шоты с Лёшей @olmogoodwin. Kling 3.0 / Veo 3.1.
- **TG Digest** — на VM, timer 03:00 UTC.
- **Funding Scanner** — dashboard на VM (34.159.55.61:8080).
- **MCP Stack** — Context7, Codex CLI, Exa, Playwright, Context Mode, Browser Use
- **Diary система** — 12 записей.

## Что сделано (session 014, 2026-04-12)
- **Steam Sniper: GSD full cycle** — 4 фазы, 6 планов, 30 requirements, 22 теста, ~3000 LOC
  - Phase 1: db.py (SQLite WAL, CRUD, миграция, price history, alerts, exchange rate)
  - Phase 2: server.py (FastAPI 7 endpoints, background collector 5 мин)
  - Phase 3: dashboard.html (карточки, поиск, charts, activity feed, тема)
  - Phase 4: deploy.py (paramiko → VPS), оба сервиса active
- **Деплой на VPS** — http://194.87.140.204:8100, systemd сервисы, shared SQLite с ботом
- **Post-GSD итерации по фидбеку Лёши:**
  - Русский поиск через Steam Market API (кириллица → перевод → lis-skins cache)
  - Карточки с картинками Steam CDN + rarity color borders
  - 3 поля цен: Вход / Сейчас / Цель
  - Trend arrows (▲/▼ за 2 недели)
  - Цены = lis-skins (множитель ×1.034 к ЦБ, ~79.59₽/$)
  - Ссылки LS + ST (lis-skins + Steam Market) на карточках
  - Activity feed — красивые карточки алертов
  - Время МСК (timezone +03:00)
  - Escape закрывает график
  - display_name/category/image_url в SQLite
- **Max Transcribe** — починен Playwright evaluate API, транскрибированы 9 аудио Лёши
- **Chrome CDP** — обновлена память: Kill→Wait→Launch с --user-data-dir обязательно

## Что сделано (session 013, 2026-04-12)
- **VoiceType: whisper-server mode** — soak test 100 req PASS. Fallback chain: server → CLI GPU → CLI CPU.
- **VoiceType: cleanup policy fix** — fast для <=3s/120chars, остальное Gemini.
- **Max Transcribe** — создан скрипт. Транскрибировано 20 аудио из чата с Лёшей.
- **Steam Sniper proposal** — PDF-предложение для Лёши.

## Что сделано (session 012, 2026-04-07)
- **Анализы крови** — сданы 03.04. Витамин D 27.9 (недостаточность) → D3.
- **Browser Use** — API починен (0.12.5). NotebookLM reauth через Playwright.

## Ближайшие шаги
- [ ] **Steam Sniper: фильтры/меню** — все / избранные / по цене / ящики / уведомления (Лёша просил)
- [ ] **Steam Sniper: трекинг ящиков** — отдельная вкладка, 3000 ящиков с биндами (Лёша)
- [ ] **Steam Sniper: PWA manifest** — ярлык на айфоне (Лёша)
- [ ] **Steam Sniper: Steam цены + история** — БЛОКЕР: нужен отдельный Steam-аккаунт от Лёши
- [ ] **Петличка DJI Mic Mini** — заказать на Ozon
- [ ] **Cypher: Browser Use интеграция** — L3 path
- [ ] **Обкатать /reflect** — 12 diary записей, пора
- [ ] **VoiceType: если качество не устроит** — trim_silence, decode params
- [ ] **Funding: EdgeX verifier** — сравнить fundingRate vs forecastFundingRate
- [ ] **Keenetic Hopper** — WireGuard VPN + policy routing + DoH

## Ссылки
- Steam Sniper Dashboard: http://194.87.140.204:8100
- Steam Sniper код: `tools/steam-sniper/` (отдельный git repo)
- Steam Sniper .planning/: `tools/steam-sniper/.planning/`
- Транскрипция Лёши: `runtime/max_audio/transcriptions.md`
- VoiceType / Cypher: `D:\code\2026\3\voice-type`
- whisper.cpp: `D:\code\2026\3\voice-type\runtime\whisper-cpp\`
- PharmOrder-Local: `~/Desktop/PharmOrder-Local/`
- Субагент playbook: `memory/subagents-playbook.md`
- Funding: `memory/funding-arb.md`
