from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from beartype import beartype

from exchanges import FundingRate
from scanner import Spread

DB_PATH = Path(__file__).parent / "funding.db"


@beartype
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS rates (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        INTEGER NOT NULL,       -- unix epoch seconds
            exchange  TEXT NOT NULL,
            coin      TEXT NOT NULL,
            rate_raw  REAL NOT NULL,           -- per-interval rate
            rate_ann  REAL NOT NULL,           -- annualized %
            interval_h INTEGER NOT NULL        -- funding interval hours
        );

        CREATE INDEX IF NOT EXISTS idx_rates_coin_ts
            ON rates(coin, ts DESC);

        CREATE INDEX IF NOT EXISTS idx_rates_exchange_coin
            ON rates(exchange, coin, ts DESC);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_rates_unique
            ON rates(ts, exchange, coin);

        CREATE TABLE IF NOT EXISTS spreads (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            ts             INTEGER NOT NULL,
            coin           TEXT NOT NULL,
            long_exchange  TEXT NOT NULL,
            short_exchange TEXT NOT NULL,
            long_rate      REAL NOT NULL,
            short_rate     REAL NOT NULL,
            spread         REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_spreads_coin_ts
            ON spreads(coin, ts DESC);
    """)


@beartype
def save_rates(rates: list[FundingRate]) -> int:
    """Save a batch of funding rates. Returns number of rows inserted."""
    if not rates:
        return 0
    ts = int(time.time())
    conn = get_connection()
    try:
        conn.executemany(
            "INSERT OR IGNORE INTO rates (ts, exchange, coin, rate_raw, rate_ann, interval_h) VALUES (?,?,?,?,?,?)",
            [(ts, r.exchange, r.coin, r.rate, r.rate_ann, r.interval_h) for r in rates],
        )
        conn.commit()
        return len(rates)
    finally:
        conn.close()


@beartype
def save_spreads(spreads: list[Spread]) -> int:
    """Save a batch of spread calculations. Returns number of rows inserted."""
    if not spreads:
        return 0
    ts = int(time.time())
    conn = get_connection()
    try:
        conn.executemany(
            "INSERT INTO spreads (ts, coin, long_exchange, short_exchange, long_rate, short_rate, spread) VALUES (?,?,?,?,?,?,?)",
            [(ts, s.coin, s.long_exchange, s.short_exchange, s.long_rate, s.short_rate, s.spread) for s in spreads],
        )
        conn.commit()
        return len(spreads)
    finally:
        conn.close()


@beartype
def get_rate_history(coin: str, exchange: str, limit: int = 50) -> list[tuple[int, float]]:
    """Get historical rates for a coin on an exchange. Returns [(ts, rate_ann), ...]."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT ts, rate_ann FROM rates WHERE coin=? AND exchange=? ORDER BY ts DESC LIMIT ?",
            (coin, exchange, limit),
        ).fetchall()
        return [(r[0], r[1]) for r in reversed(rows)]
    finally:
        conn.close()


@beartype
def get_spread_history(coin: str, limit: int = 50) -> list[tuple[int, float, str, str]]:
    """Get spread history for a coin. Returns [(ts, spread, long_ex, short_ex), ...]."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT ts, spread, long_exchange, short_exchange FROM spreads WHERE coin=? ORDER BY ts DESC LIMIT ?",
            (coin, limit),
        ).fetchall()
        return [(r[0], r[1], r[2], r[3]) for r in reversed(rows)]
    finally:
        conn.close()


@beartype
def detect_trend(coin: str, exchange: str, consecutive: int = 3) -> str | None:
    """Check if last N rates show a growing trend. Returns 'up'/'down'/None."""
    history = get_rate_history(coin, exchange, limit=consecutive + 1)
    if len(history) < consecutive + 1:
        return None

    recent = [h[1] for h in history[-(consecutive + 1):]]
    diffs = [recent[i + 1] - recent[i] for i in range(len(recent) - 1)]

    if all(d > 0 for d in diffs[-consecutive:]):
        return "up"
    if all(d < 0 for d in diffs[-consecutive:]):
        return "down"
    return None


@beartype
def detect_spread_trend(coin: str, consecutive: int = 3) -> str | None:
    """Check if spread for a coin is growing/shrinking over last N snapshots."""
    history = get_spread_history(coin, limit=consecutive + 1)
    if len(history) < consecutive + 1:
        return None

    recent = [h[1] for h in history[-(consecutive + 1):]]
    diffs = [recent[i + 1] - recent[i] for i in range(len(recent) - 1)]

    if all(d > 0 for d in diffs[-consecutive:]):
        return "up"
    if all(d < 0 for d in diffs[-consecutive:]):
        return "down"
    return None


@beartype
def get_stats() -> dict[str, int]:
    """Get DB stats."""
    conn = get_connection()
    try:
        rate_count = conn.execute("SELECT COUNT(*) FROM rates").fetchone()[0]
        spread_count = conn.execute("SELECT COUNT(*) FROM spreads").fetchone()[0]
        snapshot_count = conn.execute("SELECT COUNT(DISTINCT ts) FROM rates").fetchone()[0]
        return {
            "rates": rate_count,
            "spreads": spread_count,
            "snapshots": snapshot_count,
        }
    finally:
        conn.close()
