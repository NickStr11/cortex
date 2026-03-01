"""Configuration for Telegram group monitor."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data" / "tg-groups"

# Telegram userbot (Telethon)
TG_API_ID = int(os.environ.get("TG_API_ID", "0"))
TG_API_HASH = os.environ.get("TG_API_HASH", "")
TG_SESSION_NAME = os.environ.get("TG_SESSION_NAME", "cortex_userbot")

# Telegram bot (for sending digests)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1001434709177")

# Gemini
GEMINI_MODEL = "gemini-2.0-flash"

# Digest window (hours)
DIGEST_WINDOW_HOURS = 24


@dataclass
class GroupConfig:
    """A Telegram group to monitor."""

    name: str
    # Either username (@group) or numeric ID
    identifier: str | int
    # Minimum message length to include (skip "hi", "thanks")
    min_length: int = 50
    # Keywords to boost relevance (empty = include all long enough messages)
    keywords: list[str] = field(default_factory=list)


# Groups to monitor
GROUPS: list[GroupConfig] = [
    GroupConfig(
        name="AI Mindset (Серёжа Рис)",
        identifier=-1001497220445,
        min_length=40,
        keywords=[
            "ai", "agent", "llm", "gpt", "claude", "prompt",
            "model", "api", "deploy", "tool", "mcp",
            "бизнес", "продукт", "автоматизация", "нейросеть",
        ],
    ),
    GroupConfig(
        name="Вайбкодеры",
        identifier="vibecod3rs",
        min_length=40,
        keywords=[
            "ai", "agent", "llm", "claude", "codex", "cursor",
            "vibe", "coding", "mcp", "prompt", "api", "deploy",
            "rust", "python", "typescript", "framework",
            "openclaw", "gemini", "opus", "sonnet",
        ],
    ),
]
