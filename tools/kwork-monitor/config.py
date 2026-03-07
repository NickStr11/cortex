"""Kwork Monitor configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ── Paths ──
ROOT = Path(__file__).parent
DB_PATH = ROOT / "seen.db"

# ── Kwork credentials (from .env) ──
KWORK_LOGIN = os.environ.get("KWORK_LOGIN", "")
KWORK_PASSWORD = os.environ.get("KWORK_PASSWORD", "")

# ── Telegram ──
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_OWNER_CHAT_ID", "691773226")

# ── Gemini ──
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"  # cheap & fast for evaluation

# ── Polling ──
POLL_INTERVAL_MIN = 15  # minutes between checks

# ── Kwork category IDs ──
# 11 = Программирование, 41 = Скрипты и боты, 79 = Парсинг данных
# Full list: https://kwork.ru/categories/programming
CATEGORIES = [11, 41, 79]

# ── Price filter ──
PRICE_MIN = 3000    # ignore below 3K (демпинг)
PRICE_MAX = 300000  # ignore above 300K (enterprise)

# ── Keywords (lowercase). Project must contain at least one. ──
KEYWORDS = [
    # Боты
    "telegram", "телеграм", "тг бот", "tg бот", "бот",
    "чат-бот", "чатбот", "chatbot",
    # Парсинг
    "парсинг", "парсер", "скрейпинг", "scraping", "parser",
    "сбор данных", "выгрузка",
    # Автоматизация
    "автоматизация", "автоматизировать", "скрипт",
    "интеграция", "api",
    # AI
    "нейросет", "ai", "gpt", "chatgpt", "ии",
    "искусственный интеллект", "llm",
    # Python
    "python", "питон", "django", "fastapi", "flask",
    # Специфичное
    "crm", "1с", "1c", "bitrix", "битрикс",
    "n8n", "make.com", "zapier",
    "excel", "google sheets",
]

# ── Стоп-слова (пропускаем если есть) ──
STOP_WORDS = [
    "ios", "swift", "kotlin", "android", "flutter",
    "unity", "unreal", "c#", "java ",
    "wordpress", "joomla",
    "верстка", "figma", "tilda", "тильда",
    "pixijs", "pixi.js", "three.js", "react native",
    "vue.js", "angular", "nest.js", "nestjs",
    "photoshop", "illustrator", "corel",
    "seo", "ссылк", "индексац",
]


@dataclass
class ProjectMatch:
    """A filtered project ready for AI evaluation."""
    kwork_id: int
    title: str
    description: str
    price_from: int
    price_to: int
    url: str
    category: str = ""
    matched_keywords: list[str] = field(default_factory=list)
    ai_score: int = 0        # 1-10
    ai_summary: str = ""
    ai_response: str = ""
