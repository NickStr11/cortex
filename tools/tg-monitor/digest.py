"""Telegram Group Digest — MapReduce pipeline.

Pipeline: Enrich → MAP (parallel chunks) → REDUCE → VERIFY
Adapted from sereja.tech/blog/digest-subagents-mapreduce

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
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

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

# Fast model for MAP/VERIFY (cheap), Pro for REDUCE (quality)
GEMINI_MODEL_FAST = "gemini-2.0-flash"

CHUNK_SIZE = 15  # messages per MAP chunk

MAP_PROMPT = """Извлеки ОДНУ главную тему из этого кластера сообщений Telegram-группы.

Правила:
- Конкретика: имена участников, инструменты, числа, ссылки
- Если есть URL — обязательно включи с описанием
- Не додумывай — только то что явно написано
- 100-300 слов
- Русский, технические термины на английском

Формат:
**Тема: [название]**
[Описание с деталями]
"""

REDUCE_PROMPT = """Собери дайджест Telegram-группы из извлечённых тем.

Структура:
1. *Горячие темы* — что обсуждали, ключевые позиции участников
2. *Инструменты* — что упоминается, что хвалят/ругают
3. *Ссылки и ресурсы* — каждый URL с описанием
4. *Кейсы* — кто что делает, результаты
5. *Выводы* — тренды, практические советы

Правила:
- 500-1500 слов
- Конкретика: имена, инструменты, числа
- Не пропускай ссылки
- Формат для Telegram: *жирный*, списки через дефис
- Русский, технические термины на английском
- Пропусти болтовню, оффтоп
- Не пиши "В заключение...", "Подводя итоги..."
- Если ничего интересного — так и скажи

Формат:
*Дайджест {group_name} — {date}*

[Структурированный отчёт]
"""

VERIFY_PROMPT = """Проверь дайджест на фактическую точность.

Сверь КАЖДОЕ утверждение дайджеста с исходными сообщениями.

Для каждого факта:
- CONFIRMED — есть прямое подтверждение в сообщениях
- UNVERIFIED — нет источника, но возможно
- HALLUCINATION — противоречит сообщениям или выдумано

Формат:
ФАКТ: [утверждение]
СТАТУС: [CONFIRMED/UNVERIFIED/HALLUCINATION]
ИСТОЧНИК: [цитата из сообщения или "не найден"]

В конце: итого X confirmed, Y unverified, Z hallucinations.
Если есть HALLUCINATION — предложи исправление.
"""


# --- Enrichment ---

@beartype
def enrich_messages(messages: list[dict[str, object]]) -> list[dict[str, object]]:
    """Add engagement scores and resolve reply_to context."""
    msg_index: dict[int, dict[str, object]] = {}
    for msg in messages:
        msg_index[int(msg["message_id"])] = msg  # type: ignore[arg-type]

    # Count replies per message
    reply_counts: dict[int, int] = {}
    thread_sizes: dict[int, int] = {}
    for msg in messages:
        reply_to = msg.get("reply_to")
        if reply_to is not None:
            rid = int(reply_to)  # type: ignore[arg-type]
            reply_counts[rid] = reply_counts.get(rid, 0) + 1
            # Thread = root message
            thread_sizes[rid] = thread_sizes.get(rid, 0) + 1

    enriched: list[dict[str, object]] = []
    for msg in messages:
        mid = int(msg["message_id"])  # type: ignore[arg-type]
        replies = reply_counts.get(mid, 0)
        thread = thread_sizes.get(mid, 0)
        score = replies * 2.0 + thread * 0.5

        enriched_msg = dict(msg)
        enriched_msg["engagement_score"] = score

        # Resolve reply_to text
        reply_to = msg.get("reply_to")
        if reply_to is not None:
            parent = msg_index.get(int(reply_to))  # type: ignore[arg-type]
            if parent:
                enriched_msg["reply_to_text"] = parent.get("text", "")
                enriched_msg["reply_to_sender"] = parent.get("sender_name", "")

        enriched.append(enriched_msg)

    return enriched


@beartype
def filter_top_messages(messages: list[dict[str, object]], top_n: int = 100) -> list[dict[str, object]]:
    """Filter top messages by engagement score (min 2.0), keep chronological order."""
    scored = [m for m in messages if float(m.get("engagement_score", 0)) >= 2.0]  # type: ignore[arg-type]
    scored.sort(key=lambda m: float(m.get("engagement_score", 0)), reverse=True)  # type: ignore[arg-type]
    top = scored[:top_n]
    # Restore chronological order
    top.sort(key=lambda m: str(m.get("date", "")))
    return top


# --- Format ---

@beartype
def format_chunk(messages: list[dict[str, object]]) -> str:
    """Format a chunk of messages for LLM."""
    lines: list[str] = []
    for msg in messages:
        sender = msg.get("sender_name", "Unknown")
        text = str(msg.get("text", ""))
        date = str(msg.get("date", ""))[:16]

        reply_ctx = ""
        reply_text = msg.get("reply_to_text")
        reply_sender = msg.get("reply_to_sender")
        if reply_text:
            short = str(reply_text)[:100]
            reply_ctx = f" [ответ на {reply_sender}: {short}]"

        lines.append(f"[{date}] {sender}:{reply_ctx} {text}")
    return "\n".join(lines)


# --- Gemini calls ---

@beartype
def call_gemini(prompt: str, content: str, model: str | None = None) -> str:
    """Single Gemini API call."""
    client = genai.Client()
    response = client.models.generate_content(
        model=model or GEMINI_MODEL,
        contents=f"{prompt}\n\n{content}",
    )
    return response.text or ""


# --- Pipeline ---

@beartype
def pipeline_map(chunks: list[list[dict[str, object]]]) -> list[str]:
    """MAP: extract one topic per chunk (fast model)."""
    topics: list[str] = []
    for i, chunk in enumerate(chunks):
        formatted = format_chunk(chunk)
        print(f"    MAP [{i+1}/{len(chunks)}] ({len(chunk)} msgs)...")
        topic = call_gemini(MAP_PROMPT, formatted, model=GEMINI_MODEL_FAST)
        topics.append(topic)
    return topics


@beartype
def pipeline_reduce(group_name: str, topics: list[str]) -> str:
    """REDUCE: assemble topics into final digest (pro model)."""
    date_str = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    prompt = REDUCE_PROMPT.format(group_name=group_name, date=date_str)
    combined = "\n\n---\n\n".join(f"Тема {i+1}:\n{t}" for i, t in enumerate(topics))
    print(f"    REDUCE ({len(topics)} topics → digest)...")
    return call_gemini(prompt, combined)


@beartype
def pipeline_verify(digest: str, messages: list[dict[str, object]]) -> str:
    """VERIFY: fact-check digest against source messages (fast model)."""
    source = format_chunk(messages[:50])  # top-50 for context window
    content = f"ДАЙДЖЕСТ:\n{digest}\n\nИСХОДНЫЕ СООБЩЕНИЯ:\n{source}"
    print("    VERIFY (fact-check)...")
    return call_gemini(VERIFY_PROMPT, content, model=GEMINI_MODEL_FAST)


# --- Load ---

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


# --- Send ---

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


# --- Main ---

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="TG Group Digest (MapReduce)")
    parser.add_argument("--dry-run", action="store_true", help="Print only, don't send")
    parser.add_argument("--hours", type=int, default=DIGEST_WINDOW_HOURS, help="Time window in hours")
    parser.add_argument("--no-verify", action="store_true", help="Skip verification step")
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
        print(f"\n{'='*50}")
        print(f"Pipeline for {group_name} ({len(messages)} messages)")
        print(f"{'='*50}")

        # 1. Enrich
        print("  ENRICH: engagement scores + reply_to context...")
        enriched = enrich_messages(messages)

        # 2. Filter
        top = filter_top_messages(enriched)
        if len(top) < 5:
            # Not enough engaging messages, use all (sorted by date)
            top = sorted(enriched, key=lambda m: str(m.get("date", "")))
        print(f"  FILTER: {len(messages)} → {len(top)} messages (score >= 2.0)")

        # 3. MAP: split into chunks
        n_chunks = max(1, math.ceil(len(top) / CHUNK_SIZE))
        chunks = [top[i * CHUNK_SIZE:(i + 1) * CHUNK_SIZE] for i in range(n_chunks)]
        print(f"  MAP: {n_chunks} chunks × ~{CHUNK_SIZE} messages")
        topics = pipeline_map(chunks)

        # 4. REDUCE
        digest = pipeline_reduce(group_name, topics)
        print(f"\n{digest}\n")
        print(f"Length: {len(digest)} chars")

        # 5. VERIFY
        if not args.no_verify:
            verify_result = pipeline_verify(digest, top)
            print(f"\nVERIFY:\n{verify_result}")

            if "HALLUCINATION" in verify_result.upper():
                print("\n  WARNING: hallucinations detected, check verify output above")

        if args.dry_run:
            print("Dry run — not sending")
            continue

        # Save and send
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
