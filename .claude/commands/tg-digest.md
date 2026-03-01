Глубокий дайджест Telegram-группы через Gemini. $ARGUMENTS — ссылка на группу или username.

## Инструкции

1. Загрузи env из `D:/code/2026/2/cortex/.env` (через dotenv или export)

2. Забери последние 1500 сообщений из группы через Telethon:
   - Используй session: `data/tg-groups/cortex_userbot`
   - Креды: TG_API_ID и TG_API_HASH из .env
   - Извлеки: текст, URLs, forwards, replies, reactions, sender name, message id, date

3. Подготовь данные для LLM:
   - Формат: `[date] #id sender: [REPOST from X] [reply to #Y] text | URLs: url1, url2 [reactions:N]`
   - Сохрани в temp файл

4. Отправь в Gemini (НЕ анализируй сам — экономия токенов Claude):
   ```python
   from google import genai
   import os
   # GOOGLE_API_KEY из .env
   client = genai.Client()
   response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt + messages)
   ```

5. Промпт для Gemini:
   ```
   Глубокий аналитический дайджест Telegram-группы.

   Структура:
   1. ГОРЯЧИЕ ТЕМЫ И ДИСКУССИИ — что обсуждали, позиции участников, консенсус
   2. ИНСТРУМЕНТЫ И ТЕХНОЛОГИИ — что упоминается, что хвалят/ругают, советы
   3. ССЫЛКИ И РЕСУРСЫ — каждый URL: что это, зачем. Репосты отдельно
   4. КЕЙСЫ И ПРОЕКТЫ — кто что делает, результаты, грабли
   5. ИНСАЙТЫ И ВЫВОДЫ — тренды, практические советы, что попробовать

   Правила:
   - Русский, технические термины на английском
   - Конкретика > абстракция. Имена, числа, инструменты
   - Не пропускай ссылки
   - Следи за ветками (reply_to) и репостами
   - Markdown, 2000-4000 слов
   ```

6. Результат:
   - Сохрани в `data/tg-groups/{group_name}_digest.md`
   - Отправь .md файлом в Telegram канал (TELEGRAM_CHAT_ID из .env)
   - Покажи краткое саммари пользователю

## Параметры

- Без аргументов: покажи список доступных групп из `tools/tg-monitor/config.py`
- С аргументом: `@username` или `https://t.me/groupname` или просто `groupname`
- Доп. флаги в аргументах: `--limit 500` (по умолчанию 1500), `--no-send` (не отправлять в канал)
