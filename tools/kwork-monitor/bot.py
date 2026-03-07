"""Kwork Auto-Outreach Bot.

Scans Kwork projects → AI drafts proposals → sends to Telegram for approval →
submits offer via pykwork on approve.

Usage:
    uv run python bot.py          # start bot
    uv run python bot.py --once   # single scan, no polling
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

# ── Load .env ──
ENV_PATH = Path(__file__).parent.parent.parent / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

import httpx  # noqa: E402
from kwork import Kwork  # noqa: E402

from config import (  # noqa: E402
    CATEGORIES,
    DB_PATH,
    GEMINI_MODEL,
    GOOGLE_API_KEY,
    KEYWORDS,
    KWORK_LOGIN,
    KWORK_PASSWORD,
    POLL_INTERVAL_MIN,
    PRICE_MAX,
    PRICE_MIN,
    STOP_WORDS,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    ProjectMatch,
)

# ── Constants ──
SCAN_INTERVAL = POLL_INTERVAL_MIN * 60  # seconds
TG_POLL_INTERVAL = 2  # seconds between getUpdates
MIN_SCORE = 6  # minimum AI score to propose

# ── Kwork offer defaults ──
DEFAULT_DURATION = 5  # days
OFFER_TITLE = "<div>Индивидуальное предложение</div>"


# ══════════════════════════════════════════════
# Database
# ══════════════════════════════════════════════

def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            project_id INTEGER PRIMARY KEY,
            title TEXT,
            seen_at REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending (
            project_id INTEGER PRIMARY KEY,
            title TEXT,
            description TEXT,
            price INTEGER,
            url TEXT,
            proposal TEXT,
            duration INTEGER DEFAULT 5,
            tg_message_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at REAL
        )
    """)
    conn.commit()
    return conn


def is_seen(conn: sqlite3.Connection, pid: int) -> bool:
    return conn.execute("SELECT 1 FROM seen WHERE project_id=?", (pid,)).fetchone() is not None


def mark_seen(conn: sqlite3.Connection, pid: int, title: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO seen (project_id, title, seen_at) VALUES (?,?,?)",
        (pid, title, time.time()),
    )
    conn.commit()


def save_pending(
    conn: sqlite3.Connection,
    project: ProjectMatch,
    proposal: str,
    tg_msg_id: int,
) -> None:
    # Use project's max price (or min if no max) — stay within buyer's budget
    offer_price = project.price_to if project.price_to else project.price_from
    conn.execute(
        """INSERT OR REPLACE INTO pending
           (project_id, title, description, price, url, proposal, duration, tg_message_id, status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            project.kwork_id, project.title, project.description,
            offer_price, project.url, proposal,
            DEFAULT_DURATION, tg_msg_id, "pending", time.time(),
        ),
    )
    conn.commit()


def get_pending(conn: sqlite3.Connection, project_id: int) -> dict | None:
    row = conn.execute(
        "SELECT project_id, title, price, url, proposal, duration FROM pending WHERE project_id=? AND status='pending'",
        (project_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "project_id": row[0], "title": row[1], "price": row[2],
        "url": row[3], "proposal": row[4], "duration": row[5],
    }


def update_pending_status(conn: sqlite3.Connection, project_id: int, status: str) -> None:
    conn.execute("UPDATE pending SET status=? WHERE project_id=?", (status, project_id))
    conn.commit()


# ══════════════════════════════════════════════
# Kwork API
# ══════════════════════════════════════════════

async def fetch_projects() -> list[dict]:
    all_projects: list[dict] = []
    seen_ids: set[int] = set()

    async with Kwork(login=KWORK_LOGIN, password=KWORK_PASSWORD) as api:
        for cat_id in CATEGORIES:
            try:
                projects = await api.get_projects(
                    categories_ids=[cat_id],
                    price_from=PRICE_MIN,
                    price_to=PRICE_MAX,
                    page=1,
                )
                for p in projects:
                    pid = p.id or 0
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)
                    price = p.price or 0
                    max_price = p.possible_price_limit or price
                    all_projects.append({
                        "id": pid,
                        "title": p.title or "",
                        "description": p.description or "",
                        "price_from": price,
                        "price_to": max_price if p.allow_higher_price else price,
                        "url": f"https://kwork.ru/projects/{pid}/view",
                        "offers": p.offers or 0,
                        "username": p.username or "",
                    })
            except Exception as e:
                print(f"!! Fetch cat {cat_id}: {e}", flush=True)

    print(f"<< {len(all_projects)} projects from {len(CATEGORIES)} categories", flush=True)
    return all_projects


async def submit_offer(project_id: int, proposal: str, price: int, duration: int) -> dict:
    """Submit offer to Kwork project via pykwork web client."""
    async with Kwork(login=KWORK_LOGIN, password=KWORK_PASSWORD) as api:
        # Web client needs explicit login to get csrf cookies
        await api.web.login_via_mobile_web_auth_token(url_to_redirect="/")
        result = await api.web.submit_exchange_offer(
            project_id=project_id,
            offer_type="custom",
            description=proposal,
            kwork_duration=duration,
            kwork_price=price,
            kwork_name=OFFER_TITLE,
            raise_on_error=False,
        )
    # Check for API-level errors
    json_data = result.get("json") or {}
    if json_data.get("success") is False:
        error_msg = json_data.get("message") or json_data.get("error") or "Unknown error"
        raise RuntimeError(error_msg)
    return result


# ══════════════════════════════════════════════
# Filters
# ══════════════════════════════════════════════

def filter_projects(projects: list[dict], conn: sqlite3.Connection) -> list[ProjectMatch]:
    matches: list[ProjectMatch] = []
    for p in projects:
        pid = p["id"]
        if not pid or is_seen(conn, pid):
            continue
        text = f"{p['title']} {p['description']}".lower()
        if any(sw in text for sw in STOP_WORDS):
            continue
        matched = [kw for kw in KEYWORDS if kw.lower() in text]
        if not matched:
            continue
        matches.append(ProjectMatch(
            kwork_id=pid,
            title=p["title"],
            description=p["description"][:1000],
            price_from=p["price_from"],
            price_to=p["price_to"],
            url=p["url"],
            matched_keywords=matched[:5],
        ))
    print(f">> {len(matches)} matches", flush=True)
    return matches


# ══════════════════════════════════════════════
# AI (Gemini)
# ══════════════════════════════════════════════

EVAL_PROMPT = """Ты — AI-помощник фрилансера на Kwork. Оцени проект и напиши отклик.

ПРОЕКТ:
Название: {title}
Описание: {description}
Бюджет: {price_from}-{price_to} руб

ПРОФИЛЬ ФРИЛАНСЕРА:
- Python: Telegram боты, парсинг, автоматизация, API интеграции
- AI: Claude API, Gemini API, RAG, чат-боты с базой знаний
- Backend: FastAPI, SQLite, PostgreSQL
- НЕ делает: верстку, WordPress, 1С, PHP, Java, мобилки, дизайн

ОЦЕНКА (строго):
- 9-10: идеально (Python бот/парсинг/AI, бюджет >= 5000)
- 7-8: хорошо подходит
- 5-6: частично подходит
- 1-4: не подходит

ОТКЛИК (если score >= 6):
Напиши от первого лица, 3-5 предложений. Без воды и штампов.
Покажи что понял задачу, упомяни конкретный опыт, предложи решение.
Тон: профессиональный но живой. НЕ начинай с "Здравствуйте".
НЕ используй шаблонные фразы типа "готов обсудить детали".

JSON: {{"score": N, "summary": "1 предложение", "response": "текст отклика"}}"""


async def evaluate_project(project: ProjectMatch) -> ProjectMatch:
    api_key = GOOGLE_API_KEY
    if not api_key:
        project.ai_score = 5
        project.ai_summary = "API key not set"
        return project

    prompt = EVAL_PROMPT.format(
        title=project.title,
        description=project.description,
        price_from=project.price_from,
        price_to=project.price_to,
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
                params={"key": api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 600,
                        "responseMimeType": "application/json",
                    },
                },
            )
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            result = json.loads(text)
            project.ai_score = result.get("score", 5)
            project.ai_summary = result.get("summary", "")
            project.ai_response = result.get("response", "")
    except Exception as e:
        print(f"!! AI eval {project.kwork_id}: {e}", flush=True)
        project.ai_score = 5
        project.ai_summary = "Ошибка оценки"

    return project


# ══════════════════════════════════════════════
# Telegram Bot
# ══════════════════════════════════════════════

async def tg_request(method: str, http_timeout: float = 15, **kwargs) -> dict:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    async with httpx.AsyncClient(timeout=http_timeout) as client:
        resp = await client.post(url, json=kwargs)
        return resp.json()


async def send_project_card(project: ProjectMatch) -> int | None:
    """Send project card with inline keyboard. Returns message_id."""
    score_emoji = "🔥" if project.ai_score >= 8 else "✅" if project.ai_score >= 6 else "⚡"
    price = f"{project.price_from:,}".replace(",", " ")
    if project.price_to and project.price_to != project.price_from:
        price += f" – {project.price_to:,}".replace(",", " ")
    price += " ₽"

    msg = f"""{score_emoji} <b>Score: {project.ai_score}/10</b> | {price}

<b>{project.title}</b>

{project.ai_summary}

<b>Отклик:</b>
<i>{project.ai_response}</i>

🔗 <a href="{project.url}">Открыть на Kwork</a>
🏷 {', '.join(project.matched_keywords[:3])}"""

    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Отправить", "callback_data": f"send:{project.kwork_id}"},
            {"text": "⏭ Пропустить", "callback_data": f"skip:{project.kwork_id}"},
        ]]
    }

    result = await tg_request(
        "sendMessage",
        chat_id=TELEGRAM_CHAT_ID,
        text=msg,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=keyboard,
    )

    if result.get("ok"):
        return result["result"]["message_id"]
    print(f"!! TG send error: {result}", flush=True)
    return None


async def answer_callback(callback_id: str, text: str) -> None:
    await tg_request("answerCallbackQuery", callback_query_id=callback_id, text=text)


async def edit_message_buttons(message_id: int, text_suffix: str) -> None:
    """Remove inline keyboard and append status to message."""
    await tg_request(
        "editMessageReplyMarkup",
        chat_id=TELEGRAM_CHAT_ID,
        message_id=message_id,
        reply_markup={"inline_keyboard": []},
    )


# ══════════════════════════════════════════════
# Scan cycle
# ══════════════════════════════════════════════

async def scan_and_propose(conn: sqlite3.Connection) -> int:
    """Fetch → filter → evaluate → send proposals to TG. Returns count."""
    projects = await fetch_projects()
    matches = filter_projects(projects, conn)

    if not matches:
        return 0

    # AI evaluate (parallel, max 5)
    sem = asyncio.Semaphore(5)

    async def eval_sem(p: ProjectMatch) -> ProjectMatch:
        async with sem:
            return await evaluate_project(p)

    evaluated = await asyncio.gather(*[eval_sem(m) for m in matches])
    evaluated.sort(key=lambda p: p.ai_score, reverse=True)

    sent = 0
    for p in evaluated:
        mark_seen(conn, p.kwork_id, p.title)
        if p.ai_score < MIN_SCORE or not p.ai_response:
            continue

        msg_id = await send_project_card(p)
        if msg_id:
            save_pending(conn, p, p.ai_response, msg_id)
            sent += 1
            await asyncio.sleep(1)

    print(f">> {sent} proposals sent to TG", flush=True)
    return sent


# ══════════════════════════════════════════════
# Callback handler
# ══════════════════════════════════════════════

async def handle_callback(conn: sqlite3.Connection, callback: dict) -> None:
    """Handle inline button press."""
    cb_id = callback.get("id", "")
    data = callback.get("data", "")
    msg_id = callback.get("message", {}).get("message_id")

    print(f"<< Callback: {data} (msg={msg_id})", flush=True)

    if ":" not in data:
        await answer_callback(cb_id, "❌ Неизвестная команда")
        return

    action, pid_str = data.split(":", 1)
    try:
        project_id = int(pid_str)
    except ValueError:
        await answer_callback(cb_id, "❌ Ошибка")
        return

    if action == "skip":
        update_pending_status(conn, project_id, "skipped")
        try:
            await answer_callback(cb_id, "⏭ Пропущено")
        except Exception:
            pass  # callback may have expired
        if msg_id:
            await edit_message_buttons(msg_id, "")
            await tg_request(
                "sendMessage",
                chat_id=TELEGRAM_CHAT_ID,
                text=f"⏭ Пропущено #{project_id}",
                reply_to_message_id=msg_id,
            )
        print(f">> Skipped project {project_id}", flush=True)
        return

    if action == "send":
        pending = get_pending(conn, project_id)
        if not pending:
            try:
                await answer_callback(cb_id, "❌ Уже отправлено или не найдено")
            except Exception:
                pass
            return

        try:
            await answer_callback(cb_id, "⏳ Отправляю отклик...")
        except Exception:
            pass  # callback may have expired, but still submit

        try:
            result = await submit_offer(
                project_id=pending["project_id"],
                proposal=pending["proposal"],
                price=pending["price"],
                duration=pending["duration"],
            )
            update_pending_status(conn, project_id, "sent")
            if msg_id:
                await edit_message_buttons(msg_id, "")
            await tg_request(
                "sendMessage",
                chat_id=TELEGRAM_CHAT_ID,
                text=f"✅ Отклик отправлен на проект #{project_id}",
                reply_to_message_id=msg_id,
            )
            print(f">> Offer submitted for project {project_id}", flush=True)
        except Exception as e:
            update_pending_status(conn, project_id, "error")
            error_msg = str(e)[:200]
            await tg_request(
                "sendMessage",
                chat_id=TELEGRAM_CHAT_ID,
                text=f"❌ Ошибка отправки #{project_id}:\n<code>{error_msg}</code>",
                parse_mode="HTML",
                reply_to_message_id=msg_id,
            )
            print(f"!! Submit error {project_id}: {e}", flush=True)


# ══════════════════════════════════════════════
# Main loop
# ══════════════════════════════════════════════

async def poll_telegram(conn: sqlite3.Connection) -> None:
    """Long-poll Telegram for callback queries."""
    offset = 0
    while True:
        try:
            result = await tg_request(
                "getUpdates",
                http_timeout=45,
                offset=offset,
                timeout=30,
                allowed_updates=["callback_query"],
            )
            updates = result.get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                if "callback_query" in update:
                    await handle_callback(conn, update["callback_query"])
        except Exception as e:
            print(f"!! TG poll error: {e}", flush=True)
            await asyncio.sleep(5)

        await asyncio.sleep(TG_POLL_INTERVAL)


async def periodic_scan(conn: sqlite3.Connection) -> None:
    """Run scan every SCAN_INTERVAL seconds."""
    while True:
        try:
            count = await scan_and_propose(conn)
            if count:
                print(f">> Scan done: {count} new proposals", flush=True)
            else:
                print("-- Scan done: nothing new", flush=True)
        except Exception as e:
            print(f"!! Scan error: {e}", flush=True)

        await asyncio.sleep(SCAN_INTERVAL)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Kwork outreach bot")
    parser.add_argument("--once", action="store_true", help="Single scan, no TG polling")
    args = parser.parse_args()

    if not KWORK_LOGIN or not KWORK_PASSWORD:
        print("!! Set KWORK_LOGIN and KWORK_PASSWORD in .env", flush=True)
        sys.exit(1)
    if not TELEGRAM_BOT_TOKEN:
        print("!! Set TELEGRAM_BOT_TOKEN in .env", flush=True)
        sys.exit(1)

    conn = init_db()

    if args.once:
        await scan_and_propose(conn)
        conn.close()
        return

    print(f">> Kwork Bot started (scan every {POLL_INTERVAL_MIN} min)", flush=True)
    await tg_request(
        "sendMessage",
        chat_id=TELEGRAM_CHAT_ID,
        text="🤖 Kwork Bot запущен. Сканирую проекты...",
    )

    # Run TG polling + periodic scans concurrently
    await asyncio.gather(
        poll_telegram(conn),
        periodic_scan(conn),
    )


if __name__ == "__main__":
    asyncio.run(main())
