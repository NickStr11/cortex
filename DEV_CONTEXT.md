# Development Context Log

## Последнее обновление
- Дата: 2026-03-07

## Текущий статус
- Этап: Funding Rate Scanner — полный рабочий инструмент задеплоен.
- Последнее действие: сессия 26 — фикс settled-rate фильтра, добавление predicted rate, верификация данных.
- Текущий фокус: **Funding Rate Scanner** на VM (http://34.159.55.61:8080) + **Kwork Monitor** (auto-scan + AI + TG). Детали: `memory/funding-arb.md`
- Следующий шаг: опубликовать кворки, мониторить funding спреды.

## История изменений

### 2026-03-07 — Funding Scanner: settled filter fix + deploy (сессия 26)
- Что сделано:
  - **Баг settled-rate фильтра**: `ts % bucket_secs < 10` не работал для бирж с нестандартным settlement time (KuCoin 4/12/20 UTC vs Binance 0/8/16 UTC). Фикс: `ts % 3600 < 10` — все settlement timestamps на любой бирже кратны часу.
  - **Predicted rate включён**: последний predicted rate (из 5-мин сканера) добавляется к settled средним — как делают большинство агрегаторов.
  - **Деплой на VM**: обновлены web.py и backfill.py, сервис перезапущен.
  - **Backfill на VM**: 804 новых записей (EdgeX 1260 rates / 29.8 дней, Paradex 210 / 3.1 дня).
  - **Daily backfill timer**: `funding-backfill.timer` — ежедневно в 03:00 UTC (06:00 МСК).
  - **Верификация vs референс**: 30d delta 0.1-0.3% (perfect), 14d 0.0-0.9%, 7d 0.0-0.7%. 1d расходится на 3-9% из-за кэширования референса (обновляется раз в 6+ часов).
  - **Codex CLI xhigh**: получено второе мнение по методологии — нормализация по времени `sum(rates)/sum(hours)×8760`, включение predicted rate — стандарт индустрии.
- Файлы: web.py (settled filter + predicted rate), backfill.py (без изменений в этой сессии)

### 2026-03-06 — Funding Scanner: backfill fixes + data verification (сессия 25)
- Что сделано:
  - **Paradex backfill**: cursor-based pagination (50 pages × 1000 entries), bucketing to 8h windows. Результат: 210 rates (3.1 дня). API стримит каждые 5 сек → 518K entries для 30 дней, полный backfill нереален.
  - **EdgeX backfill**: увеличен size 100→200, добавлена pagination через `nextPageOffsetData`, max 5 pages. Результат: 1260 rates, полные 29.8 дней.
  - **web.py упрощён**: убран bucketing/deduplication step, simple average of settled rates.
  - **Reverse-engineering референса**: `/api/historical/apr` — pre-computed integer arrays, scale=100, `generated_at` обновляется раз в 6+ ч. Frontend = pure render, вся логика на сервере.
  - **Сравнение**: 30d match 0.0-0.2% (excellent), 7d 0.0-1.0% (good), 1d 3-9% (timing issue).
- Файлы: backfill.py (Paradex cursor, EdgeX pagination), web.py (simplified averaging)

### 2026-03-05/06 — Funding Scanner: full build (сессии 23-24)
- Что сделано:
  - **Полный скрипт сканера**: 12 бирж (7 CEX + 5 DEX), 21 монета, async httpx, SQLite DB
  - **Биржи**: Binance, Bybit, OKX, KuCoin, Bitget, Gate, MEXC (CEX) + Hyperliquid, Paradex, EdgeX, Pacifica, Extended (DEX)
  - **Web dashboard**: FastAPI + HTML/CSS/JS, таблица спредов, фильтр по монетам, сортировка, иконки бирж (CoinMarketCap + DEX favicons), real-time обновление 10 сек
  - **Backfill**: 30 дней settled rates для всех бирж, async pagination
  - **DB**: SQLite WAL, UNIQUE index (ts, exchange, coin), rates + spreads tables, trend detection
  - **Scanner loop**: systemd timer каждые 5 мин (predicted rates)
  - **Web service**: systemd service, uvicorn, порт 8080
  - **Deploy на VM**: cortex-vm (34.159.55.61), Google Cloud, europe-west3-b
  - **Алерты**: TG интеграция (форматированные сообщения при спреде >15%/yr)
  - **Аннуализация**: корректная для разных интервалов (1h ×8760, 4h ×2190, 8h ×1095)
- Файлы: exchanges.py, scanner.py, db.py, config.py, alerts.py, web.py, backfill.py, deploy.py, main.py

### 2026-03-05/06 — Kwork Monitor: авто-сканер + AI + бот (сессии 23-24)
- Что сделано:
  - **main.py**: fetch проектов Kwork API → фильтрация keywords/stop-words → параллельная оценка Gemini Flash → отправка в TG. Режимы: `--loop` (polling 15 мин), `--dry-run`
  - **bot.py**: интерактивный бот — scan → AI оценка → TG с кнопками → автоматическая подача offers через pykwork SDK
  - **config.py**: категории (IT=11, боты=41, парсинг=79), keywords (telegram, парсинг, AI, Python), stop-words (iOS, frontend, PHP), цены 3K-300K
  - **create_kwork.py**: Playwright автоматизация создания кворков (contenteditable title, Chosen.js, trumbowyg WYSIWYG, cover upload)
  - **gen_covers.py**: обложки через Gemini Image Gen (банана)
  - **fill_profile.py**: заполнение профиля через Playwright
  - **Proxy**: HTTP proxy обязателен (VPN блокирует kwork.ru)
  - **Dedup**: SQLite seen.db, 5 concurrent Gemini requests (семафор)
- Файлы: main.py, bot.py, config.py, create_kwork.py, gen_covers.py, fill_profile.py, explore_form.py, find_title.py, и др.

### 2026-03-05 — Funding Rate Arbitrage ресёрч (сессия 23)
- Что сделано:
  - **Ресёрч funding rate арбитража**: панель tablefundthe.replit.app (платная подписка), логин/IP задокументированы в memory/funding-arb.md
  - **Верификация данных панели**: проверены реальные рейты через API Binance, Bybit, OKX — данные панели подтверждены
  - **CEX vs DEX анализ**: CEX↔CEX спреды ~0% (все около нуля), CEX↔DEX спреды 10-40%/yr на топ-монетах
  - **API подключены**: Binance premiumIndex, Bybit v5 tickers, Hyperliquid metaAndAssetCtxs, dYdX v4 perpetualMarkets
  - **Текущие спреды** (BTC): Hyperliquid +10.95%/yr vs Binance +0.25%/yr = ~10.7% спред
  - **Лучшие спреды**: DOGE ~41% (dYdX vs Binance), OP ~38% (Hyperliquid vs Binance), AVAX ~22%
  - **Расчёт break-even**: price spread ~0.17% + commissions ~0.08% → ~13 дней при 7%/yr
  - **memory/funding-arb.md создан**: полный контекст — панель, API, рейты, стратегия, следующие шаги
- Файлы: memory/funding-arb.md (новый)
- Решения: CEX↔DEX = основная стратегия. BTC/ETH через Hyperliquid самый безопасный. Следующий шаг — мониторинг-бот с TG алертами.

### 2026-03-04 — Git housekeeping + субагент-playbook (сессия 22)
- Что сделано:
  - **Git sync**: обнаружено 7 непушнутых коммитов в main (сессии 10-20). Main синхронизирован с origin.
  - **Cleanup репо**: удалено 46 мусорных файлов из корня (40+ kwork скриншотов, header-*.png, pharmorder-*.png, screenshots/, YouTube .srt).
  - **Субагент-playbook**: ресёрч лучших практик (obra/superpowers, Addy Osmani, официальные доки). Правила делегирования прописаны в CLAUDE.md и memory/subagents-playbook.md.
  - **CLAUDE.md обновлён**: секция "Делегирование" — субагенты параллельно, Codex CLI xhigh, run_in_background.
  - **Незакоммиченные изменения**: DEV_CONTEXT.md (сессия 21) + heartbeat analyzer (HN ссылки) — закоммичены и пушнуты.
  - **2 стэша**: обнаружены (CLAUDE.md, .mcp.json) — не критичны, оставлены.
- Файлы: CLAUDE.md, DEV_CONTEXT.md, tools/heartbeat/analyzer.py, memory/subagents-playbook.md (новый)
- Решения: Agent Teams (полные команды) — overkill для текущих задач. Custom subagent .md — уже есть. Достаточно параллельных Task-ов + Codex CLI.

### 2026-03-04 — Kwork автоматизация: профиль + кворки + обложки (сессия 21)
- Что сделано:
  - **Kwork профиль**: заполнен через Playwright + HTTP proxy (45.135.29.96:8000, VPN блокирует kwork.ru). Специализация, описание, навыки. Профиль подтверждён скриншотом.
  - **Kwork creation script** (`tools/kwork-monitor/create_kwork.py`): 6 итераций отладки формы:
    - Title: contenteditable div `#editor-title` + `keyboard.type()` (НЕ textarea)
    - Categories: jQuery Chosen.js → `jQuery(sel).val().trigger('chosen:updated').trigger('change')`
    - Type/Вид/Язык/Платформа: labels в `#kwork-save-attributes` → Playwright `.get_by_text().click()`
    - "Продолжить": это `<div class="js-next-step-btn">`, НЕ button. JS `.click()` не работает, только Playwright native click
    - Description/Instruction: trumbowyg WYSIWYG → innerHTML + textarea.value
    - Cover: `input[name="first-kwork-photo[]"]` (не первый file input!)
    - Publish: кнопка "Готово" (не `.js-save-kwork` — тот только сохраняет черновик)
  - **3 кворка подготовлены** (не опубликованы):
    1. "Разработаю Telegram-бота на Python" — 5000₽, 5 дней, Чат-боты
    2. "Спаршу данные с любого сайта" — 3000₽, 3 дня, Парсеры
    3. "Создам AI чат-бота с базой знаний" — 10000₽, 7 дней, ИИ-боты
  - **Генерация обложек** — попробовано 5 подходов:
    1. Pillow (градиент + текст) — убого
    2. HTML+CSS → Playwright screenshot — чистый дизайн, но "дёшево"
    3. Imagen 4.0 (без текста) — неплохие абстракции, текст нужен отдельно
    4. Imagen 4.0 (с текстом) — коверкает кириллицу ("Марсинь", "зат-фот")
    5. **Nano Banana 2 Pro** (`gemini-3-pro-image-preview`) — лучший результат, кириллица ок, но нет контроля над точным визуалом
  - **Nano Banana скилл** создан: `.claude/skills/banana/SKILL.md` — инструкция по генерации через Pro версию
  - **Референсы протестированы**: Emberlen (Behance) и Google Antigravity (antigravity.google) — подкидывались как PIL Image в промпт. Модель ловит общий вайб, но не даёт точного контроля.
- **Открытая проблема**: AI-генераторы не дают контролируемый результат по визуалу. Промпт → рандом. Нет способа точно указать layout, spacing, font weight, glow intensity. Для production-quality обложек нужен либо Figma/Photoshop, либо HTML+CSS (точный контроль) + AI-фон (атмосфера).
- Файлы: create_kwork.py (main script), gen_covers.py (Nano Banana генерация), render_covers.py (HTML→PNG), explore_form.py (DOM exploration), find_title.py (title field investigation), test_step1.py (step navigation test), open_kwork.py (browser opener), covers/*.html (HTML covers), covers/*.png (generated), covers/ref/ (reference screenshots)
- Утилиты: fill_profile.py, send_profile.py, check_profile.py (профиль — выполнено)
- Решения: Kwork.ru использует jQuery + Chosen.js (не Vue). Формы — accordion (4 шага на одной странице). HTTP proxy обязателен (VPN блокирует). Nano Banana 2 Pro — лучший генератор с кириллицей, но для точного дизайна нужен другой подход.

### 2026-03-04 — История приходов + Созвездие матрица + прайс-чекер R&D (сессия 20)
- Что сделано:
  - **История приходов (ReeTov.DBF)**: sozvhist.dbf оказался бонусной программой "Созвездие", а НЕ историей заказов. Найден ReeTov.DBF (85,805 записей, 7,747 EAN, 13 поставщиков) — реестр приходов товаров. Перестроен order_history.db, обновлены SQL-запросы в server.py (ean вместо ean13, nakl_date вместо datezak, pr_w_nds вместо price). Бейджи в UI: "123x (72%)" рядом с поставщиками.
  - **Созвездие (МС "Созвездие")**: исследован маркетинговый союз аптек при ПУЛЬС. Два типа матриц: MANDATORY_MATRIX (О — обязательная) и RECOMMENDED_GOODS (Р — рекомендованная). Текущий квартал 1кв2026: 18,073 EAN (5,614 обязательных + 12,459 рекомендованных). Создан sozvezdie.db (product.dbf + product_post.dbf + workt_5160.dbf → SQLite с таблицами matrix_products и matrix_suppliers). API: `/api/sozvezdie` (по EAN → тип матрицы + рек.цена + список поставщиков), `/api/sozvezdie-batch` (batch-проверка для поиска). UI: маркеры О/Р в поиске, в заголовке товара, на строках поставщиков + инфо-баннер "Товар входит в маркетинговый ассортимент Созвездие (Обязательная матрица, рек.цена: 68₽)".
  - **Прайс-чекер R&D**: розничные цены хранятся в ReeTov.DBF поле BL_ROSN_PR (закупка × наценка из gradeRascen.DBF). Формула: до 300₽→25%, 300-600₽→24%, 600+₽→23%. НО на маминой копии BL_ROSN_PR=0 — расценка делается на рабочем ПК. Нужен ReeTov.DBF с рабочего компа. DataMatrix парсинг работает: GTIN→EAN→поиск в базе (протестировано на 3 кодах: Колдакт бронхо, Цистон, Питавастор).
  - **sync_standalone.py обновлён**: добавлены `_convert_reetov()`, `sync_order_history()`, `_convert_sozvezdie()`, `sync_sozvezdie()`. Main loop: прайсы (60с) + заявки (5с) + история (5мин) + матрица (10мин). sync.bat: добавлен `dbfread` в зависимости.
  - **sklit_sync.zip** пересобран (12 KB) на рабочем столе — готов для мамы.
- Файлы: server.py (supplier-history SQL fix, sozvezdie endpoints, sozvezdie-batch), index.html (supplier hist badges, sozvezdie badges О/Р в поиске/header/offers, info banner), order_history.db (rebuilt from ReeTov), sozvezdie.db (new), sync_standalone.py (reetov + sozvezdie sync)
- Данные: ReeTov.DBF=85,805 приходов (март 2025—март 2026), product.dbf=36,511 товаров матрицы, 120,608 связей товар-поставщик

### 2026-03-04 — Scan items fix + EAN aliases + параллельные сессии (сессия 19)
- Что сделано:
  - **Баг scan items**: при перезапуске sync.bat отсканированные коды исчезали через секунду. Причина: sync.bat открывал браузер без `?key=` → 401, плюс race condition — пустой localStorage мог перезаписать серверные данные.
  - **Фикс sync.bat**: URL теперь включает `?key=...` для автоматической авторизации.
  - **Фикс index.html (VPS)**: добавлен флаг `_scanItemsServerLoaded` — пустой массив НЕ перезаписывает сервер до первой успешной загрузки. Убрано условие `d.items.length` при инит-загрузке.
  - **EAN alias**: Энам (4810703128026, белорусский перепак) привязан к Энам 20мг (оригинальный EAN 8901148245525) — 13 предложений от поставщиков.
  - **Диагностика**: 3 неизвестных EAN (4610166050113, 5060391651965, 4810703128026). Первые два — реально отсутствуют у поставщиков. Третий (Энам) — исправлен.
  - **Параллельные сессии**: работа в двух окнах Claude Code одновременно для ускорения итераций.
  - **sklit_sync.zip** пересобран (11 KB, без .db файлов) для отправки маме.
- Файлы: index.html (VPS, scan items guard), sync.bat (auth URL), sklit_cache.db (VPS, EAN alias)
- Архитектура: для полноценной привязки альтернативных EAN нужна таблица `ean_aliases(ean → id_name)` — пока ручные INSERT в продакшн DB.


### 2026-03-03 — Delta sync + shared scan items (сессия 18)
- Что сделано:
  - **Delta sync**: полная переработка загрузки прайсов. Вместо 89MB полного дампа — только изменения (set-based diff). Первый запуск сохраняет snapshot, последующие шлют дельту (upserts + deletes). Payload gzip-ится при >512KB.
  - **Удалён paramiko/SFTP**: загрузка прайсов теперь HTTP-only (`POST /api/sync/prices-delta`). Зависимость `paramiko` убрана из sync.bat.
  - **`--upload` флаг**: принудительная полная загрузка БД, если нужен ресет.
  - **Мультикомп синк**: протестировано на домашнем ПК (184926 продуктов) + мамин ноутбук (184601 продуктов). Дельты работают — "Без изменений" при повторном запуске.
  - **First-run логика**: новый ПК только сохраняет snapshot, НЕ загружает полный прайс (VPS уже имеет данные от другого ПК).
  - **Shared scan items**: scanItems переехали из localStorage в server-side storage. `GET/POST /api/scan-items` + polling каждые 3 сек. Коды видны на всех компах в реальном времени.
  - **sync.bat фикс**: URL теперь включает API key (`?key=...`) для автоматической авторизации.
  - **Баг дубликатов**: SQL JOIN-based delta давал потери (~18K продуктов). Исправлено на set-based comparison (Python sets полных кортежей).
- Файлы: server.py (delta endpoint + scan-items API), index.html (server sync вместо localStorage), sync_standalone.py (delta sync), sync.bat (убран paramiko)
- Архитектура: любой ПК может загрузить дельту прайсов, VPS — single source of truth, scan items общие для всех браузеров.

### 2026-03-02 — Standalone sync client + Context Mode MCP (сессия 17)
- Что сделано:
  - **Context Mode MCP установлен**: `claude mcp add context-mode -- npx -y context-mode`. Сжимает выход тулов на 98% (56KB→299B), сессии живут значительно дольше. Работает через batch_execute, execute, index, search, fetch_and_index.
  - **Диагностика**: sync_standalone.py (в sklit_sync.zip) не загружал прайсы на VPS — только забирал заявки. Поэтому счётчик не обновлялся.
  - **Фикс sync_standalone.py**: дописан полный двусторонний синк (~420 строк, zero deps на проект):
    - `sync_prices()`: watch pr_all.dbf mtime → convert() DBF→SQLite+FTS → upload на VPS
    - `pull_and_write()`: poll VPS → zayava.DBF (было и раньше)
    - Встроены: `convert()`, `_build_supplier_map()`, `_read_apteks()`, supplier map, apteks meta
  - Архив `sklit_sync.zip` пересобран на рабочем столе
  - Протестировано на домашнем ПК — прайсы загрузились на VPS
  - **VPS.md** обновлён: два варианта запуска, настройка на чистом ПК, таблица диагностики
  - План автозагрузки: `.pyw` + `shell:startup` или Task Scheduler
- Файлы: sync_standalone.py (обновлён), sync.bat (обновлён), VPS.md (обновлён)

### 2026-03-02 — PharmOrder VPS полировка (сессия 16)
- Что сделано:
  - **Sync-статус в header**: `GET /api/sync/status` — зелёная/жёлтая/красная точка + возраст базы, pending exports count
  - Sync-индикатор поллит каждые 30 сек, VPS only (в local mode скрыт)
  - Кнопка "Обновить прайсы" скрывается в VPS mode (sync_client обновляет)
  - **Поиск фикс**: contains-match вместо starts-with only. "цитрал" теперь находит и "Цитралгин" и "Гель цитралгин флебогель". Starts-with идут первыми в сортировке.
  - **Фильтр нулевых остатков**: товары без остатков у всех поставщиков не показываются в поиске (EAN-поиск не фильтруется)
  - **Batch auto_distribute()**: одно подключение к БД, batch SQL (IN (...)) вместо per-item lookup. 50 позиций: 3мс вместо ~10с.
  - **`POST /api/cart/batch`**: добавление всех позиций автозаказа одним запросом вместо sequential await per item (~1 мин → мгновенно)
  - **UI cleanup**: убран buildTag ("build 2026-02-12-7"), убрана статистика ("189k / 55 пост."), Cloud OK + sync indicator справа
  - **Серая полоса сбоку**: border/shadow на закрытых панелях убраны (только на open)
  - Прайсы обновлены и залиты на VPS (189k продуктов, 86.5MB)
  - VPS.md — документация для работы на рабочем ПК (доступы, архитектура, команды)
- Файлы: server.py, db.py, static/index.html, VPS.md (новый)

### 2026-03-02 — PharmOrder на VPS (сессия 15)
- Что сделано:
  - **PharmOrder задеплоен на VPS** (194.87.140.204:8000) — systemd service, auth middleware (API key)
  - Auth: `X-API-Key` header / cookie / `?key=` query param. `/health` без auth. Cookie ставится на 30 дней.
  - **Sync архитектура**: VPS (PharmOrder) ← sync → локальный ПК (sync_client.py)
  - `POST /api/sync/upload-db` — sync-client заливает sklit_cache.db (90MB, 190k продуктов)
  - `GET /api/sync/pending-exports` + `POST /api/sync/confirm-export` — очередь экспортов
  - `prepare_export()` в db.py — строит записи для zayava.DBF без прямой записи (VPS mode)
  - `export_to_sklit()` рефакторнут: общая `_build_export_records()` + прямая запись только в local mode
  - Supplier map + apteks info сохраняются в SQLite при convert() — VPS читает из DB, не из DBF
  - `_build_supplier_map()` и `_read_apteks()` — SQLite fallback когда DBF файлов нет
  - `needs_update()` — VPS mode: не пытается конвертить без DBF
  - **sync_client.py** (~180 строк): watch pr_all.dbf → convert → upload DB; poll exports → write zayava.DBF → confirm
  - **Batch lookup**: `POST /api/lookup-batch` — все EAN за один запрос. **16x ускорение** (400ms vs 6.3s на 20 кодов)
  - Frontend `processScanQueue()` переписан: один batch запрос вместо sequential await per item
  - **UI cloud history**: consumed выгрузки серые (opacity 0.45), badge на кнопке "Облако" с числом новых
  - E2E тест пройден: заказ на VPS → sync-client забрал → zayava.DBF с правильными ID_PRICE/ID_POST/ID_A/ID_GRP
  - Локальный режим (run.bat) не затронут — мама работает как раньше
- API key VPS: `464AFZ-j5lluujCAgO4JrKkLD8twd_U5Hys5yGlTRck`
- URL: `http://194.87.140.204:8000/?key=464AFZ-j5lluujCAgO4JrKkLD8twd_U5Hys5yGlTRck`
- Файлы: server.py, db.py, sync_client.py (новый), sync_client.bat (новый), .env.sync (новый), .env.example (новый)

### 2026-03-02 — PharmOrder планирование + TG уведомления (сессия 14)
- Что сделано:
  - Удалены неиспользуемые bash-скрипты (init-project.sh, setup-vm.sh)
  - Починен /screenshot — теперь читает из буфера обмена напрямую (PowerShell)
  - Проверена VM cortex-vm: SSH только через `gcloud compute ssh`, daily digest таймер активен (06:00 MSK)
  - Heartbeat запущен: найден Context Mode MCP (98% сжатие контекста, 524 HN points) — записан в backlog
  - TG уведомления для мамы: relay_server.py на VPS дополнен notify_telegram(), мама (Luda, chat_id 7255623391) получает "Новая заявка: X позиций" при каждом POST /api/scans
  - paramiko установлен на Windows для SSH к VPS
  - Исследован PharmOrder: FastAPI + SQLite + DBF, экспорт пишет в C:\SKLIT\zayava.DBF (бинарный append)
  - Спланирована архитектура миграции: PharmOrder на VPS, маленький клиент на рабочем компе забирает экспорт и пишет в DBF локально
- Решения: PharmOrder можно перенести на VPS без апгрейда сервера. Единственная привязка к локалке — запись в zayava.DBF, решается клиентским скриптом. Нужна полная версия с рабочего компа.

### 2026-03-01 — TG Bridge + SVG эксперименты (сессия 13)
- Что сделано:
  - tools/tg-bridge/main.py — Telegram → Claude Code бридж через long polling
  - Бот @cipher_think_bot принимает сообщения, прокидывает в `claude -p`, возвращает ответ
  - Whitelist по user_id (691773226), история 20 сообщений (history.json), /new для сброса
  - Фиксы: Windows encoding (PYTHONIOENCODING=utf-8), nested session (unset CLAUDECODE env)
  - dotfiles-claude синкнут с текущим ~/.claude/ (aboutme, ai-knowledge обновлены, push)
  - Эксперимент: image → SVG конвертация (vtracer, Inkscape CLI trace). Inkscape 64-scan лучший результат для сложных лого, но автотулы не тянут разбивку на семантические объекты
  - Inkscape установлен через winget (1.4.3)
- Решения: `claude -p` без `--continue` (конфликтует с интерактивной сессией), вместо этого ручная history.json. Автоматический трейсинг упирается в потолок на сложных иллюстрациях — нужен Gemini 3.1 Pro или ручная работа.

### 2026-03-01 — Telethon авторизован + дайджесты в продакшне (сессия 12)
- Что сделано:
  - Telethon авторизован через QR-код (из PowerShell пользователя). Блокер решён!
  - Сессия cortex_userbot.session создана и загружена на VM
  - Первый дайджест vibecod3rs: 1494 сообщения → Claude субагент (GOOGLE_API_KEY был просрочен)
  - Новый GOOGLE_API_KEY получен, Gemini digest работает
  - /tg-digest скилл создан (Telethon fetch → Gemini analysis → .md в канал)
  - Группа Вайбкодеры добавлена в config.py (vibecod3rs)
  - AI Mindset: username не работал → заменён на числовой ID (-1001497220445)
  - digest.py/daily.py: дайджест отправляется как .md файл (sendDocument), не текстом
  - Systemd timer: 03:00 UTC (06:00 MSK), обе группы фетчатся
  - VM: .env почищен от комментариев, все файлы синхронизированы
  - PharmOrder: улучшен поиск (multi-word fallback: "нурофен леди" → "Нурофен экспресс леди")
  - Создан .docx с заявкой для аптеки, отправлен маме в TG
- Решения: QR-авторизация > код (коды Telegram не доставлялись). Gemini > Claude для дайджестов (экономия токенов). .md файл > текст (нет лимита 4096 символов).

### 2026-03-01 — TG Monitor написан (сессия 11)
- Что сделано:
  - tools/tg-monitor/monitor.py — Telethon userbot, читает сообщения из TG-групп, сохраняет в JSON
  - tools/tg-monitor/digest.py — дайджест через Gemini, отправка в Telegram
  - tools/tg-monitor/config.py — список групп, фильтры по длине и ключевым словам
  - tools/tg-monitor/daily.py — объединяет heartbeat + tg-monitor в один запуск
  - tools/tg-monitor/deploy/ — systemd service + timer + setup-vm.sh
  - .gitignore обновлён — data/tg-groups/ и *.session исключены
- Блокер: Telethon auth — коды не приходили (решён в сессии 12 через QR).

### 2026-02-28 — Контент-пайплайн запущен (сессия 10)
- Что сделано:
  - PR #46 смержен (сессия 9 docs), разрешены конфликты с Agent-Reach из main
  - tools/pipeline/main.py — написан пайплайн DEV_CONTEXT → Gemini 3 Flash → Telegram
  - Gemini 3 Flash (gemini-3-flash-preview) — заменил Anthropic API (ключа нет)
  - GitHub Actions pipeline.yml — триггер на push DEV_CONTEXT.md в main
  - GitHub Secrets: GOOGLE_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
  - Пайплайн протестирован локально и через Actions — посты уходят в канал
  - Гайд "Новый комп за 5 минут" отправлен в Telegram (message_id=830)
  - Разобрались что VM нужна только для 24/7 бота, для пайплайна — не нужна
  - Изучили подход Серёжи Риса (sereja.tech) — публичный блог Hugo+Vercel, 82 статьи
- Решения: GitHub Actions > VM cron для пайплайна. GOOGLE_API_KEY вместо ANTHROPIC_API_KEY.
- Ключи в чате засвечены — перегенерить GOOGLE_API_KEY и TELEGRAM_BOT_TOKEN.

### 2026-02-27 — Personal OS v2 + Google Cloud VM + контент-пайплайн (сессия 9)
- Что сделано:
  - Разбор двух AI Mindset видео (Founder OS #22 + POS sprint) — полный анализ субтитров через субагентов
  - Эксперимент: статья из логов сессии 8 ("Как я проверил свой AI-проект на уникальность") — получилось читабельно
  - dotfiles-claude: приватный GitHub репо с настройками ~/.claude/ (CLAUDE.md, aboutme.md, ai-rules, skills, memory)
  - Хук sync-memory.py: MEMORY.md автоматически пушится в dotfiles-claude при завершении сессии
  - Хук pull-dotfiles.py: автопулл dotfiles при старте сессии (1 раз в день)
  - setup.sh: одна команда разворачивает всё на новом компе
  - Google Cloud VM: cortex-vm (e2-small, europe-west3-b, Ubuntu 22.04, IP 34.159.55.61)
  - Cortex склонирован на VM, Python + git установлены
  - Telegram бот @cipher_think_bot подключён к приватному каналу (chat_id: -1001434709177)
  - Токен и chat_id сохранены в .env на VM
- Решения: контент-пайплайн (сессия → статья → Telegram) — следующий конкретный шаг. Нужен Anthropic API ключ на VM.
- Ожидание: экспорт Telegram канала с личными заметками и аудио для анализа.

### 2026-02-26 — Reality check + cleanup + Research Agent-Reach (сессия 8)
- Что сделано:
  - idea-reality MCP подключен и протестирован (добавлен в прошлой сессии, заработал после рестарта)
  - Cortex reality check: signal 74/100, прямой конкурент Atman36/personal-assist-orchestrator (0 stars, macOS-only, 1 день работы). Cortex объективно зрелее.
  - Детальное сравнение Cortex vs pcorp: мы — CLI toolkit (cloud-first, cross-platform), они — standalone daemon (macOS, SQLite state)
  - #38 (Remote Control API) — исследовано, закрыто. Это remote desktop для CLI, не API для оркестрации. Dispatch через Issues остаётся.
  - #42 (idea-reality MCP) — закрыто, проверка пройдена.
  - Cipher (OpenClaw агент на VPS 89.19.208.38) — ревью: мёртвый проект, Docker не запущен, workspace-свалка. Всё полезное уже в Cortex.
  - cipher-knowledge репа — уже в архиве на GitHub.
  - VPS Timeweb — решено удалить (не выполняет функций, деньги списываются).
  - Исследован проект Agent-Reach (1.7k stars): Zero API fees подтверждено (скрейпинг, cookies, free tiers)
  - Вердикт по Agent-Reach: полная замена нецелесообразна, точечная интеграция (Jina Reader, bird CLI)
  - Отчет: research/agent-reach-analysis.md
- Решения: Открытых Issues — 0. Cipher закрыт, VPS удаляется. Cortex — единственный активный проект.

### 2026-02-25 — Council + Research + Personal OS (сессия 7)
- Что сделано:
  - /council → сгенерирован спринт из 4 задач (P2-P5, P1 убран — API ключ не нужен)
  - Задиспатчены Jules: #30 (metrics tests), #31 (CONTRIBUTING+LICENSE), #32 (new-project), #33 (heartbeat PH)
  - Jules закрыл 3/4: PR #34 (docs), PR #35 (metrics 99% coverage), PR #36 (scaffold). #33 в работе.
  - AI Mindset дайджест: 8 видео → research/ai-mindset-digest.md (закоммичен)
  - Анализ дневника: 603 записи Obsidian (2022-2026) → aboutme.md (Personal OS foundation)
  - Обсуждение: Obsidian как инфраструктура для AI-агентов (skills, rules, MCP)
  - Personal OS setup: структура AI/ в Obsidian vault (aboutme, rules, skills, knowledge)
  - Симлинки ~/.claude/ → Obsidian vault (aboutme.md, ai-rules/, ai-knowledge/)
  - Глобальный ~/.claude/CLAUDE.md создан — ссылается на aboutme + rules + knowledge
  - Философия в aboutme.md дополнена: эволюция мировоззрения (стоицизм → тёмный поворот → детерминизм), ключевые авторы, главное противоречие
- Решения: ANTHROPIC_API_KEY не нужен. Personal OS v1 настроен — Obsidian = single source of truth через симлинки.

### 2026-02-25 — Sync + финализация (сессия 6)
- Что сделано:
  - Jules завершил все 3 задачи: /quick-commit (PR #27), /metrics (PR #28), README landing (PR #29)
  - DEV_CONTEXT.md обновлён, прогресс синхронизирован
- Решения: Cortex полностью завершён. Все запланированные фичи реализованы.

### 2026-02-24 — Council спринт + cleanup (сессия 5)
- Что сделано:
  - `/learn` — мета-анализ: Jules >> Codex, 0% тестов → 97%, hotspots в heartbeat
  - `/council` — сгенерирован план из 5 задач (P1-P5)
  - Закрыты stale Issues: #7, #10, #13
  - PROJECT_CONTEXT.md — все 6 этапов и DoD отмечены [x] (PR #23)
  - DEV_CONTEXT.md синхронизирован с реальностью (PR #22)
  - Задиспатчены Jules: /quick-commit (#24), /metrics (#25), README (#26)
  - Установлен uv (был не установлен на системе)
- Решения: Cortex feature-complete. Следующий шаг — реальный продукт (фриланс-бот) или open-source launch.

### 2026-02-24 — Heartbeat + forge-port + тесты (сессия 4)
- Что сделано:
  - Heartbeat модуль: Python-скрипт сканирует HN + GitHub Trending + Reddit
  - `/heartbeat` slash-команда для ручного запуска
  - `.github/workflows/heartbeat.yml` — cron каждые 3 дня
  - Первый запуск heartbeat: 6 HN постов, 15 GitHub репо
  - Auto-review PR: `.github/workflows/code-review.yml` (Jules, PR #14)
  - Forge-port: 3 хука, 1 агент, 3 команды из claude-forge (PR #19)
  - Jules добавил Reddit в heartbeat (PR #18)
  - Jules написал тесты для heartbeat: 97% coverage (PR #21)
- Решения: Codex плохо справляется с ресёрч-задачами, Jules надёжнее для кода.

### 2026-02-23 — Тест Codex + исследование рынка (сессия 3)
- Что сделано:
  - Протестирован Codex через chatgpt.com — полный цикл за 1м 45с (PR #8)
  - Собран дайджест по AI-агентам (Codex/Jules/Devin/Claude Code/Cursor/Aider)
  - Зафиксирован паттерн "AI-корпорация" через GitHub Issues

### 2026-02-23 — Исследование и инициализация (сессия 2)
- Что сделано:
  - Исследован референс-воркфлоу "Персональная Корпорация"
  - Скопирован шаблон → D:\code\2026\2\cortex
  - PROJECT_CONTEXT.md заполнен
  - /council и /dispatch команды созданы
  - GitHub Apps подключены (Jules + Codex)
  - AGENTS.md, gh CLI авторизован
  - Первый полный цикл: Issue #2 → Jules → PR → Merge

## Технические детали
- Архитектура: CLI команды → GitHub Issues → AI агенты (Jules/Codex) → PR → Human merge
- Стек: Python 3.12, uv, beartype, Claude Code CLI, GitHub Actions
- Интеграции: Context7 MCP, Sequential Thinking MCP, Playwright MCP, idea-reality MCP, Codex CLI MCP
- Inkscape 1.4.3 установлен (winget), доступен для CLI trace bitmap

## Инвентарь

### Команды (14)
council, dispatch, heartbeat, handoff, status, verify, new-project, screenshot, tdd, build-fix, learn, quick-commit, metrics, tg-digest, daily

### Агенты (4)
architect, code-reviewer, security-auditor, verify-agent

### Хуки (8)
check-secrets, check-filesize, pre-commit-check, protect-main, grab-screenshot, output-secret-filter, mcp-usage-tracker, expensive-tool-warning

### Tools (6)
heartbeat (HN/Reddit/GitHub trends), pipeline (DEV_CONTEXT → article → Telegram), tg-monitor (TG groups → digest → Telegram), tg-bridge (Telegram → Claude Code bridge), funding-scanner (12 бирж × 21 монета, web dashboard, VM deploy), kwork-monitor (auto-scan + AI оценка + TG бот)

### Workflows (4)
heartbeat.yml (cron), code-review.yml (PR review), jules-trigger.yml (auto-trigger), pipeline.yml (DEV_CONTEXT → Telegram)

## Известные проблемы
- Codex не триггерится через Issues — только через chatgpt.com вручную
- Codex плохо справляется с ресёрч/кодовыми задачами — годится для доков/шаблонов
- tools/video/extract.py: баг — хардкодит output dir для URL (workaround: --output flag)

## Прогресс
- [x] /council — AI-консилиум
- [x] /dispatch — создание Issues с назначением агентов
- [x] GitHub Apps (Jules + Codex)
- [x] AGENTS.md
- [x] gh CLI авторизован
- [x] Первый цикл: Issue → Jules → PR → Merge
- [x] Codex протестирован (PR #8)
- [x] Heartbeat — авто-ресёрч трендов (HN + GitHub + Reddit)
- [x] Auto-review PR (code-review.yml)
- [x] Forge-port: хуки, агент, команды
- [x] Тесты heartbeat (97% coverage)
- [x] DEV_CONTEXT.md и PROJECT_CONTEXT.md синхронизированы
- [x] Все milestones и DoD выполнены
- [x] Stale Issues закрыты (#7, #10, #13)
- [x] /quick-commit команда (PR #27, Jules)
- [x] /metrics — трекинг агентов (PR #28, Jules)
- [x] README как landing page (PR #29, Jules)
- [x] Metrics tests 99% coverage (PR #35, Jules)
- [x] CONTRIBUTING.md + LICENSE (PR #34, Jules)
- [x] /new-project scaffold (PR #36, Jules)
- [x] Heartbeat + Product Hunt (#33, Jules)
- [x] Research: Agent-Reach (research/agent-reach-analysis.md)
- [x] AI Mindset дайджест (research/ai-mindset-digest.md)
- [x] aboutme.md — персональный контекст (Obsidian vault)
- [x] Personal OS v1: Obsidian vault → симлинки → ~/.claude/ (aboutme, rules, knowledge)
- [x] idea-reality MCP — pre-build проверка идей на уникальность
- [x] Cortex reality check (signal 74, конкурент слабее)
- [x] #38 Remote Control API — исследовано, не подходит для dispatch
- [x] Cipher cleanup — репа в архиве, VPS удаляется
- [x] dotfiles-claude — приватный репо, автосинк памяти между компами
- [x] Google Cloud VM (cortex-vm, e2-small, 34.159.55.61) — задеплоен, Cortex склонирован
- [x] Telegram бот подключён к приватному каналу (chat_id: -1001434709177)
- [x] Контент-пайплайн: DEV_CONTEXT → Gemini 3 Flash → Telegram (PR #47, pipeline.yml)
- [x] TG Monitor: Telethon userbot + Gemini digest + daily runner (tools/tg-monitor/)
- [x] Systemd timer для daily digest на VM (deploy/cortex-daily.timer)
- [x] Telethon авторизован (QR), сессия на VM, дайджесты работают
- [x] GOOGLE_API_KEY обновлён
- [x] /tg-digest скилл
- [x] TG Bridge: Telegram → Claude Code через @cipher_think_bot (tools/tg-bridge/)
- [x] dotfiles-claude синкнут с текущим состоянием
- [x] TG уведомления маме при новых заявках (relay → @cipher_think_bot → Luda)
- [x] /screenshot починен (буфер обмена → Read tool)
- [x] Cleanup: удалены init-project.sh, setup-vm.sh
- [x] PharmOrder → VPS: получить полную версию с рабочего компа
- [x] PharmOrder → VPS: деплой (194.87.140.204:8000) + auth middleware + sync endpoints
- [x] PharmOrder → VPS: sync_client.py для DBF экспорта + прайс-синк
- [x] PharmOrder → VPS: batch lookup (16x speedup), cloud history UI
- [x] PharmOrder → VPS: sync-статус в header, поиск фикс (contains), batch автозаказ + корзина
- [x] PharmOrder → VPS: UI cleanup (buildTag, stats, панели), VPS.md документация
- [x] PharmOrder → VPS: sync_standalone.py дописан (загрузка прайсов + экспорт), протестировано
- [x] Context Mode MCP установлен и работает (98% сжатие контекста)
- [x] PharmOrder → VPS: delta sync (HTTP-only, без SFTP, set-based diff)
- [x] PharmOrder → VPS: shared scan items (server-side, real-time sync 3 сек)
- [x] PharmOrder → VPS: мультикомп экосистема (домашний ПК + мамин ноутбук работают)
- [x] PharmOrder: история приходов (ReeTov.DBF → order_history.db, бейджи "72% Катрен")
- [x] PharmOrder: Созвездие матрица (О/Р маркеры в поиске, header, таблице поставщиков)
- [x] PharmOrder: sozvezdie.db с привязкой поставщиков к товарам матрицы (120K связей)
- [x] PharmOrder: batch endpoint sozvezdie-batch для поиска
- [ ] PharmOrder: прайс-чекер (нужен ReeTov.DBF с рабочего ПК, BL_ROSN_PR=0 на маминой копии)
- [ ] PharmOrder: ИИ-рекомендации (Gemini — синтез: история + цена + матрица → совет)
- [ ] PharmOrder: автозаявка (скорость продаж + остатки → прогноз)
- [ ] PharmOrder → VPS: кассовый комп (принести sklit_sync, тест)
- [ ] Перегенерить TELEGRAM_BOT_TOKEN (засвечен в чате)
- [ ] Анализ экспорта Telegram канала (заметки + аудио)
- [x] Kwork: профиль заполнен через Playwright + proxy
- [x] Kwork: create_kwork.py — автоматизация создания кворков (все 4 шага)
- [x] Kwork: Nano Banana скилл (`.claude/skills/banana/SKILL.md`)
- [ ] Kwork: обложки (нет контроля визуала через AI-генераторы)
- [ ] Kwork: опубликовать 3 кворка
- [x] Git housekeeping: 7 непушнутых коммитов main → синхронизированы
- [x] Cleanup репо: 46 мусорных файлов удалены
- [x] Субагент-playbook: правила делегирования в CLAUDE.md + memory
- [x] Funding Rate Scanner: полный стек (12 бирж, 21 монета, SQLite, FastAPI web dashboard)
- [x] Funding Rate Scanner: backfill 30 дней settled rates + daily timer
- [x] Funding Rate Scanner: deploy на VM (34.159.55.61:8080, systemd service + timer)
- [x] Funding Rate Scanner: верификация vs референс (30d delta <0.3%)
- [x] Kwork Monitor: auto-scan Kwork API + Gemini AI оценка + TG алерты
- [x] Kwork Monitor: интерактивный бот (bot.py) — scan → оценка → auto-offer
- [x] Kwork Monitor: create_kwork.py — автоматизация публикации кворков
- [ ] Kwork: опубликовать 3 кворка
- [ ] ~~Фриланс-бот~~ (отложен)

## Идеи / Backlog
- Context Mode MCP (github.com/mksglu/claude-context-mode) — сжатие выхода тулов на 98%, сессии живут 3ч вместо 30мин
- PharmOrder cloud: HTTPS (caddy/nginx + certbot), накладные sync
- Контент-пайплайн: DEV_CONTEXT → статья через Claude API → Telegram канал (приватный → потом публичный)
- Personal OS v2: Obsidian MCP (поиск по vault в реальном времени)
- Self-improving rules (агент пишет новые правила при ошибках)
- Веб-дашборд для визуализации Issues/PR pipeline
- Open-source launch: r/ClaudeAI, Show HN
