# TG Monitor — Telegram Group Parser + Daily Digest

Читает сообщения из Telegram-групп через Telethon userbot, генерирует дайджест через Gemini 3 Flash, отправляет в приватный канал.

## Файлы

| Файл | Что делает |
|------|-----------|
| `config.py` | Список групп, фильтры, env vars |
| `monitor.py` | Telethon — чтение сообщений из групп → JSON |
| `digest.py` | JSON → Gemini 3 Flash → дайджест → Telegram |
| `daily.py` | Объединяет heartbeat + tg-monitor в один запуск |
| `deploy/` | Systemd service + timer + setup script для VM |

## Env vars

```env
# Telethon userbot
TG_API_ID=36203046
TG_API_HASH=<from my.telegram.org>

# Gemini
GOOGLE_API_KEY=<key>

# Bot для отправки дайджеста
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_CHAT_ID=-1001434709177
```

## Использование

```bash
# 1. Скачать сообщения (первый запуск — попросит телефон + код)
uv run python tools/tg-monitor/monitor.py --limit 200

# 2. Сгенерировать и отправить дайджест
uv run python tools/tg-monitor/digest.py

# 3. Полный цикл (heartbeat + tg + send)
uv run python tools/tg-monitor/daily.py

# Dry run (без отправки)
uv run python tools/tg-monitor/daily.py --dry-run
```

## Деплой на VM

```bash
gcloud compute ssh cortex-vm --zone=europe-west3-b
bash tools/tg-monitor/deploy/setup-vm.sh
```

## Добавление групп

Отредактируй `GROUPS` в `config.py`:

```python
GROUPS = [
    GroupConfig(
        name="AI Mindset",
        identifier="aimindset_chat",  # @username или числовой ID
        min_length=40,
        keywords=["ai", "agent", ...],
    ),
    GroupConfig(
        name="Another Group",
        identifier=-100123456789,  # числовой ID
    ),
]
```
