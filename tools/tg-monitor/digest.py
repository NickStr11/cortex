"""Telegram Group Digest — generate and send daily digest.

Usage:
    uv run python tools/tg-monitor/digest.py                   # generate + send
    uv run python tools/tg-monitor/digest.py --dry-run         # print only
    uv run python tools/tg-monitor/digest.py --hours 48        # last 48h

Requires env:
    GOOGLE_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""
from __future__ import annotations

import io
import json
import os
import sys
from datetime import datetime, timezone, timedelta

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx
from beartype import beartype
from google import genai

from config import (
    DATA_DIR,
    DIGEST_WINDOW_HOURS,
    GEMINI_MODEL,
    GROUPS,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)

DIGEST_PROMPT = """Глубокий аналитический дайджест Telegram-группы по AI/tech.

Задача: концентрация профита — выжми максимум пользы.

Структура:
1. *Горячие темы* — что обсуждали, ключевые позиции участников
2. *Инструменты* — что упоминается, что хвалят/ругают, советы по использованию
3. *Ссылки и ресурсы* — каждый URL с описанием что это и зачем
4. *Кейсы* — кто что делает, результаты, грабли
5. *Выводы* — тренды, практические советы

Правила:
- 500-1500 слов
- Конкретика: имена, инструменты, числа
- Не пропускай ссылки — каждая важна
- Следи за ветками обсуждений
- Репосты отмечай отдельно
- Формат для Telegram: *жирный*, списки через дефис
- Русский, технические термины на английском
- Пропусти болтовню, приветствия, оффтоп
- Не пиши "В заключение...", "Подводя итоги..."
- Если ничего интересного — так и скажи

Формат:
*Дайджест [название группы] — [дата]*

[Структурированный отчёт]
"""


@beartype
def load_recent_messages(hours: int) -> dict[str, list[dict[str, object]]]:
    """Load messages from all groups within the time window."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result: dict[str, list[dict[str, object]]] = {}

    for group in GROUPS:
        safe_name = group.name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        path = DATA_DIR / f"{safe_name}.json"
        if not path.exists():
            print(f"  No data for {group.name} ({path})")
            continue

        all_msgs: list[dict[str, object]] = json.loads(path.read_text(encoding="utf-8"))
        recent = []
        for msg in all_msgs:
            date_str = str(msg.get("date", ""))
            if not date_str:
                continue
            try:
                msg_date = datetime.fromisoformat(date_str)
                if msg_date.tzinfo is None:
                    msg_date = msg_date.replace(tzinfo=timezone.utc)
                if msg_date >= cutoff:
                    recent.append(msg)
            except ValueError:
                continue

        if recent:
            result[group.name] = recent
            print(f"  {group.name}: {len(recent)} messages in last {hours}h")
        else:
            print(f"  {group.name}: no messages in last {hours}h")

    return result


@beartype
def format_messages_for_llm(group_name: str, messages: list[dict[str, object]]) -> str:
    """Format messages as text for LLM input."""
    lines: list[str] = [f"Группа: {group_name}", f"Сообщений: {len(messages)}", ""]

    # Sort chronologically
    messages.sort(key=lambda m: str(m.get("date", "")))

    for msg in messages:
        sender = msg.get("sender_name", "Unknown")
        text = str(msg.get("text", ""))
        date = str(msg.get("date", ""))[:16]  # Trim to minute
        reply = msg.get("reply_to")
        prefix = f"[reply to #{reply}] " if reply else ""
        lines.append(f"[{date}] {sender}: {prefix}{text}")
        lines.append("")

    return "\n".join(lines)


@beartype
def generate_digest(group_name: str, messages_text: str) -> str:
    """Generate digest via Gemini."""
    client = genai.Client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"{DIGEST_PROMPT}\n\n{messages_text}",
    )
    return response.text  # type: ignore[return-value]


@beartype
def send_file_to_telegram(filepath: Path, caption: str, token: str, chat_id: str) -> int:
    """Send file to Telegram. Returns message_id."""
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with open(filepath, "rb") as f:
        response = httpx.post(
            url,
            data={"chat_id": chat_id, "caption": caption},
            files={"document": (filepath.name, f)},
            timeout=30,
        )
    response.raise_for_status()
    result: dict[str, object] = response.json()
    message = result["result"]  # type: ignore[index]
    return int(message["message_id"])  # type: ignore[index]


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="TG Group Digest")
    parser.add_argument("--dry-run", action="store_true", help="Print only, don't send")
    parser.add_argument("--hours", type=int, default=DIGEST_WINDOW_HOURS, help="Time window in hours")
    args = parser.parse_args()

    if not os.environ.get("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY required", file=sys.stderr)
        sys.exit(1)

    token = TELEGRAM_BOT_TOKEN
    chat_id = TELEGRAM_CHAT_ID
    if not args.dry_run and (not token or not chat_id):
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required", file=sys.stderr)
        sys.exit(1)

    print(f"Loading messages from last {args.hours}h...")
    groups_messages = load_recent_messages(args.hours)

    if not groups_messages:
        print("No recent messages found. Run monitor.py first.")
        sys.exit(0)

    for group_name, messages in groups_messages.items():
        print(f"\nGenerating digest for {group_name} ({len(messages)} messages)...")
        messages_text = format_messages_for_llm(group_name, messages)
        digest = generate_digest(group_name, messages_text)

        print(f"\n{'='*50}\n{digest}\n{'='*50}")
        print(f"Length: {len(digest)} chars")

        if args.dry_run:
            print("Dry run — not sending")
            continue

        # Save as .md and send as file
        safe_name = group_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        md_path = DATA_DIR / f"{safe_name}_digest_{date_str}.md"
        md_path.write_text(digest, encoding="utf-8")
        print(f"Saved: {md_path}")

        caption = f"Дайджест {group_name} — {date_str}"
        msg_id = send_file_to_telegram(md_path, caption, token, chat_id)
        print(f"Sent to Telegram: message_id={msg_id}")


if __name__ == "__main__":
    main()
