"""Kwork dialog auto-reply bot powered by Gemini.

Usage:
    uv run python reply_bot.py --dry-run
    uv run python reply_bot.py --once --send
    uv run python reply_bot.py --loop --send
"""
from __future__ import annotations

import argparse
import asyncio
import atexit
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

# Load .env before imports from config.
ENV_PATH = Path(__file__).parent.parent.parent / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

import httpx  # noqa: E402
from kwork import Kwork  # noqa: E402

from bot import parse_json_payload  # noqa: E402
from config import (  # noqa: E402
    DB_PATH,
    GEMINI_MODEL,
    GOOGLE_API_KEY,
    KWORK_LOGIN,
    KWORK_PASSWORD,
    KWORK_PROXY,
)

POLL_INTERVAL_SEC = 45
MAX_DIALOGS_PER_PASS = 5
MAX_HISTORY_MESSAGES = 12
MAX_REPLY_LEN = 1200
LOCK_PATH = Path(__file__).with_name("reply_bot.lock")

REPLY_PROMPT = """Ты — исполнитель на Kwork. Нужно написать короткий живой ответ клиенту в диалоге.

Правила:
- Пиши по-русски.
- 2-5 коротких предложений.
- Без воды, без канцелярита, без "буду рад сотрудничеству".
- Не выдумывай сделанную работу и кейсы.
- Если не хватает деталей, задай 1-3 конкретных вопроса.
- Если задача подходит, покажи понимание и предложи следующий шаг.
- Не используй markdown, списки и эмодзи.
- Не обещай созвон, если клиент сам не просил.

Профиль исполнителя:
- Python, Telegram-боты, парсинг, автоматизация, FastAPI, SQLite/PostgreSQL.
- AI-интеграции: Claude API, Gemini API, RAG, чат-боты с базой знаний.
- Не делает: дизайн, верстку, WordPress, 1C, Java, мобильные приложения.

Контекст диалога:
{history}

Нужно ответить на последние входящие сообщения клиента:
{incoming}

Верни JSON:
{{"reply": "текст ответа"}}
"""


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def acquire_lock() -> None:
    if LOCK_PATH.exists():
        try:
            existing_pid = int(LOCK_PATH.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            existing_pid = 0

        if existing_pid and process_alive(existing_pid):
            raise RuntimeError(f"reply_bot.py already running (pid={existing_pid})")

        LOCK_PATH.unlink(missing_ok=True)

    LOCK_PATH.write_text(str(os.getpid()), encoding="utf-8")


def release_lock() -> None:
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dialog_reply_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_message_id INTEGER NOT NULL UNIQUE,
            dialog_user_id INTEGER NOT NULL,
            dialog_username TEXT,
            incoming_text TEXT,
            reply_text TEXT,
            status TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def already_processed(conn: sqlite3.Connection, message_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM dialog_reply_log WHERE source_message_id=? AND status='sent'",
        (message_id,),
    ).fetchone()
    return row is not None


def log_reply(
    conn: sqlite3.Connection,
    *,
    message_ids: list[int],
    dialog_user_id: int,
    dialog_username: str,
    incoming_text: str,
    reply_text: str,
    status: str,
) -> None:
    now = time.time()
    conn.executemany(
        """
        INSERT INTO dialog_reply_log (
            source_message_id,
            dialog_user_id,
            dialog_username,
            incoming_text,
            reply_text,
            status,
            created_at
        )
        VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(source_message_id) DO UPDATE SET
            dialog_user_id=excluded.dialog_user_id,
            dialog_username=excluded.dialog_username,
            incoming_text=excluded.incoming_text,
            reply_text=excluded.reply_text,
            status=excluded.status,
            created_at=excluded.created_at
        """,
        [
            (
                message_id,
                dialog_user_id,
                dialog_username,
                incoming_text[:2000],
                reply_text[:2000],
                status,
                now,
            )
            for message_id in message_ids
        ],
    )
    conn.commit()


def print_status(conn: sqlite3.Connection) -> None:
    print("reply log by status:", flush=True)
    rows = conn.execute(
        "SELECT status, COUNT(*) FROM dialog_reply_log GROUP BY status ORDER BY status"
    ).fetchall()
    if not rows:
        print("  none", flush=True)
        return
    for status, count in rows:
        print(f"  {status}: {count}", flush=True)

    print("\nlatest replies:", flush=True)
    rows = conn.execute(
        """
        SELECT dialog_username, source_message_id, status, incoming_text, reply_text, created_at
        FROM dialog_reply_log
        ORDER BY id DESC
        LIMIT 10
        """
    ).fetchall()
    for username, message_id, status, incoming, reply, created_at in rows:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))
        print(f"  {ts} {username} msg={message_id} {status}", flush=True)
        print(f"    in: {incoming[:120]}", flush=True)
        print(f"    out: {reply[:120]}", flush=True)


def clean_text(text: str | None) -> str:
    return " ".join((text or "").replace("\r", " ").split()).strip()


def clip_text(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


async def generate_reply(history: str, incoming: str) -> str:
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY not set")

    prompt = REPLY_PROMPT.format(history=history, incoming=incoming)
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
            params={"key": GOOGLE_API_KEY},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.5,
                    "maxOutputTokens": 400,
                    "responseMimeType": "application/json",
                },
            },
        )
        resp.raise_for_status()

    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    payload = parse_json_payload(text)
    reply = clean_text(payload.get("reply", ""))
    if not reply:
        raise RuntimeError("Gemini returned empty reply")
    return reply[:MAX_REPLY_LEN]


def format_history(messages: list[object], client_user_id: int) -> str:
    lines: list[str] = []
    for msg in messages[-MAX_HISTORY_MESSAGES:]:
        from_id = getattr(msg, "from_id", None)
        text = clean_text(getattr(msg, "message", ""))
        if not text:
            continue
        role = "Клиент" if from_id == client_user_id else "Я"
        lines.append(f"{role}: {text}")
    return "\n".join(lines) or "История пустая."


async def process_dialog(
    api: Kwork,
    conn: sqlite3.Connection,
    *,
    user_id: int,
    username: str,
    send: bool,
) -> bool:
    messages = await api.get_dialog_with_user(username)
    incoming = [
        msg
        for msg in messages
        if (msg.message_id or 0) > 0
        and msg.from_id == user_id
        and clean_text(msg.message)
        and not already_processed(conn, int(msg.message_id))
    ]
    if not incoming:
        return False

    incoming_text = "\n".join(
        f"- {clean_text(msg.message)}" for msg in incoming if clean_text(msg.message)
    )
    history = format_history(messages, user_id)
    reply = await generate_reply(history=clip_text(history), incoming=clip_text(incoming_text))

    status = "draft"
    if send:
        await api.send_message(user_id, reply)
        status = "sent"

    log_reply(
        conn,
        message_ids=[int(msg.message_id) for msg in incoming if msg.message_id],
        dialog_user_id=user_id,
        dialog_username=username,
        incoming_text=incoming_text,
        reply_text=reply,
        status=status,
    )
    print(f">> {status} reply to {username} ({user_id})", flush=True)
    print(f"   in: {incoming_text[:180]}", flush=True)
    print(f"   out: {reply[:180]}", flush=True)
    return True


async def scan_dialogs(conn: sqlite3.Connection, *, send: bool) -> int:
    processed = 0
    async with Kwork(login=KWORK_LOGIN, password=KWORK_PASSWORD, proxy=KWORK_PROXY) as api:
        dialogs = await api.get_dialogs_page(page=1)
        for dialog in dialogs[:MAX_DIALOGS_PER_PASS]:
            user_id = dialog.user_id or 0
            username = dialog.username or ""
            unread_count = dialog.unread_count or 0
            if not user_id or not username or unread_count <= 0:
                continue

            try:
                if await process_dialog(api, conn, user_id=user_id, username=username, send=send):
                    processed += 1
            except Exception as e:
                print(f"!! dialog {username} ({user_id}): {e}", flush=True)
    return processed


async def main() -> None:
    parser = argparse.ArgumentParser(description="Kwork dialog auto-reply bot")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit")
    parser.add_argument("--loop", action="store_true", help="Run forever")
    parser.add_argument("--send", action="store_true", help="Send replies to Kwork")
    parser.add_argument("--dry-run", action="store_true", help="Generate drafts only")
    parser.add_argument("--status", action="store_true", help="Show reply log status and exit")
    args = parser.parse_args()

    if not KWORK_LOGIN or not KWORK_PASSWORD:
        print("!! Set KWORK_LOGIN and KWORK_PASSWORD in .env", flush=True)
        sys.exit(1)

    conn = init_db()
    if args.status:
        print_status(conn)
        conn.close()
        return

    send = args.send and not args.dry_run
    if not args.once and not args.loop:
        args.once = True

    print(
        f">> Reply bot started (mode={'send' if send else 'dry-run'}, interval={POLL_INTERVAL_SEC}s)",
        flush=True,
    )

    if args.once:
        count = await scan_dialogs(conn, send=send)
        print(f">> Scan done: {count} dialogs processed", flush=True)
        conn.close()
        return

    try:
        acquire_lock()
    except RuntimeError as e:
        print(f"!! {e}", flush=True)
        conn.close()
        sys.exit(1)
    atexit.register(release_lock)

    while True:
        try:
            count = await scan_dialogs(conn, send=send)
            print(f">> Loop pass done: {count} dialogs processed", flush=True)
        except Exception as e:
            print(f"!! reply loop error: {e}", flush=True)
        await asyncio.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    asyncio.run(main())
