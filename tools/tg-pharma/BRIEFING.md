# tg-pharma — брифинг для Клода (обновлён 2026-03-12)

Этот файл описывает актуальное состояние проекта. Читай его перед тем как лезть в код.

---

## Что это

Телеграм-бот `@pharmorder_ops_bot` — приватный ассистент для аптеки поверх PharmOrder.

**Где живёт:** `D:\code\2026\2\cortex\tools\tg-pharma\`
**Запуск:** `uv run python main.py`
**НЕ на VPS** — бот крутится локально (домашний ПК или мамин ноут).

---

## Ключевые файлы

| Файл | Роль |
|------|------|
| `main.py` | Telegram polling, диспетчер actions, pending flow |
| `intent.py` | Gemini → ParsedIntent (action + query + qty + period) |
| `pharm_api.py` | HTTP-клиент к PharmOrder VPS (поиск, инвентарь) |
| `history_client.py` | SSH к VPS order_history.db, BotRefsClient, LocalAnalyticsClient |
| `build_refs.py` | Строит bot_refs.db из СКЛИ Т данных |
| `data/bot_refs.db` | Identity/alias слой: 91K names, 90K makers, 22K alias rows |

---

## Архитектура данных

```
Запрос пользователя
       │
  IntentParser (Gemini Flash)
       │
  ParsedIntent {action, query, qty, period}
       │
  ┌────┴─────────────┬──────────────┬──────────────┐
  │                  │              │              │
BotRefsClient   PharmOrderAPI   HistoryClient  LocalAnalytics
(data/bot_refs.db) (VPS HTTP)  (VPS SSH→SQLite) (fallback)
  │                  │              │
 EAN→id_name     /api/search    order_history.db
 canonical name  /api/inventory  (25MB, 85K приходов)
 alias lookup    /api/product    sklit_cache.db
                                 (78MB, 184K продуктов)
```

**Два бота на разных токенах (ВАЖНО):**
- `@cipher_think_bot` — рабочий бот аптечных заявок (`TELEGRAM_BOT_TOKEN` в root .env). НЕЛЬЗЯ ТРОГАТЬ.
- `@pharmorder_ops_bot` — этот бот (`PHARMA_TELEGRAM_BOT_TOKEN` в `tools/tg-pharma/.env`).

---

## .env переменные

`tools/tg-pharma/.env` (создать если нет):

```env
PHARMA_TELEGRAM_BOT_TOKEN=<токен @pharmorder_ops_bot>
PHARMA_ALLOWED_CHAT_IDS=691773226
PHARMORDER_API_BASE=http://194.87.140.204:8000
PHARMORDER_API_KEY=464AFZ-j5lluujCAgO4JrKkLD8twd_U5Hys5yGlTRck
GOOGLE_API_KEY=<Gemini API key>
PHARMORDER_SSH_HOST=194.87.140.204
PHARMORDER_SSH_USER=root
PHARMORDER_SSH_PASSWORD=<пароль VPS>
PHARMORDER_REMOTE_ORDER_HISTORY_DB=/opt/pharmorder/src/data/order_history.db
PHARMA_REFS_DB=data/bot_refs.db
PHARMA_GEMINI_MODEL=gemini-3-flash-preview
```

Бот также подтягивает `../../.env` (root cortex) если там есть нужные переменные.

---

## Поддерживаемые actions

### Read-only (более агентный режим)

| Action | Что делает |
|--------|-----------|
| `resolve_product` | Найти товар: имя, EAN, поставщики, цены, историю закупок |
| `purchase_stats` | История закупок по товару за период |
| `compare_suppliers` | Сравнить поставщиков по товару (начат) |
| `compare_periods` | Сравнить периоды по товару (начат) |
| `show_inventory` | Показать остаток по товару |
| `chat` | Свободный разговор / уточнение |

### Write (только через preview → confirm → apply)

| Action | Что делает |
|--------|-----------|
| `set_inventory` | Установить остаток |
| `add_inventory` | Добавить к остатку |
| `subtract_inventory` | Убрать из остатка |
| `delete_inventory` | Удалить позицию |
| `restore_inventory` | Восстановить последнюю удалённую |

### Batch mode (пачка операций)
`start_batch` → добавляй команды → `show_batch` → `apply_batch`

---

## Периоды

Бот понимает как именованные, так и произвольные периоды:

```
last_month         → прошлый месяц
this_month         → текущий месяц
last_90_days       → 90 дней
last_180_days      → полгода
all_time           → всё время
last_17_days       → "за последние 17 дней"
last_41_days       → "за последние 41 день"
last_8_months      → "за 8 месяцев"
last_2_years       → "за 2 года"
```

Динамические периоды (`last_N_days/months/years`) протянуты через `intent.py` → `history_client.py` → SSH-запрос.

---

## Память чата (chat_state.json)

Бот помнит в рамках сессии:
- `last_product_focus` — последний упомянутый товар
- `last_period` — последний период
- `recent_turns` — последние реплики
- `last_deleted` — последняя удалённая позиция (для restore)

Это позволяет follow-up сценарии:
```
— какой у нас азитромицин?
— а 500?          ← понимает что спрашивает про азитромицин 500
— удали эту позицию
— верни назад
```

---

## Identity/Alias слой (bot_refs.db)

`BotRefsClient` в `history_client.py` — основной слой для резолвинга.

**Что умеет:**
- По EAN → canonical name + maker + id_name
- По имени → canonical name + альтернативные EAN одного товара
- Понимает что разные EAN = один товар (дозировки, фасовки)
- `build_refs.py` собирает из СКЛИ Т: `pr_all.dbf` + `lsprtov.dbf`

**Fallback:** если `bot_refs.db` нет — падает на `LocalAnalyticsClient` (bot_analytics.db) → PharmOrder API.

---

## Query variants (история_client.py)

`build_query_variants(query)` генерирует варианты для поиска:
- Простые русские окончания: `периневу → перинева`, `перинев`
- Token fallbacks по первым N словам
- LIKE-паттерны для SQLite

Это фиксит проблему: `ко периневу` не матчилось на `ко-перинева`.

---

## Pending flow (write-операции)

```
Пользователь: "поставь азитромицин 500 = 10"
     ↓
intent.py → {action: set_inventory, query: "азитромицин 500", qty: 10}
     ↓
Поиск кандидатов → список 1-5 товаров
     ↓
Бот: "Нашёл: [1] Азитромицин 500 мг, EAN 460xxxxxxx, Тева
       Установить остаток = 10? Ответь 1 для подтверждения"
     ↓
Пользователь: "1"
     ↓
apply → PharmOrder API → "✓ Остаток установлен: 10"
```

- Токен pending = `uuid.hex` (16 символов)
- TTL = 900 секунд (15 мин)
- Lock через `threading.Lock()`
- Cleanup протухших по интервалу

---

## Текущее состояние (март 2026)

### Работает ✅
- Поиск товаров (`resolve_product`) с историей закупок
- `purchase_stats` с dynamic periods (за N дней/месяцев/лет)
- Все write-операции через confirm flow
- `restore_inventory` (последняя удалённая позиция)
- Batch mode (пачка операций)
- Follow-up по контексту чата
- Проверено на живых данных: азитромицин 500, ко-перинева

### В процессе / не добито 🔧
- `compare_suppliers` — скелет есть, рендер неполный
- `compare_periods` — скелет есть, рендер неполный
- Inventory insights (что заканчивается, аномалии) — не начато

### Известный блокер ⚠️
- При запуске нужно убедиться что нет второго процесса с тем же `PHARMA_TELEGRAM_BOT_TOKEN`
  (409 Conflict убьёт оба). Именно поэтому сделали отдельный токен для ops-бота.

---

## Следующие шаги (в порядке приоритета)

1. **Live smoke** — запустить `@pharmorder_ops_bot`, проверить `ко-перинева` и dynamic periods в живом чате
2. **Добить compare_suppliers** — сравнение по поставщикам с diff ценой
3. **Добить compare_periods** — YoY/MoM сравнение по товару
4. **Inventory insights** — что заканчивается, отклонения от нормы
5. **Связать inventory + auto-order** — остатки → прогноз заказа

---

## Целевая схема продукта

```
inventory (data/bot_refs.db + PharmOrder API)
    ↓
tg-pharma (operator console)
    ↓
auto-order (decision engine) — будущее
```

---

## VPS (PharmOrder, 194.87.140.204)

Сам бот на VPS **не крутится** — только данные.

| Что на VPS | Где |
|-----------|-----|
| PharmOrder API | `http://194.87.140.204:8000` |
| sklit_cache.db | `/opt/pharmorder/src/data/sklit_cache.db` (78MB, 184K продуктов) |
| order_history.db | `/opt/pharmorder/src/data/order_history.db` (25MB, 85K приходов) |
| sozvezdie.db | `/opt/pharmorder/src/data/sozvezdie.db` (22MB, Созвездие матрица) |
| inventory.db | `/opt/pharmorder/src/data/inventory.db` |

PharmOrder VPS docs: `/opt/pharmorder/README.md`
