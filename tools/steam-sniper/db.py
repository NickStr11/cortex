"""SQLite persistence layer for Steam Sniper.

Single source of truth: replaces watchlist.json.
Used by both Telegram bot (main.py) and future FastAPI dashboard.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from beartype import beartype

if TYPE_CHECKING:
    from collections.abc import Generator

logger = logging.getLogger("sniper.db")

DB_PATH = Path(__file__).parent / "data" / "sniper.db"


@contextmanager
def get_conn() -> Generator[sqlite3.Connection]:
    """Return a configured SQLite connection with WAL mode."""
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@beartype
def init_db() -> None:
    """Create all tables if they don't exist. Safe to call multiple times."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                name_lower      TEXT NOT NULL,
                type            TEXT NOT NULL CHECK(type IN ('buy','sell')),
                target_rub      REAL NOT NULL,
                added_price_usd REAL,
                added_at        TEXT NOT NULL,
                qty             INTEGER DEFAULT 1,
                display_name    TEXT,
                category        TEXT,
                image_url       TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_name_type
                ON watchlist(name_lower, type);

            CREATE TABLE IF NOT EXISTS price_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name_lower  TEXT NOT NULL,
                price_usd   REAL NOT NULL,
                ts          TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_ph_name_ts
                ON price_history(name_lower, ts);

            CREATE TABLE IF NOT EXISTS alerts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                type        TEXT NOT NULL CHECK(type IN ('buy','sell')),
                price_usd   REAL NOT NULL,
                target_rub  REAL NOT NULL,
                ts          TEXT NOT NULL DEFAULT (datetime('now')),
                message     TEXT
            );

            CREATE TABLE IF NOT EXISTS exchange_rates (
                currency    TEXT PRIMARY KEY,
                rate        REAL NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_lists (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT NOT NULL,
                item_name  TEXT NOT NULL,
                list_type  TEXT NOT NULL CHECK(list_type IN ('favorite','wishlist')),
                added_at   TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_user_lists_unique
                ON user_lists(user_id, item_name, list_type);
        """)
        # Migrate: add columns if missing (safe for existing DBs)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(watchlist)")}
        if "display_name" not in cols:
            conn.execute("ALTER TABLE watchlist ADD COLUMN display_name TEXT")
        if "category" not in cols:
            conn.execute("ALTER TABLE watchlist ADD COLUMN category TEXT")
        if "image_url" not in cols:
            conn.execute("ALTER TABLE watchlist ADD COLUMN image_url TEXT")


@beartype
def get_watchlist() -> dict[str, list[dict]]:
    """Drop-in replacement for _load_watchlist(). Returns {buy: [...], sell: [...]}."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM watchlist ORDER BY added_at"
        ).fetchall()
    result: dict[str, list[dict]] = {"buy": [], "sell": []}
    for row in rows:
        result[row["type"]].append(dict(row))
    return result


@beartype
def upsert_item(
    name: str,
    type_: str,
    target_rub: float,
    added_price_usd: float,
    added_at: str,
    qty: int = 1,
    display_name: str | None = None,
    category: str | None = None,
    image_url: str | None = None,
) -> None:
    """Insert or update a watchlist item. Idempotent on (name_lower, type)."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO watchlist(name, name_lower, type, target_rub,
                                  added_price_usd, added_at, qty,
                                  display_name, category, image_url)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(name_lower, type) DO UPDATE SET
                target_rub=excluded.target_rub,
                added_price_usd=excluded.added_price_usd,
                added_at=excluded.added_at,
                display_name=COALESCE(excluded.display_name, watchlist.display_name),
                category=COALESCE(excluded.category, watchlist.category),
                image_url=COALESCE(excluded.image_url, watchlist.image_url)
            """,
            (name, name.lower(), type_, target_rub, added_price_usd, added_at, qty,
             display_name, category, image_url),
        )


@beartype
def remove_item(name: str) -> int:
    """Delete watchlist entries by name. Returns count of rows deleted."""
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM watchlist WHERE name_lower=?", (name.lower(),)
        )
        return cur.rowcount


@beartype
def get_watchlist_names() -> set[str]:
    """Return set of name_lower strings from watchlist."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT name_lower FROM watchlist"
        ).fetchall()
    return {row["name_lower"] for row in rows}


@beartype
def insert_price_snapshots(snapshots: list[tuple[str, float]]) -> None:
    """Bulk insert price history rows."""
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO price_history(name_lower, price_usd) VALUES (?,?)",
            snapshots,
        )


@beartype
def prune_old_history(days: int = 90) -> int:
    """Delete price_history rows older than N days. Returns rowcount."""
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM price_history WHERE ts < datetime('now', ?)",
            (f"-{days} days",),
        )
        return cur.rowcount


@beartype
def log_alert(
    name: str,
    type_: str,
    price_usd: float,
    target_rub: float,
    message: str,
) -> None:
    """Record a triggered alert to the alerts table."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO alerts(name, type, price_usd, target_rub, message)
            VALUES (?,?,?,?,?)
            """,
            (name, type_, price_usd, target_rub, message),
        )


@beartype
def migrate_json_to_sqlite(json_path: Path, rate: float) -> int:
    """Import watchlist.json into SQLite. target>100 = RUB, else USD*rate. Idempotent."""
    if not json_path.exists():
        return 0
    data = json.loads(json_path.read_text(encoding="utf-8"))
    migrated = 0
    for type_ in ("buy", "sell"):
        for entry in data.get(type_, []):
            raw_target = float(entry["target"])
            if raw_target > 100.0:
                target_rub = raw_target
                logger.warning(
                    "Migration: %s target=%.1f treated as RUB",
                    entry["name"],
                    raw_target,
                )
            else:
                target_rub = raw_target * rate
                logger.info(
                    "Migration: %s target=%.1f USD -> %.0f RUB",
                    entry["name"],
                    raw_target,
                    target_rub,
                )
            upsert_item(
                name=entry["name"],
                type_=type_,
                target_rub=target_rub,
                added_price_usd=float(entry.get("added_price", 0)),
                added_at=entry.get("added_at", datetime.now().isoformat()),
                qty=1,
            )
            migrated += 1
    return migrated


@beartype
def get_price_history(name: str, tf: str = "7d") -> list[dict]:
    """Return price history rows for charting. Sorted by ts ASC.

    Timeframes: '24h', '7d', '30d', 'all'. Defaults to '7d' if invalid.
    """
    tf_map = {"24h": "-1 day", "7d": "-7 days", "30d": "-30 days"}
    with get_conn() as conn:
        if tf == "all":
            rows = conn.execute(
                "SELECT price_usd, ts FROM price_history "
                "WHERE name_lower = ? ORDER BY ts ASC",
                (name.lower(),),
            ).fetchall()
        else:
            modifier = tf_map.get(tf, "-7 days")
            rows = conn.execute(
                "SELECT price_usd, ts FROM price_history "
                "WHERE name_lower = ? AND ts >= datetime('now', ?) "
                "ORDER BY ts ASC",
                (name.lower(), modifier),
            ).fetchall()
    return [dict(row) for row in rows]


@beartype
def get_portfolio_stats(prices: dict[str, float], rate: float = 0.0) -> dict:
    """Compute portfolio stats from current prices map.

    Args:
        prices: {name_lower: price_usd} from collector cache.
        rate: USD/RUB rate to use (lis-skins rate, not CBR).

    Returns dict with total_items, total_value_rub, total_added_rub, delta_pct.
    """
    wl = get_watchlist()
    if rate <= 0:
        rate = get_cached_rate("USD") or 0.0
    all_items = wl["buy"] + wl["sell"]

    total_value_rub = 0.0
    total_added_rub = 0.0

    for item in all_items:
        name_lower = item["name_lower"]
        qty = item.get("qty", 1) or 1
        added_usd = item.get("added_price_usd", 0) or 0

        if name_lower in prices:
            total_value_rub += prices[name_lower] * rate * qty
        if added_usd > 0:
            total_added_rub += added_usd * rate * qty

    delta_pct = (
        ((total_value_rub - total_added_rub) / total_added_rub) * 100
        if total_added_rub > 0
        else 0.0
    )

    return {
        "total_items": len(all_items),
        "total_value_rub": round(total_value_rub, 2),
        "total_added_rub": round(total_added_rub, 2),
        "delta_pct": round(delta_pct, 2),
    }


@beartype
def get_recent_alerts(limit: int = 20) -> list[dict]:
    """Return recent alerts for activity feed, DESC by timestamp."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name, type, price_usd, target_rub, ts, message "
            "FROM alerts ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


@beartype
def get_cached_rate(currency: str = "USD") -> float | None:
    """Return cached exchange rate or None if not stored."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT rate FROM exchange_rates WHERE currency=?", (currency,)
        ).fetchone()
    return float(row["rate"]) if row else None


@beartype
def save_rate(currency: str, rate: float) -> None:
    """Upsert exchange rate."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO exchange_rates(currency, rate, updated_at)
            VALUES (?,?,datetime('now'))
            ON CONFLICT(currency) DO UPDATE SET
                rate=excluded.rate, updated_at=excluded.updated_at
            """,
            (currency, rate),
        )


# --- User Lists (favorites / wishlist) ---


@beartype
def add_list_item(user_id: str, item_name: str, list_type: str) -> None:
    """Add item to user's list. Idempotent -- duplicate is silently ignored."""
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO user_lists(user_id, item_name, list_type) VALUES (?,?,?)",
            (user_id, item_name, list_type),
        )


@beartype
def remove_list_item(user_id: str, item_name: str, list_type: str) -> int:
    """Remove item from user's list. Returns rows deleted (0 or 1)."""
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM user_lists WHERE user_id=? AND item_name=? AND list_type=?",
            (user_id, item_name, list_type),
        )
        return cur.rowcount


@beartype
def get_list_items(user_id: str, list_type: str | None = None) -> list[dict]:
    """Return user's list items. If list_type is None, return all lists."""
    with get_conn() as conn:
        if list_type:
            rows = conn.execute(
                "SELECT item_name, list_type, added_at FROM user_lists "
                "WHERE user_id=? AND list_type=? ORDER BY added_at DESC",
                (user_id, list_type),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT item_name, list_type, added_at FROM user_lists "
                "WHERE user_id=? ORDER BY added_at DESC",
                (user_id,),
            ).fetchall()
    return [dict(row) for row in rows]
