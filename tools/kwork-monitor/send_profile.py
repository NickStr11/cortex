"""Send Kwork profile text to Telegram."""
import httpx
import asyncio
import os
import sys
from pathlib import Path

# Load .env
ENV_PATH = Path(__file__).parent.parent.parent / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = "691773226"

MSG1 = """ПРОФИЛЬ KWORK -- копипасти куда нужно

== О СЕБЕ (описание профиля) ==

Python-разработчик. Делаю ботов, парсеры и AI-интеграции, которые реально работают в продакшне.

Что делаю:
- Telegram-боты (aiogram): от простых до сложных с БД, платежами, интеграциями
- Парсинг и скрейпинг (Scrapy, Playwright): сбор данных с любых сайтов, обход защит
- AI-интеграции: чат-боты с базой знаний (RAG), Claude API, Gemini API, GPT
- Автоматизация бизнес-процессов: CRM, синхронизация баз, уведомления
- Backend: FastAPI, PostgreSQL, SQLite

Примеры реализованных проектов:
[ok] Система автоматизации аптеки -- сканирование товаров, синхронизация с учетной системой, уведомления в Telegram
[ok] AI-дайджест Telegram-каналов -- MapReduce пайплайн, автоанализ 1000+ сообщений
[ok] Мониторинг фриланс-площадок -- автопоиск проектов + AI-оценка релевантности

Работаю быстро, на связи в Telegram. Перед началом -- четкое ТЗ и сроки."""

MSG2 = """== СПЕЦИАЛИЗАЦИЯ (теги) ==

Python, Telegram-боты, парсинг, AI, автоматизация, FastAPI, Claude API, Gemini, скрейпинг, интеграции

== ИДЕИ ДЛЯ КВОРКОВ (3 штуки) ==

1. "Telegram-бот под ключ на Python"
Цена: от 5,000 руб
Описание: Разработаю Telegram-бота любой сложности на aiogram. Меню, кнопки, база данных, платежи, интеграции с внешними API. Чистый код, документация, деплой на сервер.

2. "Парсинг данных с любого сайта"
Цена: от 3,000 руб
Описание: Соберу данные с любого сайта: каталоги, цены, контакты, отзывы. Scrapy для больших объемов, Playwright для JS-сайтов. Результат в CSV/Excel/JSON/БД. Обход защит, регулярное обновление.

3. "AI чат-бот с базой знаний для бизнеса"
Цена: от 10,000 руб
Описание: Чат-бот который отвечает на вопросы клиентов на основе ваших документов, FAQ, базы знаний. RAG-подход (Claude/GPT/Gemini). Telegram или веб-виджет. Бот учится на ваших данных и не выдумывает."""


async def main():
    async with httpx.AsyncClient(timeout=15) as client:
        for text in [MSG1, MSG2]:
            r = await client.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True},
            )
            data = r.json()
            if data.get("ok"):
                print(f"Sent ({len(text)} chars)")
            else:
                print(f"Error: {data}")


if __name__ == "__main__":
    asyncio.run(main())
