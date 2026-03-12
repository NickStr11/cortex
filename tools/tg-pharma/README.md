# tg-pharma

Приватный Telegram-бот для PharmOrder.

Что умеет сейчас:
- текст и голос
- conversational reply через Gemini Flash 3
- понять, какой товар обычно имеется в виду
- сказать, что чаще покупали в прошлом месяце и у какого поставщика
- подготовить смену остатка только через `preview -> confirm -> apply`
- использовать лёгкий `bot_refs.db` как identity/alias layer поверх живых VPS `sklit_cache.db` и `order_history.db`

Примеры:
- `поставь остаток азитромицина 5 штук`
- `какой у нас азитромицин?`
- `какой азитромицин мы чаще покупали в прошлом месяце и у какого поставщика?`

Запуск:
```powershell
cd D:\code\2026\2\cortex\tools\tg-pharma
uv sync
uv run python main.py
```

Сборка лёгкой reference БД из копии SKLIT:
```powershell
cd D:\code\2026\2\cortex\tools\tg-pharma
uv run python build_refs.py --sklit-root C:\Users\User\Desktop\SKLIT
```

Нужные env:
- `PHARMA_TELEGRAM_BOT_TOKEN`
- `PHARMA_ALLOWED_CHAT_IDS`
- `PHARMORDER_API_BASE`
- `PHARMORDER_API_KEY`
- `GOOGLE_API_KEY`
- `PHARMA_GEMINI_MODEL`
- `PHARMORDER_SSH_HOST`
- `PHARMORDER_SSH_USER`
- `PHARMORDER_SSH_PASSWORD`
- `PHARMORDER_REMOTE_ORDER_HISTORY_DB`
- `PHARMA_REFS_DB`
- `PHARMA_ANALYTICS_DB` (опциональный legacy fallback)

Заметки:
- если используешь тот же token, что у `tools/tg-bridge`, не держи оба long-poller одновременно
- `audit.jsonl` хранит write-операции по остаткам
- история закупок идёт по SSH с VPS из `order_history.db`
- `bot_refs.db` нужен только для identity/alias layer, а не для хранения всей аналитики
