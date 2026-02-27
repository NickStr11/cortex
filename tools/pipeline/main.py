"""Content Pipeline: DEV_CONTEXT → Article → Telegram

Usage:
    uv run python tools/pipeline/main.py
    uv run python tools/pipeline/main.py --dry-run   # print article, don't send

Requires:
    ANTHROPIC_API_KEY
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import anthropic
import httpx
from beartype import beartype

ROOT = Path(__file__).parent.parent.parent
DEV_CONTEXT = ROOT / "DEV_CONTEXT.md"

WRITING_STYLE = """Ты помогаешь писать короткие посты для Telegram-канала на основе логов разработки.

Стиль:
- Разговорный, без воды, без мотивашек
- От первого лица, как будто пишешь себе в дневник
- Матерные слова допустимы если уместны, не вставляй их специально
- Конкретика: что именно сделал, что не работало, что понял
- Незавершённые мысли — нормально

Структура (не буквально, по ощущению):
- Что было / ситуация
- Что сделал / что не сработало
- Что понял (если есть)

Длина: 150-350 слов. Не больше.

Форматирование для Telegram:
- Жирный через *текст*
- Никаких заголовков с ###
- Можно список через дефис если реально нужен

НЕ писать:
- "Таким образом...", "В заключение...", "Подводя итоги..."
- Мотивашки и "ты молодец"
- Формальный язык
- Длинные нумерованные списки"""


@beartype
def extract_last_session(dev_context: str) -> str:
    """Extract the most recent ### session from История изменений."""
    match = re.search(r"## История изменений\n(.+?)(?=\n## |\Z)", dev_context, re.DOTALL)
    if not match:
        raise ValueError("История изменений section not found in DEV_CONTEXT.md")

    history = match.group(1)
    sections = re.split(r"\n(?=### )", history)
    session_sections = [s.strip() for s in sections if s.strip().startswith("###")]

    if not session_sections:
        raise ValueError("No session entries found in История изменений")

    return session_sections[0]  # First = most recent


@beartype
def generate_article(session_log: str) -> str:
    """Generate Telegram post from session log using Claude API."""
    client = anthropic.Anthropic()

    with client.messages.stream(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=WRITING_STYLE,
        messages=[
            {
                "role": "user",
                "content": (
                    "Напиши пост для Telegram-канала на основе этого лога сессии разработки.\n\n"
                    f"{session_log}"
                ),
            }
        ],
    ) as stream:
        final = stream.get_final_message()

    return final.content[0].text  # type: ignore[union-attr]


@beartype
def send_to_telegram(text: str, token: str, chat_id: str) -> int:
    """Send message to Telegram. Returns message_id."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = httpx.post(
        url,
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=30,
    )
    response.raise_for_status()
    result: dict[str, object] = response.json()
    message = result["result"]  # type: ignore[index]
    return int(message["message_id"])  # type: ignore[index]


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    # Check env vars early
    if not dry_run:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required", file=sys.stderr)
            sys.exit(1)
    else:
        token, chat_id = "", ""

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY required", file=sys.stderr)
        sys.exit(1)

    # Read and parse
    text = DEV_CONTEXT.read_text(encoding="utf-8")
    last_session = extract_last_session(text)

    title_line = last_session.splitlines()[0]
    print(f"Session: {title_line}")

    # Generate
    print("Generating article...")
    article = generate_article(last_session)

    print(f"\n{'='*50}\n{article}\n{'='*50}\n")
    print(f"Length: {len(article)} chars")

    if dry_run:
        print("Dry run — not sending to Telegram")
        return

    # Send
    msg_id = send_to_telegram(article, token, chat_id)
    print(f"Sent to Telegram: message_id={msg_id}")


if __name__ == "__main__":
    main()
