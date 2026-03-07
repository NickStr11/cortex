"""
Kwork Monitor — freelance project scanner with AI evaluation.

Fetches new projects from Kwork → filters by keywords →
evaluates with Gemini → sends to Telegram.

Usage:
    uv run python main.py              # single run
    uv run python main.py --loop       # poll every 15 min
    uv run python main.py --dry-run    # print, don't send to TG
"""
from __future__ import annotations

import os
import argparse
import asyncio
import json
import sqlite3
import sys
import time
from pathlib import Path

# ── Load .env BEFORE importing config ──
ENV_PATH = Path(__file__).parent.parent.parent / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

import httpx  # noqa: E402

from config import (  # noqa: E402
    DB_PATH,
    GEMINI_MODEL,
    GOOGLE_API_KEY,
    CATEGORIES,
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


# ══════════════════════════════════════════════
# Database (dedup)
# ══════════════════════════════════════════════

def init_db() -> sqlite3.Connection:
    """Create seen-projects DB if needed."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            project_id INTEGER PRIMARY KEY,
            title TEXT,
            seen_at REAL
        )
    """)
    conn.commit()
    return conn


def is_seen(conn: sqlite3.Connection, project_id: int) -> bool:
    row = conn.execute("SELECT 1 FROM seen WHERE project_id = ?", (project_id,)).fetchone()
    return row is not None


def mark_seen(conn: sqlite3.Connection, project_id: int, title: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO seen (project_id, title, seen_at) VALUES (?, ?, ?)",
        (project_id, title, time.time()),
    )
    conn.commit()


# ══════════════════════════════════════════════
# Kwork API
# ══════════════════════════════════════════════

async def fetch_projects() -> list[dict]:
    """Fetch projects from Kwork using pykwork."""
    from kwork import Kwork

    login = KWORK_LOGIN
    password = KWORK_PASSWORD

    if not login or not password:
        print("!! KWORK_LOGIN / KWORK_PASSWORD not set in .env", flush=True)
        sys.exit(1)

    all_projects: list[dict] = []
    seen_ids: set[int] = set()

    async with Kwork(login=login, password=password) as api:
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
                print(f"!! Error fetching category {cat_id}: {e}", flush=True)

    print(f"<< Fetched {len(all_projects)} projects from {len(CATEGORIES)} categories", flush=True)
    return all_projects


# ══════════════════════════════════════════════
# Filters
# ══════════════════════════════════════════════

def filter_projects(projects: list[dict], conn: sqlite3.Connection) -> list[ProjectMatch]:
    """Apply keyword/stop-word filters and dedup."""
    matches: list[ProjectMatch] = []

    for p in projects:
        pid = p["id"]
        if not pid or is_seen(conn, pid):
            continue

        text = f"{p['title']} {p['description']}".lower()

        # Stop words check
        if any(sw in text for sw in STOP_WORDS):
            continue

        # Keyword match
        matched = [kw for kw in KEYWORDS if kw.lower() in text]
        if not matched:
            continue

        matches.append(ProjectMatch(
            kwork_id=pid,
            title=p["title"],
            description=p["description"][:1000],  # trim
            price_from=p["price_from"],
            price_to=p["price_to"],
            url=p["url"],
            matched_keywords=matched[:5],
        ))

    print(f">> Filtered: {len(matches)} matches from {len(projects)} total", flush=True)
    return matches


# ══════════════════════════════════════════════
# AI Evaluation (Gemini Flash)
# ══════════════════════════════════════════════

async def evaluate_project(project: ProjectMatch) -> ProjectMatch:
    """Score project and draft a response using Gemini."""
    api_key = GOOGLE_API_KEY
    if not api_key:
        project.ai_score = 5
        project.ai_summary = "API key not set"
        project.ai_response = ""
        return project

    prompt = f"""Ты — строгий AI-фильтр для фрилансера. Оцени проект с биржи Kwork.

ПРОЕКТ:
Название: {project.title}
Описание: {project.description}
Бюджет: {project.price_from}-{project.price_to} руб

ПРОФИЛЬ ФРИЛАНСЕРА (только это умеет):
- Python-разработчик (НЕ frontend, НЕ верстальщик, НЕ дизайнер)
- Telegram боты (aiogram), парсинг (scrapy, playwright), автоматизация
- AI интеграции (Claude API, Gemini API, RAG, чат-боты с базой знаний)
- Backend: FastAPI, SQLite, PostgreSQL
- НЕ делает: верстку, WordPress, 1С, PHP, Java, мобильные приложения, дизайн, SEO

КРИТЕРИИ ОЦЕНКИ (будь СТРОГИМ):
- 9-10: идеально подходит (Python бот/парсинг/AI, бюджет >= 5000)
- 7-8: хорошо подходит (можно сделать за 1-3 дня)
- 5-6: частично подходит (нужно изучить что-то новое)
- 3-4: слабо подходит (не совпадает стек или слишком дешёво)
- 1-2: не подходит (frontend, дизайн, другой язык)

Если проект НЕ про Python/боты/парсинг/AI — ставь 1-3, даже если "вроде можно".

ЗАДАЧА:
1. Оцени score (1-10) — будь строгим!
2. Резюме (1-2 предложения)
3. Черновик отклика (3-4 предложения): конкретно, без воды, покажи экспертизу. Если score < 5, отклик не нужен.

JSON: {{"score": 5, "summary": "...", "response": "..."}}"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
                params={"key": api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 500,
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
        print(f"!! AI eval error for {project.kwork_id}: {e}", flush=True)
        project.ai_score = 5
        project.ai_summary = "Ошибка оценки"

    return project


# ══════════════════════════════════════════════
# Telegram
# ══════════════════════════════════════════════

def format_message(p: ProjectMatch) -> str:
    """Format project for Telegram."""
    score_emoji = "🔥" if p.ai_score >= 8 else "✅" if p.ai_score >= 6 else "⚡" if p.ai_score >= 4 else "⬜"
    price = f"{p.price_from:,}".replace(",", " ")
    if p.price_to and p.price_to != p.price_from:
        price += f" – {p.price_to:,}".replace(",", " ")
    price += " ₽"

    msg = f"""{score_emoji} <b>Score: {p.ai_score}/10</b> | {price}

<b>{p.title}</b>

{p.ai_summary}

<b>Черновик отклика:</b>
<i>{p.ai_response}</i>

🔗 <a href="{p.url}">Открыть на Kwork</a>
🏷 {', '.join(p.matched_keywords[:3])}"""
    return msg


def format_digest(matches: list[ProjectMatch]) -> str:
    """Format a summary digest of all new projects."""
    lines = [f"📋 <b>Kwork: {len(matches)} новых проектов</b>\n"]
    for i, p in enumerate(matches, 1):
        score_emoji = "🔥" if p.ai_score >= 8 else "✅" if p.ai_score >= 6 else "⚡"
        price = f"{p.price_from:,}".replace(",", " ") + " ₽"
        lines.append(f"{i}. {score_emoji} [{p.ai_score}] {p.title[:60]} — {price}")
    return "\n".join(lines)


async def send_telegram(text: str) -> None:
    """Send message via Telegram bot."""
    token = TELEGRAM_BOT_TOKEN
    chat_id = TELEGRAM_CHAT_ID
    if not token:
        print("!! TELEGRAM_BOT_TOKEN not set", flush=True)
        return

    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )


# ══════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════

async def run_once(dry_run: bool = False) -> int:
    """Single scan cycle. Returns number of new matches."""
    conn = init_db()

    # 1. Fetch
    projects = await fetch_projects()

    # 2. Filter
    matches = filter_projects(projects, conn)

    if not matches:
        print("-- No new matching projects", flush=True)
        conn.close()
        return 0

    # 3. AI evaluate (parallel, max 5 concurrent)
    sem = asyncio.Semaphore(5)

    async def eval_with_sem(p: ProjectMatch) -> ProjectMatch:
        async with sem:
            return await evaluate_project(p)

    evaluated = await asyncio.gather(*[eval_with_sem(m) for m in matches])

    # Sort by score descending
    evaluated.sort(key=lambda p: p.ai_score, reverse=True)

    # 4. Send top matches (score >= 6)
    sent = 0
    for p in evaluated:
        if p.ai_score < 6:
            continue

        msg = format_message(p)
        if dry_run:
            print(f"\n{'='*50}")
            print(msg.replace("<b>", "").replace("</b>", "")
                  .replace("<i>", "").replace("</i>", "")
                  .replace("<a href=\"", "").replace("\">", " "))
        else:
            await send_telegram(msg)
            await asyncio.sleep(1)  # rate limit

        mark_seen(conn, p.kwork_id, p.title)
        sent += 1

    # Mark low-score as seen too (don't re-evaluate)
    for p in evaluated:
        if p.ai_score < 6:
            mark_seen(conn, p.kwork_id, p.title)

    print(f">> Sent {sent} projects to Telegram", flush=True)
    conn.close()
    return sent


async def main() -> None:
    parser = argparse.ArgumentParser(description="Kwork project monitor")
    parser.add_argument("--loop", action="store_true", help="Poll continuously")
    parser.add_argument("--dry-run", action="store_true", help="Print instead of sending to TG")
    args = parser.parse_args()

    if args.loop:
        print(f">> Starting Kwork monitor (polling every {POLL_INTERVAL_MIN} min)", flush=True)
        while True:
            try:
                await run_once(dry_run=args.dry_run)
            except Exception as e:
                print(f"!! Error in scan cycle: {e}", flush=True)
            print(f"-- Sleeping {POLL_INTERVAL_MIN} min...", flush=True)
            await asyncio.sleep(POLL_INTERVAL_MIN * 60)
    else:
        await run_once(dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
