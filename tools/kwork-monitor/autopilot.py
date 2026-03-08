"""Unified Kwork autopilot: auto-offers, auto-replies, Telegram escalations.

Usage:
    uv run python autopilot.py --dry-run --once
    uv run python autopilot.py --status
    uv run python autopilot.py
"""
from __future__ import annotations

import argparse
import asyncio
import atexit
import html
import os
import random
import sqlite3
import sys
import time
from pathlib import Path

from bot import (
    DEFAULT_DURATION,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    ProjectMatch,
    edit_message_buttons,
    evaluate_project,
    fetch_projects,
    filter_projects,
    get_pending,
    init_db as init_offer_db,
    log_offer_attempt,
    mark_seen,
    submit_offer,
    summarize_submit_result,
    tg_request,
    update_pending_status,
)
from config import KWORK_LOGIN, KWORK_PASSWORD, KWORK_PROXY
from kwork import Kwork
from reply_bot import clip_text, clean_text, format_history, generate_reply, log_reply


class SafeStream:
    def __init__(self, stream: object) -> None:
        self._stream = stream
        self.encoding = getattr(stream, "encoding", "utf-8")

    def write(self, data: str) -> int:
        try:
            return self._stream.write(data)
        except OSError:
            return 0

    def flush(self) -> None:
        try:
            self._stream.flush()
        except OSError:
            return

    def isatty(self) -> bool:
        try:
            return bool(self._stream.isatty())
        except OSError:
            return False


def ensure_background_stdio() -> None:
    sink = open(os.devnull, "w", encoding="utf-8")
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None) or sink
        setattr(sys, name, SafeStream(stream))


ensure_background_stdio()

AUTO_OFFER_SCORE = 8
MANUAL_REVIEW_SCORE = 6
OFFER_LOOP_INTERVAL_SEC = 300
REPLY_LOOP_INTERVAL_SEC = 45
MAX_DIALOGS_PER_PASS = 5
MAX_OFFER_ACTIONS_PER_PASS = 2
DEFAULT_PENDING_DRAIN_LIMIT = 2
LOCK_PATH = Path(__file__).with_name("autopilot.lock")
AUTH_BLOCK_COOLDOWN_SEC = 1800
HUMAN_OFFER_DELAY_RANGE_SEC = (18, 55)
HUMAN_REPLY_DELAY_RANGE_SEC = (40, 180)
LOOP_JITTER_RANGE_SEC = (-15, 45)
AUTO_OFFERS_DAILY_MIN = int(os.environ.get("KWORK_AUTO_OFFERS_DAILY_MIN", "10"))
AUTO_OFFERS_DAILY_MAX = int(os.environ.get("KWORK_AUTO_OFFERS_DAILY_MAX", "15"))
TELEGRAM_NOTIFY_ONLY_REPLIES = os.environ.get(
    "KWORK_TG_NOTIFY_ONLY_REPLIES",
    "1",
).strip().lower() not in {"0", "false", "no"}

loop_state = {
    "auth_block_until": 0.0,
    "last_auth_block_notify_at": 0.0,
}

REPLY_ESCALATE_KEYWORDS = [
    "цена",
    "стоимость",
    "бюджет",
    "срок",
    "дедлайн",
    "договор",
    "созвон",
    "звонок",
    "предоплат",
    "оплат",
    "скидк",
    "гарант",
    "доступ",
    "тз",
    "техзад",
    "техническ",
    "паспорт",
    "карта",
    "счёт",
    "договоримся",
]


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        import os

        os.kill(pid, 0)
    except PermissionError:
        return True
    except (OSError, SystemError):
        return False
    return True


def acquire_lock() -> None:
    if LOCK_PATH.exists():
        try:
            existing_pid = int(LOCK_PATH.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            existing_pid = 0

        if existing_pid and process_alive(existing_pid):
            raise RuntimeError(f"autopilot.py already running (pid={existing_pid})")
        LOCK_PATH.unlink(missing_ok=True)

    LOCK_PATH.write_text(str(__import__("os").getpid()), encoding="utf-8")


def release_lock() -> None:
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def ensure_tables(conn: sqlite3.Connection) -> None:
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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS autopilot_offer_log (
            project_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            score INTEGER NOT NULL,
            price INTEGER NOT NULL,
            url TEXT NOT NULL,
            proposal TEXT,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            detail TEXT,
            created_at REAL NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS autopilot_daily_limits (
            day_key TEXT PRIMARY KEY,
            target_count INTEGER NOT NULL,
            limit_reached INTEGER NOT NULL DEFAULT 0,
            limit_detail TEXT,
            updated_at REAL NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS offer_analytics (
            project_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            buyer_username TEXT,
            budget_from INTEGER NOT NULL,
            budget_to INTEGER NOT NULL,
            offer_price INTEGER NOT NULL,
            ai_score INTEGER NOT NULL,
            competition_offers INTEGER NOT NULL DEFAULT 0,
            matched_keywords TEXT,
            proposal_len INTEGER NOT NULL DEFAULT 0,
            mode TEXT NOT NULL,
            sent_at REAL,
            first_reply_at REAL,
            reply_count INTEGER NOT NULL DEFAULT 0,
            dialog_user_id INTEGER,
            dialog_username TEXT,
            last_reply_text TEXT,
            updated_at REAL NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS offer_reply_events (
            source_message_id INTEGER PRIMARY KEY,
            project_id INTEGER,
            dialog_user_id INTEGER NOT NULL,
            dialog_username TEXT,
            incoming_text TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        """
    )
    conn.commit()


def log_autopilot_offer(
    conn: sqlite3.Connection,
    *,
    project: ProjectMatch,
    price: int,
    mode: str,
    status: str,
    detail: str,
) -> None:
    conn.execute(
        """
        INSERT INTO autopilot_offer_log (
            project_id,
            title,
            score,
            price,
            url,
            proposal,
            mode,
            status,
            detail,
            created_at
        )
        VALUES (?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(project_id) DO UPDATE SET
            title=excluded.title,
            score=excluded.score,
            price=excluded.price,
            url=excluded.url,
            proposal=excluded.proposal,
            mode=excluded.mode,
            status=excluded.status,
            detail=excluded.detail,
            created_at=excluded.created_at
        """,
        (
            project.kwork_id,
            project.title,
            project.ai_score,
            price,
            project.url,
            project.ai_response[:4000],
            mode,
            status,
            detail[:2000],
            time.time(),
        ),
    )
    conn.commit()


def current_day_key(ts: float | None = None) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(ts or time.time()))


def day_bounds(day_key: str) -> tuple[float, float]:
    start_ts = time.mktime(time.strptime(day_key, "%Y-%m-%d"))
    return start_ts, start_ts + 86400


def get_or_create_daily_limit(conn: sqlite3.Connection) -> tuple[str, int, bool, str]:
    day_key = current_day_key()
    row = conn.execute(
        """
        SELECT target_count, limit_reached, COALESCE(limit_detail, '')
        FROM autopilot_daily_limits
        WHERE day_key=?
        """,
        (day_key,),
    ).fetchone()
    if row is not None:
        return day_key, int(row[0]), bool(row[1]), str(row[2] or "")

    target = random.randint(
        min(AUTO_OFFERS_DAILY_MIN, AUTO_OFFERS_DAILY_MAX),
        max(AUTO_OFFERS_DAILY_MIN, AUTO_OFFERS_DAILY_MAX),
    )
    target = max(target, count_sent_offers_for_day(conn, day_key=day_key))
    conn.execute(
        """
        INSERT INTO autopilot_daily_limits (
            day_key,
            target_count,
            limit_reached,
            limit_detail,
            updated_at
        )
        VALUES (?,?,?,?,?)
        """,
        (day_key, target, 0, "", time.time()),
    )
    conn.commit()
    return day_key, target, False, ""


def count_sent_offers_for_day(conn: sqlite3.Connection, *, day_key: str | None = None) -> int:
    effective_day = day_key or current_day_key()
    start_ts, end_ts = day_bounds(effective_day)
    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM offer_attempts
        WHERE outcome='sent'
          AND created_at >= ?
          AND created_at < ?
        """,
        (start_ts, end_ts),
    ).fetchone()
    return int(row[0] or 0)


def get_daily_offer_state(conn: sqlite3.Connection) -> dict[str, object]:
    day_key, target_count, limit_reached, limit_detail = get_or_create_daily_limit(conn)
    sent_count = count_sent_offers_for_day(conn, day_key=day_key)
    if sent_count > target_count:
        target_count = sent_count
        conn.execute(
            """
            UPDATE autopilot_daily_limits
            SET target_count=?, updated_at=?
            WHERE day_key=?
            """,
            (target_count, time.time(), day_key),
        )
        conn.commit()
    remaining = max(target_count - sent_count, 0)
    return {
        "day_key": day_key,
        "target_count": target_count,
        "sent_count": sent_count,
        "remaining": remaining,
        "limit_reached": limit_reached,
        "limit_detail": limit_detail,
    }


def mark_daily_limit_reached(conn: sqlite3.Connection, detail: str) -> None:
    day_key, target_count, _, _ = get_or_create_daily_limit(conn)
    conn.execute(
        """
        INSERT INTO autopilot_daily_limits (
            day_key,
            target_count,
            limit_reached,
            limit_detail,
            updated_at
        )
        VALUES (?,?,?,?,?)
        ON CONFLICT(day_key) DO UPDATE SET
            target_count=excluded.target_count,
            limit_reached=1,
            limit_detail=excluded.limit_detail,
            updated_at=excluded.updated_at
        """,
        (day_key, target_count, 1, detail[:500], time.time()),
    )
    conn.commit()


def daily_offer_budget_exhausted(conn: sqlite3.Connection) -> tuple[bool, str]:
    state = get_daily_offer_state(conn)
    if bool(state["limit_reached"]):
        detail = str(state["limit_detail"] or "Kwork offer limit reached")
        return True, detail
    if int(state["remaining"]) <= 0:
        return True, (
            f"daily target reached: {state['sent_count']}/{state['target_count']} "
            f"for {state['day_key']}"
        )
    return False, ""


def is_offer_limit_error(error: Exception | str) -> bool:
    text = str(error).lower()
    limit_markers = [
        "лимит",
        "limit",
        "quota",
        "too many",
        "maximum number",
        "максимальн",
        "превыш",
        "исчерпа",
        "не можете отправить больше",
        "слишком много отклик",
        "количество отклик",
    ]
    return any(marker in text for marker in limit_markers)


def log_offer_analytics(
    conn: sqlite3.Connection,
    *,
    project: ProjectMatch,
    offer_price: int,
    mode: str,
) -> None:
    conn.execute(
        """
        INSERT INTO offer_analytics (
            project_id,
            title,
            buyer_username,
            budget_from,
            budget_to,
            offer_price,
            ai_score,
            competition_offers,
            matched_keywords,
            proposal_len,
            mode,
            sent_at,
            updated_at
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(project_id) DO UPDATE SET
            title=excluded.title,
            buyer_username=excluded.buyer_username,
            budget_from=excluded.budget_from,
            budget_to=excluded.budget_to,
            offer_price=excluded.offer_price,
            ai_score=excluded.ai_score,
            competition_offers=excluded.competition_offers,
            matched_keywords=excluded.matched_keywords,
            proposal_len=excluded.proposal_len,
            mode=excluded.mode,
            sent_at=excluded.sent_at,
            updated_at=excluded.updated_at
        """,
        (
            project.kwork_id,
            project.title,
            project.buyer_username[:255],
            project.price_from,
            project.price_to,
            offer_price,
            project.ai_score,
            project.offers_count,
            ",".join(project.matched_keywords[:10]),
            len(project.ai_response or ""),
            mode,
            time.time(),
            time.time(),
        ),
    )
    conn.commit()


def attach_reply_to_offer_analytics(
    conn: sqlite3.Connection,
    *,
    message_ids: list[int],
    user_id: int,
    username: str,
    incoming_text: str,
) -> None:
    if not username:
        return

    row = conn.execute(
        """
        SELECT project_id, reply_count
        FROM offer_analytics
        WHERE buyer_username=?
          AND sent_at IS NOT NULL
        ORDER BY sent_at DESC
        LIMIT 1
        """,
        (username,),
    ).fetchone()
    if row is None:
        return

    project_id = int(row[0])
    now = time.time()
    conn.executemany(
        """
        INSERT OR IGNORE INTO offer_reply_events (
            source_message_id,
            project_id,
            dialog_user_id,
            dialog_username,
            incoming_text,
            created_at
        )
        VALUES (?,?,?,?,?,?)
        """,
        [
            (
                message_id,
                project_id,
                user_id,
                username[:255],
                incoming_text[:2000],
                now,
            )
            for message_id in message_ids
        ],
    )
    conn.execute(
        """
        UPDATE offer_analytics
        SET
            first_reply_at=COALESCE(first_reply_at, ?),
            reply_count=reply_count + ?,
            dialog_user_id=?,
            dialog_username=?,
            last_reply_text=?,
            updated_at=?
        WHERE project_id=?
        """,
        (
            now,
            len(message_ids),
            user_id,
            username[:255],
            incoming_text[:2000],
            now,
            project_id,
        ),
    )
    conn.commit()


def backfill_offer_analytics(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT
            attempts.project_id,
            MIN(attempts.created_at) AS sent_at,
            COALESCE(pending.title, '') AS title,
            COALESCE(pending.price, 0) AS price,
            COALESCE(pending.proposal, '') AS proposal,
            COALESCE(autolog.score, 0) AS score,
            COALESCE(autolog.mode, 'legacy') AS mode
        FROM offer_attempts AS attempts
        LEFT JOIN pending ON pending.project_id = attempts.project_id
        LEFT JOIN autopilot_offer_log AS autolog ON autolog.project_id = attempts.project_id
        LEFT JOIN offer_analytics AS analytics ON analytics.project_id = attempts.project_id
        WHERE attempts.outcome='sent'
          AND analytics.project_id IS NULL
        GROUP BY
            attempts.project_id,
            pending.title,
            pending.price,
            pending.proposal,
            autolog.score,
            autolog.mode
        """
    ).fetchall()
    if not rows:
        return

    now = time.time()
    conn.executemany(
        """
        INSERT INTO offer_analytics (
            project_id,
            title,
            buyer_username,
            budget_from,
            budget_to,
            offer_price,
            ai_score,
            competition_offers,
            matched_keywords,
            proposal_len,
            mode,
            sent_at,
            updated_at
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            (
                int(project_id),
                (title or f"project #{project_id}")[:500],
                "",
                int(price or 0),
                int(price or 0),
                int(price or 0),
                int(score or 0),
                0,
                "",
                len(proposal or ""),
                mode or "legacy",
                float(sent_at or now),
                now,
            )
            for project_id, sent_at, title, price, proposal, score, mode in rows
        ],
    )
    conn.commit()


def reply_already_done(conn: sqlite3.Connection, message_id: int) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM dialog_reply_log
        WHERE source_message_id=?
          AND status IN ('sent', 'escalated')
        """,
        (message_id,),
    ).fetchone()
    return row is not None


def reply_needs_manual_review(messages: list[object], incoming_text: str) -> bool:
    text = incoming_text.lower()
    if any(keyword in text for keyword in REPLY_ESCALATE_KEYWORDS):
        return True

    if len(incoming_text) > 500:
        return True

    for msg in messages:
        if getattr(msg, "files", None) or getattr(msg, "quote", None):
            return True
        if getattr(msg, "custom_request", None) or getattr(msg, "inbox_order", None):
            return True

    return False


def is_signin_proxy_block(error: Exception | str) -> bool:
    text = str(error)
    return "HTTP 403 for POST /signIn" in text and "ipAdress" in text


def in_auth_block_cooldown() -> bool:
    return time.time() < float(loop_state["auth_block_until"])


def start_auth_block_cooldown() -> bool:
    now = time.time()
    loop_state["auth_block_until"] = now + AUTH_BLOCK_COOLDOWN_SEC
    should_notify = now - float(loop_state["last_auth_block_notify_at"]) >= AUTH_BLOCK_COOLDOWN_SEC
    if should_notify:
        loop_state["last_auth_block_notify_at"] = now
    return should_notify


async def notify_tg(text: str, *, parse_mode: str = "HTML") -> None:
    if TELEGRAM_NOTIFY_ONLY_REPLIES:
        print("-- TG notify suppressed (non-reply event)", flush=True)
        return
    if not TELEGRAM_BOT_TOKEN:
        print(f"-- TG notify skipped: {text}", flush=True)
        return
    try:
        await tg_request(
            "sendMessage",
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )
    except Exception as e:
        print(f"!! TG notify failed: {e}", flush=True)


async def human_pause(kind: str, *, enabled: bool) -> None:
    if not enabled:
        return

    if kind == "offer":
        low, high = HUMAN_OFFER_DELAY_RANGE_SEC
    else:
        low, high = HUMAN_REPLY_DELAY_RANGE_SEC

    delay = random.randint(low, high)
    print(f"-- human pause before {kind}: {delay}s", flush=True)
    await asyncio.sleep(delay)


async def notify_reply_event(text: str, *, parse_mode: str = "HTML") -> None:
    if not TELEGRAM_BOT_TOKEN:
        print(f"-- TG reply notify skipped: {text}", flush=True)
        return
    try:
        await tg_request(
            "sendMessage",
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )
    except Exception as e:
        print(f"!! TG reply notify failed: {e}", flush=True)


def format_reply_notification(
    *,
    username: str,
    user_id: int,
    incoming_text: str,
    note: str,
) -> str:
    return (
        f"📩 <b>Новый ответ на отклик</b> @{html.escape(username)} ({user_id})\n"
        f"<code>{html.escape(clip_text(incoming_text, 700))}</code>\n"
        f"{note}"
    )


def next_loop_sleep(base: int) -> int:
    low, high = LOOP_JITTER_RANGE_SEC
    return max(15, base + random.randint(low, high))


async def process_offer_candidate(
    conn: sqlite3.Connection,
    project: ProjectMatch,
    *,
    dry_run: bool,
) -> str:
    price = project.price_to if project.price_to else project.price_from

    if project.ai_score < MANUAL_REVIEW_SCORE or not project.ai_response:
        mark_seen(conn, project.kwork_id, project.title)
        log_autopilot_offer(
            conn,
            project=project,
            price=price,
            mode="skip",
            status="ignored",
            detail="score below review threshold or empty AI response",
        )
        return "ignored"

    if project.ai_score >= AUTO_OFFER_SCORE:
        if dry_run:
            mark_seen(conn, project.kwork_id, project.title)
            log_autopilot_offer(
                conn,
                project=project,
                price=price,
                mode="auto",
                status="dry_run",
                detail="would auto-submit",
            )
            print(f"-- DRY RUN auto-offer #{project.kwork_id}", flush=True)
            return "dry_run"

        try:
            await human_pause("offer", enabled=True)
            result = await submit_offer(
                project_id=project.kwork_id,
                proposal=project.ai_response,
                price=price,
                duration=DEFAULT_DURATION,
            )
            mark_seen(conn, project.kwork_id, project.title)
            log_offer_attempt(
                conn,
                project.kwork_id,
                "sent",
                summarize_submit_result(result),
                response_status=result.get("status"),
                response_url=result.get("url"),
            )
            log_autopilot_offer(
                conn,
                project=project,
                price=price,
                mode="auto",
                status="submitted",
                detail=summarize_submit_result(result),
            )
            log_offer_analytics(
                conn,
                project=project,
                offer_price=price,
                mode="auto",
            )
            print(f">> Auto-offer submitted #{project.kwork_id}", flush=True)
            return "submitted"
        except Exception as e:
            error_msg = str(e)[:200]
            log_offer_attempt(conn, project.kwork_id, "error", error_msg)
            log_autopilot_offer(
                conn,
                project=project,
                price=price,
                mode="auto",
                status="error",
                detail=error_msg,
            )
            if is_offer_limit_error(e):
                mark_daily_limit_reached(conn, error_msg)
                print(f"!! Daily Kwork offer limit reached: {error_msg}", flush=True)
                return "limit_reached"
            return "error"

    mark_seen(conn, project.kwork_id, project.title)
    log_autopilot_offer(
        conn,
        project=project,
        price=price,
        mode="manual",
        status="suppressed",
        detail="manual review candidate suppressed because Telegram is reply-only",
    )
    print(f">> Suppressed manual-review offer #{project.kwork_id}", flush=True)
    return "suppressed"


def list_pending_rows(conn: sqlite3.Connection, *, limit: int | None = None) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    sql = """
        SELECT project_id, title, price, url, proposal, duration, tg_message_id, status, created_at
        FROM pending
        WHERE status IN ('pending', 'error')
        ORDER BY created_at DESC
    """
    params: tuple[object, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (limit,)
    return list(conn.execute(sql, params).fetchall())


async def submit_existing_pending(
    conn: sqlite3.Connection,
    *,
    limit: int | None,
    dry_run: bool,
) -> int:
    effective_limit = limit if limit is not None else DEFAULT_PENDING_DRAIN_LIMIT
    rows = list_pending_rows(conn, limit=effective_limit)
    submitted = 0
    for row in rows:
        if not dry_run:
            budget_hit, budget_detail = daily_offer_budget_exhausted(conn)
            if budget_hit:
                print(f"-- pending drain stopped: {budget_detail}", flush=True)
                break

        project_id = int(row["project_id"])
        pending = get_pending(conn, project_id)
        if not pending:
            continue

        if dry_run:
            print(f"-- DRY RUN pending #{project_id} {row['title']}", flush=True)
            submitted += 1
            continue

        try:
            await human_pause("offer", enabled=True)
            result = await submit_offer(
                project_id=pending["project_id"],
                proposal=pending["proposal"],
                price=pending["price"],
                duration=pending["duration"],
            )
            update_pending_status(conn, project_id, "sent")
            log_offer_attempt(
                conn,
                project_id,
                "sent",
                summarize_submit_result(result),
                response_status=result.get("status"),
                response_url=result.get("url"),
            )
            tg_message_id = row["tg_message_id"]
            if tg_message_id:
                try:
                    await edit_message_buttons(int(tg_message_id), "")
                except Exception:
                    pass
            print(f">> Submitted existing pending #{project_id}", flush=True)
            submitted += 1
            await asyncio.sleep(1)
        except Exception as e:
            error_msg = str(e)[:200]
            update_pending_status(conn, project_id, "error")
            log_offer_attempt(conn, project_id, "error", error_msg)
            print(f"!! Existing pending #{project_id}: {error_msg}", flush=True)
            if is_offer_limit_error(e):
                mark_daily_limit_reached(conn, error_msg)
                print("-- pending drain stopped after daily limit response", flush=True)
                break
            await notify_tg(
                (
                    f"❌ <b>Ошибка отправки pending</b> #{project_id}\n"
                    f"<b>{html.escape(str(row['title']))}</b>\n"
                    f"<code>{html.escape(error_msg)}</code>"
                ),
            )
    return submitted


async def offer_pass(conn: sqlite3.Connection, *, dry_run: bool) -> int:
    if not dry_run:
        budget_hit, budget_detail = daily_offer_budget_exhausted(conn)
        if budget_hit:
            print(f"-- offer pass skipped: {budget_detail}", flush=True)
            return 0

    projects = await fetch_projects()
    matches = filter_projects(projects, conn)
    if not matches:
        return 0

    sem = asyncio.Semaphore(5)

    async def eval_sem(project: ProjectMatch) -> ProjectMatch:
        async with sem:
            return await evaluate_project(project)

    evaluated = await asyncio.gather(*[eval_sem(match) for match in matches])
    evaluated.sort(key=lambda project: project.ai_score, reverse=True)

    processed = 0
    acted = 0
    for project in evaluated:
        if not dry_run:
            budget_hit, budget_detail = daily_offer_budget_exhausted(conn)
            if budget_hit:
                print(f"-- offer pass stopped: {budget_detail}", flush=True)
                break

        outcome = await process_offer_candidate(conn, project, dry_run=dry_run)
        processed += 1
        if outcome == "limit_reached":
            break
        if outcome in {"submitted", "dry_run"}:
            acted += 1
            if acted >= MAX_OFFER_ACTIONS_PER_PASS:
                print(
                    f"-- offer pass action cap reached ({MAX_OFFER_ACTIONS_PER_PASS})",
                    flush=True,
                )
                break
        await asyncio.sleep(1)
    return processed


async def process_dialog(
    api: Kwork,
    conn: sqlite3.Connection,
    *,
    user_id: int,
    username: str,
    dry_run: bool,
) -> bool:
    messages = await api.get_dialog_with_user(username)
    incoming = [
        msg
        for msg in messages
        if (msg.message_id or 0) > 0
        and msg.from_id == user_id
        and clean_text(msg.message)
        and not reply_already_done(conn, int(msg.message_id))
    ]
    if not incoming:
        return False

    incoming_text = "\n".join(
        f"- {clean_text(msg.message)}" for msg in incoming if clean_text(msg.message)
    )
    message_ids = [int(msg.message_id) for msg in incoming if msg.message_id]
    attach_reply_to_offer_analytics(
        conn,
        message_ids=message_ids,
        user_id=user_id,
        username=username,
        incoming_text=incoming_text,
    )

    if reply_needs_manual_review(incoming, incoming_text):
        log_reply(
            conn,
            message_ids=message_ids,
            dialog_user_id=user_id,
            dialog_username=username,
            incoming_text=incoming_text,
            reply_text="manual review required",
            status="escalated",
        )
        await notify_reply_event(
            format_reply_notification(
                username=username,
                user_id=user_id,
                incoming_text=incoming_text,
                note="⚠️ Нужен ручной ответ",
            ),
        )
        print(f">> Escalated dialog @{username}", flush=True)
        return True

    history = format_history(messages, user_id)
    reply = await generate_reply(history=clip_text(history), incoming=clip_text(incoming_text))
    status = "draft"
    if not dry_run:
        await human_pause("reply", enabled=True)
        await api.send_message(user_id, reply)
        status = "sent"

    log_reply(
        conn,
        message_ids=message_ids,
        dialog_user_id=user_id,
        dialog_username=username,
        incoming_text=incoming_text,
        reply_text=reply,
        status=status,
    )
    await notify_reply_event(
        format_reply_notification(
            username=username,
            user_id=user_id,
            incoming_text=incoming_text,
            note="🤖 Автоответ отправлен" if status == "sent" else "📝 Подготовлен черновик автоответа",
        ),
    )
    print(f">> {status} reply to @{username}", flush=True)
    return True


async def reply_pass(conn: sqlite3.Connection, *, dry_run: bool) -> int:
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
                if await process_dialog(
                    api,
                    conn,
                    user_id=user_id,
                    username=username,
                    dry_run=dry_run,
                ):
                    processed += 1
            except Exception as e:
                await notify_reply_event(
                    format_reply_notification(
                        username=username,
                        user_id=user_id,
                        incoming_text="ошибка обработки входящего сообщения",
                        note=f"❌ Ошибка автоответа: <code>{html.escape(str(e)[:200])}</code>",
                    ),
                )
                print(f"!! dialog @{username}: {e}", flush=True)
    return processed


def print_status(conn: sqlite3.Connection) -> None:
    state = get_daily_offer_state(conn)
    print("daily auto-offer budget:", flush=True)
    print(
        (
            f"  {state['day_key']}: sent={state['sent_count']} / "
            f"target={state['target_count']} / remaining={state['remaining']} / "
            f"limit_reached={state['limit_reached']}"
        ),
        flush=True,
    )
    if state["limit_detail"]:
        print(f"  detail: {state['limit_detail']}", flush=True)

    print("autopilot offer log:", flush=True)
    rows = conn.execute(
        "SELECT status, COUNT(*) FROM autopilot_offer_log GROUP BY status ORDER BY status"
    ).fetchall()
    if not rows:
        print("  none", flush=True)
    else:
        for status, count in rows:
            print(f"  {status}: {count}", flush=True)

    print("\nautopilot latest offers:", flush=True)
    rows = conn.execute(
        """
        SELECT project_id, title, score, mode, status, created_at
        FROM autopilot_offer_log
        ORDER BY created_at DESC
        LIMIT 10
        """
    ).fetchall()
    for project_id, title, score, mode, status, created_at in rows:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))
        print(f"  {ts} #{project_id} [{mode}/{status}] score={score} {title}", flush=True)

    print("\ndialog reply log:", flush=True)
    rows = conn.execute(
        "SELECT status, COUNT(*) FROM dialog_reply_log GROUP BY status ORDER BY status"
    ).fetchall()
    if not rows:
        print("  none", flush=True)
    else:
        for status, count in rows:
            print(f"  {status}: {count}", flush=True)


def print_analytics(conn: sqlite3.Connection) -> None:
    old_factory = conn.row_factory
    conn.row_factory = sqlite3.Row
    rows = list(
        conn.execute(
            """
            SELECT
                project_id,
                title,
                buyer_username,
                budget_from,
                budget_to,
                offer_price,
                ai_score,
                competition_offers,
                matched_keywords,
                proposal_len,
                mode,
                sent_at,
                first_reply_at,
                reply_count
            FROM offer_analytics
            WHERE sent_at IS NOT NULL
            ORDER BY sent_at DESC
            """
        ).fetchall()
    )
    conn.row_factory = old_factory

    if not rows:
        print("analytics: no sent offers tracked yet", flush=True)
        return

    total_sent = len(rows)
    replied = [row for row in rows if row["first_reply_at"] is not None]
    replied_count = len(replied)
    reply_rate = (replied_count / total_sent) * 100 if total_sent else 0.0

    avg_reply_hours = 0.0
    if replied:
        avg_reply_hours = sum(
            max(float(row["first_reply_at"]) - float(row["sent_at"]), 0.0)
            for row in replied
        ) / replied_count / 3600

    print("analytics summary:", flush=True)
    print(f"  sent: {total_sent}", flush=True)
    print(f"  replied: {replied_count}", flush=True)
    print(f"  reply rate: {reply_rate:.1f}%", flush=True)
    print(f"  avg first reply: {avg_reply_hours:.1f}h", flush=True)

    def print_bucket_stats(
        title: str,
        items: list[tuple[str, list[sqlite3.Row]]],
    ) -> None:
        print(f"\n{title}:", flush=True)
        for label, bucket_rows in items:
            if not bucket_rows:
                print(f"  {label}: 0 sent", flush=True)
                continue
            bucket_replied = sum(1 for row in bucket_rows if row["first_reply_at"] is not None)
            bucket_rate = (bucket_replied / len(bucket_rows)) * 100
            print(
                f"  {label}: {bucket_replied}/{len(bucket_rows)} ({bucket_rate:.1f}%)",
                flush=True,
            )

    print_bucket_stats(
        "by score",
        [
            ("8-10", [row for row in rows if int(row["ai_score"]) >= 8]),
            ("6-7", [row for row in rows if 6 <= int(row["ai_score"]) <= 7]),
            ("0-5", [row for row in rows if int(row["ai_score"]) <= 5]),
        ],
    )

    print_bucket_stats(
        "by competition",
        [
            ("0-5 offers", [row for row in rows if int(row["competition_offers"]) <= 5]),
            ("6-15 offers", [row for row in rows if 6 <= int(row["competition_offers"]) <= 15]),
            ("16+ offers", [row for row in rows if int(row["competition_offers"]) >= 16]),
        ],
    )

    def price_ratio(row: sqlite3.Row) -> float:
        budget_to = int(row["budget_to"] or 0)
        budget_from = int(row["budget_from"] or 0)
        budget = max(budget_to, budget_from, 1)
        return float(row["offer_price"]) / budget

    print_bucket_stats(
        "by price ratio",
        [
            ("<= 70% budget", [row for row in rows if price_ratio(row) <= 0.70]),
            ("71-90% budget", [row for row in rows if 0.70 < price_ratio(row) <= 0.90]),
            ("> 90% budget", [row for row in rows if price_ratio(row) > 0.90]),
        ],
    )

    if replied:
        print("\nlatest replied offers:", flush=True)
        latest_replied = sorted(
            replied,
            key=lambda row: float(row["first_reply_at"] or 0),
            reverse=True,
        )[:5]
        for row in latest_replied:
            reply_delay_h = max(float(row["first_reply_at"]) - float(row["sent_at"]), 0.0) / 3600
            print(
                (
                    f"  #{row['project_id']} score={row['ai_score']} "
                    f"offers={row['competition_offers']} "
                    f"price={row['offer_price']}/{row['budget_to'] or row['budget_from']} "
                    f"reply_in={reply_delay_h:.1f}h {row['title']}"
                ),
                flush=True,
            )


async def offer_loop(conn: sqlite3.Connection, *, dry_run: bool) -> None:
    while True:
        if in_auth_block_cooldown():
            await asyncio.sleep(min(OFFER_LOOP_INTERVAL_SEC, 60))
            continue
        try:
            count = await offer_pass(conn, dry_run=dry_run)
            print(f">> Offer pass done: {count} candidates processed", flush=True)
        except Exception as e:
            if is_signin_proxy_block(e):
                print(f"!! offer loop auth blocked: {e}", flush=True)
                if start_auth_block_cooldown():
                    await notify_tg(
                        (
                            "⚠️ <b>Kwork режет текущий proxy IP на signIn</b>\n"
                            "Автопилот уходит в cooldown на 30 минут и не будет спамить одинаковой ошибкой.\n"
                            f"<code>{html.escape(str(e)[:200])}</code>"
                        ),
                    )
            else:
                await notify_tg(
                    f"❌ <b>Offer loop error</b>\n<code>{html.escape(str(e)[:200])}</code>"
                )
            print(f"!! offer loop error: {e}", flush=True)
        await asyncio.sleep(next_loop_sleep(OFFER_LOOP_INTERVAL_SEC))


async def reply_loop(conn: sqlite3.Connection, *, dry_run: bool) -> None:
    while True:
        if in_auth_block_cooldown():
            await asyncio.sleep(min(REPLY_LOOP_INTERVAL_SEC, 60))
            continue
        try:
            count = await reply_pass(conn, dry_run=dry_run)
            print(f">> Reply pass done: {count} dialogs processed", flush=True)
        except Exception as e:
            if is_signin_proxy_block(e):
                print(f"!! reply loop auth blocked: {e}", flush=True)
                if start_auth_block_cooldown():
                    await notify_tg(
                        (
                            "⚠️ <b>Kwork режет текущий proxy IP на signIn</b>\n"
                            "Автопилот уходит в cooldown на 30 минут и не будет спамить одинаковой ошибкой.\n"
                            f"<code>{html.escape(str(e)[:200])}</code>"
                        ),
                    )
            else:
                await notify_tg(
                    f"❌ <b>Reply loop error</b>\n<code>{html.escape(str(e)[:200])}</code>"
                )
            print(f"!! reply loop error: {e}", flush=True)
        await asyncio.sleep(next_loop_sleep(REPLY_LOOP_INTERVAL_SEC))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Unified Kwork autopilot")
    parser.add_argument("--once", action="store_true", help="Run one pass of offers + replies and exit")
    parser.add_argument("--dry-run", action="store_true", help="Do not send offers/replies, only log decisions")
    parser.add_argument("--status", action="store_true", help="Show autopilot status and exit")
    parser.add_argument("--analytics", action="store_true", help="Show offer analytics and exit")
    parser.add_argument("--drain-pending", action="store_true", help="Submit already queued pending offers and exit")
    parser.add_argument("--pending-limit", type=int, default=None, help="Limit how many pending offers to submit")
    args = parser.parse_args()

    if not KWORK_LOGIN or not KWORK_PASSWORD:
        print("!! Set KWORK_LOGIN and KWORK_PASSWORD in .env", flush=True)
        sys.exit(1)

    conn = init_offer_db()
    ensure_tables(conn)
    backfill_offer_analytics(conn)

    if args.status:
        print_status(conn)
        conn.close()
        return

    if args.analytics:
        print_analytics(conn)
        conn.close()
        return

    print(
        f">> Autopilot started (mode={'dry-run' if args.dry_run else 'live'})",
        flush=True,
    )

    if args.drain_pending:
        count = await submit_existing_pending(conn, limit=args.pending_limit, dry_run=args.dry_run)
        print(f">> Pending drain done: {count} items processed", flush=True)
        conn.close()
        return

    if args.once:
        offers = await offer_pass(conn, dry_run=args.dry_run)
        replies = await reply_pass(conn, dry_run=args.dry_run)
        print(f">> One-shot done: offers={offers}, replies={replies}", flush=True)
        conn.close()
        return

    try:
        acquire_lock()
    except RuntimeError as e:
        print(f"!! {e}", flush=True)
        conn.close()
        sys.exit(1)
    atexit.register(release_lock)

    await asyncio.gather(
        offer_loop(conn, dry_run=args.dry_run),
        reply_loop(conn, dry_run=args.dry_run),
    )


if __name__ == "__main__":
    asyncio.run(main())
