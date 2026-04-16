# Steam Sniper — задача для Codex

## Что за проект

Steam Sniper — персональный дашборд для мониторинга цен CS2 скинов на lis-skins.com. Два пользователя (Никита и Лёша). Production на VPS.

**Стек:** Python 3.12+, FastAPI, SQLite (WAL mode), vanilla JS (ES modules), TradingView Lightweight Charts, Telegram бот.

**Репозиторий:** `tools/steam-sniper/` (внутри монорепо cortex)

**Production URL:** http://194.87.140.204:8100

## Структура проекта

```
server.py          — FastAPI сервер (783 строк): REST API + background collector
db.py              — SQLite слой (397 строк): watchlist, price_history, user_lists, alerts
category.py        — Классификатор CS2 предметов (160 строк): 15 категорий
dashboard.html     — HTML shell (240 строк): табы, панели
deploy.py          — Деплой на VPS через paramiko
main.py            — Telegram бот (polling mode)

static/js/
  main.js          — Entry point, импорты всех модулей
  catalog.js       — Каталог: карточки, пагинация, sidebar, поиск
  search.js        — Верхний поиск (dropdown с результатами)
  lists.js         — Избранное/Хотелки (❤️/⭐ toggle)
  cases.js         — Таб кейсов
  watchlist.js     — Таб watchlist
  chart.js         — TradingView графики
  router.js        — Hash-based tab router
  state.js         — Shared state
  events.js        — Event bus
  modal.js         — Модалка добавления
  alerts.js        — Activity feed
  stats.js         — Hero статистика
  utils.js         — Форматирование

static/css/styles.css  — Все стили (1095 строк)
static/sw.js           — Service Worker (PWA)
static/manifest.json   — PWA manifest

data/image_cache.json  — 15003 записей {item_name_lower: steam_cdn_image_url}

extension/             — Chrome Manifest V3 extension для lis-skins.com
```

## Инфраструктура

**VPS:** 194.87.140.204
**SSH:** root@194.87.140.204, ключ `~/.ssh/vps_key` (Ed25519)
**Remote path:** /opt/steam-sniper/
**Systemd services:**
- `steam-sniper-dashboard` — FastAPI (порт 8100)
- `steam-sniper-bot` — Telegram бот

**Деплой:**
```bash
cd tools/steam-sniper && uv run python deploy.py
```
Или ручной upload:
```python
import paramiko
from pathlib import Path
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
k = paramiko.Ed25519Key.from_private_key_file(str(Path.home() / '.ssh' / 'vps_key'))
c.connect('194.87.140.204', username='root', pkey=k, timeout=10)
sftp = c.open_sftp()
sftp.put('server.py', '/opt/steam-sniper/server.py')
sftp.close()
c.exec_command('systemctl restart steam-sniper-dashboard')
```

**Логи:** `journalctl -u steam-sniper-dashboard -n 50 --no-pager`

## Источники данных

1. **Lis-skins JSON API** (основной): `https://lis-skins.com/market_export_json/csgo.json`
   - ~24000 предметов
   - Поля: `name` (английский), `price` (USD), `url`, `count`
   - **НЕТ картинок, НЕТ русских имён**
   - Обновляется каждые 5 минут через background collector

2. **Steam Market Search API** (для русских имён + картинок при ручном поиске):
   - URL: `https://steamcommunity.com/market/search/render/?query={q}&appid=730&norender=1&count=50&l=russian`
   - Возвращает: `hash_name` (EN), `name` (RU), `icon_url` (Steam CDN)
   - Лимит: ~10 результатов на страницу

3. **ByMykel/CSGO-API** (для картинок каталога):
   - `https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/skins.json` и ещё 8 датасетов
   - Предзагружено в `data/image_cache.json` (15003 записи)
   - Имена БЕЗ wear suffix: "AK-47 | Redline" (не "AK-47 | Redline (Field-Tested)")
   - Функция `_get_item_image()` стрипает wear через `rfind(" (")` для fallback lookup

4. **ЦБ РФ** (курс USD/RUB): `https://www.cbr-xml-daily.ru/daily_json.js`
   - Lis-skins rate = CBR × 1.0314 (откалибровано 2026-04-13)

## ЗАДАЧА: Русский поиск в каталоге

### Проблема

Пользователь вводит "изумруд" в поиске каталога — должен получить те же результаты, что на lis-skins.com (44 предмета). Сейчас получает **33** (или 76, в зависимости от состояния кеша/SW).

### Контекст проблемы

На lis-skins.com все предметы имеют русские имена. Когда пользователь ищет "изумруд" на lis-skins, их поисковик матчит русские названия. 

У нас в каталоге (`/api/catalog`) все имена АНГЛИЙСКИЕ (из JSON export lis-skins). Русских имён нигде нет.

### Что было сделано (итерации)

**Итерация 1:** Поиск по-русски не работал вообще. Каталог искал только по английским именам.

**Итерация 2:** Добавлен маршрут через Steam Market API — если запрос кириллический, отправляем в Steam, получаем английские имена, фильтруем каталог. Результат: 32 из 44. Steam API возвращает максимум ~50 результатов за все страницы.

**Итерация 3:** Добавлен локальный словарь `_RU_EN_DICT` (80+ терминов). "изумруд" → "emerald", ищем локально. Результат: 76 предметов (больше чем у lis-skins). Причина: мы ищем ВСЕ предметы с "emerald" в имени, а lis-skins видимо фильтрует точнее по своим русским именам.

**Итерация 4 (текущая проблема):** Service Worker (`static/sw.js`) кеширует JS файлы по стратегии **cache-first**. Старый catalog.js без русского поиска застрял в кеше браузера. Обновили `CACHE_NAME` с `sniper-v1` на `sniper-v2`, но у пользователя всё равно старый кеш — hard refresh не помогает.

### Что нужно сделать

1. **Service Worker cache-busting** — JS файлы должны обновляться при деплое. Текущая стратегия cache-first для static файлов слишком агрессивная. Варианты:
   - Переключить static на network-first (или stale-while-revalidate)
   - Добавить version query param к JS imports (`catalog.js?v=2`)
   - Или вообще убрать SW кеширование для JS (оставить только для иконок)

2. **Русский поиск** — добиться идентичных результатов с lis-skins.com:
   - Сейчас "изумруд" даёт 76 у нас и 44 на lis-skins
   - Нужно понять, как lis-skins фильтрует (возможно, по точному русскому имени, а не по подстроке)
   - Идеальное решение: построить ПОЛНЫЙ маппинг русских имён для всех 24000 предметов
   - Источник русских имён: Steam Market API (медленно, по одному) или готовая база
   
3. **После фикса — задеплоить на VPS** и убедиться что у пользователя всё работает без ручной очистки кеша.

### Текущее состояние кода

**server.py, `/api/catalog` endpoint (строки ~561-580):**
```python
if q:
    has_cyrillic = any("\u0400" <= c <= "\u04ff" for c in q)
    if has_cyrillic:
        en_query = _translate_ru_to_en(q.lower())
        if en_query:
            words = en_query.lower().split()
            items = [it for it in items if all(w in it["name"].lower() for w in words)]
        else:
            steam_results = _steam_search(q)
            en_names = {sr["hash_name"].lower() for sr in steam_results}
            items = [it for it in items if it["name"].lower() in en_names]
    else:
        words = q.lower().split()
        items = [it for it in items if all(w in it["name"].lower() for w in words)]
```

**Словарь `_RU_EN_DICT`** — 80+ терминов, работает для основных слов. Но не покрывает все возможные русские запросы.

**Service Worker (`static/sw.js`):**
- `CACHE_NAME = 'sniper-v2'` (обновлён с v1)
- Static assets: cache-first
- HTML/API: network-first

### Ключевые файлы для изменения

- `server.py` — `/api/catalog` поиск, `_translate_ru_to_en()`, `_RU_EN_DICT`
- `static/sw.js` — стратегия кеширования  
- `static/js/catalog.js` — фронтенд каталога (сейчас ОК, проблема в кеше)
- `dashboard.html` — может понадобиться для cache-busting query params

### Как проверить

1. Открыть http://194.87.140.204:8100
2. Перейти на таб "КАТАЛОГ"
3. Ввести "изумруд" в поиске каталога
4. Должно показать ~44 предмета (как на lis-skins.com)
5. Попробовать ещё: "нож", "керамбит", "азимов", "вулкан", "градиент"

### API для тестирования

```bash
# Каталог (основной endpoint)
curl "http://194.87.140.204:8100/api/catalog?q=emerald&limit=50"
curl "http://194.87.140.204:8100/api/catalog?q=%D0%B8%D0%B7%D1%83%D0%BC%D1%80%D1%83%D0%B4&limit=50"

# Поиск (dropdown, использует Steam API для русского)  
curl "http://194.87.140.204:8100/api/search?q=%D0%B8%D0%B7%D1%83%D0%BC%D1%80%D1%83%D0%B4"

# Debug info
curl "http://194.87.140.204:8100/api/debug"
```

### Критерии успеха

1. Пользователь вводит "изумруд" → видит ~44 предмета (идентично lis-skins)
2. Русский поиск работает для любых CS2 терминов
3. Обновление дашборда не требует ручной очистки кеша (SW корректно обновляет файлы)
4. Деплой на VPS работает, сервис перезапускается без ошибок
