from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from beartype import beartype

from config import COINS
from db import get_connection, get_stats
from exchanges import ALL_EXCHANGES

PERIODS: list[tuple[str, int]] = [
    ("1d", 1),
    ("2d", 2),
    ("3d", 3),
    ("7d", 7),
    ("14d", 14),
    ("21d", 21),
    ("30d", 30),
]

COINS_BY_CAP: list[str] = [
    "BTC", "ETH", "XRP", "SOL", "DOGE",
    "ADA", "TRX", "LINK", "SUI", "AVAX",
    "BCH", "DOT", "NEAR", "APT", "FIL",
    "OP", "ARB", "XLM", "TON", "HYPE", "PAXG",
]

_EXCHANGE_TYPES: dict[str, str] = {ex.name: ex.exchange_type for ex in ALL_EXCHANGES}
_HIST_CACHE: dict[str, Any] | None = None
_HIST_CACHE_TS: int = 0


@dataclass(frozen=True, slots=True)
class LatestRateRow:
    ts: int
    exchange: str
    coin: str
    rate_raw: float
    rate_ann: float
    interval_h: int
    price: float | None
    next_funding_ts: int | None


@beartype
def _age_ago_str(ts: int, now: int) -> str:
    ago = max(now - ts, 0)
    if ago < 60:
        return f"{ago}s ago"
    if ago < 3600:
        return f"{ago // 60}m ago"
    return f"{ago // 3600}h {(ago % 3600) // 60}m ago"


@beartype
def _window_until_ts(now: int) -> int:
    return now - (now % 86400)


@beartype
def _annualize_points(points: list[tuple[float, int]]) -> float | None:
    total_hours = sum(interval_h for _, interval_h in points)
    if total_hours <= 0:
        return None
    total_rate = sum(rate_raw for rate_raw, _ in points)
    return round(total_rate * 8760 * 100 / total_hours, 1)


@beartype
def _infer_next_funding_ts(interval_h: int, now: int) -> int:
    interval_s = max(interval_h, 1) * 3600
    return ((now // interval_s) + 1) * interval_s * 1000


@beartype
def _is_row_fresh(row: LatestRateRow, now: int) -> bool:
    max_age = max(6 * 3600, row.interval_h * 2 * 3600)
    return now - row.ts <= max_age


@beartype
def _format_price(value: float | None) -> float | None:
    if value is None:
        return None
    if value >= 1000:
        return round(value, 1)
    if value >= 100:
        return round(value, 2)
    if value >= 1:
        return round(value, 4)
    return round(value, 6)


@beartype
def _load_latest_rows(now: int) -> list[LatestRateRow]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT r.ts, r.exchange, r.coin, r.rate_raw, r.rate_ann, r.interval_h, r.price, r.next_funding_ts
            FROM rates r
            JOIN (
                SELECT exchange, coin, MAX(ts) AS max_ts
                FROM rates
                GROUP BY exchange, coin
            ) latest
              ON latest.exchange = r.exchange
             AND latest.coin = r.coin
             AND latest.max_ts = r.ts
            """
        ).fetchall()
    finally:
        conn.close()

    items = [
        LatestRateRow(
            ts=row[0],
            exchange=row[1],
            coin=row[2],
            rate_raw=row[3],
            rate_ann=row[4],
            interval_h=row[5],
            price=row[6],
            next_funding_ts=row[7],
        )
        for row in rows
    ]
    return [row for row in items if row.coin in COINS and _is_row_fresh(row, now)]


@beartype
def build_live_snapshot() -> dict[str, Any]:
    now = int(time.time())
    latest_rows = _load_latest_rows(now)

    rows_by_coin: dict[str, list[LatestRateRow]] = {coin: [] for coin in COINS}
    for row in latest_rows:
        rows_by_coin.setdefault(row.coin, []).append(row)

    max_ts = max((row.ts for row in latest_rows), default=0)
    live_coins: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []

    for coin in COINS_BY_CAP:
        coin_rows = sorted(rows_by_coin.get(coin, []), key=lambda row: row.rate_ann)
        if not coin_rows:
            continue

        live_rows: list[dict[str, Any]] = []
        for row in coin_rows:
            next_ts = row.next_funding_ts or _infer_next_funding_ts(row.interval_h, now)
            live_rows.append({
                "exchange": row.exchange,
                "exchange_type": _EXCHANGE_TYPES.get(row.exchange, "UNKNOWN"),
                "price": _format_price(row.price),
                "funding_apr_pct": round(row.rate_ann, 2),
                "funding_period_pct": round(row.rate_raw * 100, 6),
                "interval_h": row.interval_h,
                "payments": max(round(24 / max(row.interval_h, 1)), 1),
                "next_funding_ts": next_ts,
                "as_of_ts": row.ts * 1000,
            })

        long_row = coin_rows[0]
        short_row = coin_rows[-1]
        funding_spread = round(short_row.rate_ann - long_row.rate_ann, 2)
        price_spread_pct: float | None = None
        price_spread_abs: float | None = None
        break_even_days: float | None = None
        if long_row.price and short_row.price and long_row.price > 0:
            price_spread_pct = round(((short_row.price - long_row.price) / long_row.price) * 100, 3)
            price_spread_abs = round(short_row.price - long_row.price, 6)
            daily_edge = funding_spread / 365
            if daily_edge > 0 and price_spread_pct > 0:
                break_even_days = round(price_spread_pct / daily_edge, 1)

        pair = {
            "ticker": coin,
            "long_exchange": long_row.exchange,
            "short_exchange": short_row.exchange,
            "long_price": _format_price(long_row.price),
            "short_price": _format_price(short_row.price),
            "long_funding_apr_pct": round(long_row.rate_ann, 2),
            "short_funding_apr_pct": round(short_row.rate_ann, 2),
            "funding_spread_apr_pct": funding_spread,
            "price_spread_pct": price_spread_pct,
            "price_spread_abs": price_spread_abs,
            "long_interval_h": long_row.interval_h,
            "short_interval_h": short_row.interval_h,
            "long_payments": max(round(24 / max(long_row.interval_h, 1)), 1),
            "short_payments": max(round(24 / max(short_row.interval_h, 1)), 1),
            "long_next_funding_ts": long_row.next_funding_ts or _infer_next_funding_ts(long_row.interval_h, now),
            "short_next_funding_ts": short_row.next_funding_ts or _infer_next_funding_ts(short_row.interval_h, now),
            "break_even_days": break_even_days,
        }

        pairs.append(pair)
        live_coins.append({
            "ticker": coin,
            "best_pair": pair,
            "exchanges": live_rows,
        })

    active_exchanges = len({row.exchange for row in latest_rows})
    stats = get_stats()
    return {
        "active_exchanges": active_exchanges,
        "snapshots": stats["snapshots"],
        "total_rates": stats["rates"],
        "last_scan_ago": _age_ago_str(max_ts, now) if max_ts else "n/a",
        "last_scan_ts": max_ts * 1000 if max_ts else None,
        "scan_interval": "every 1m",
        "coins": live_coins,
        "pairs": sorted(pairs, key=lambda item: item["funding_spread_apr_pct"], reverse=True),
    }


@beartype
def build_historical_apr() -> dict[str, Any]:
    global _HIST_CACHE, _HIST_CACHE_TS

    now = int(time.time())
    window_until = _window_until_ts(now)
    if (
        _HIST_CACHE is not None
        and now - _HIST_CACHE_TS < 300
        and _HIST_CACHE["window_until_ms"] == window_until * 1000
    ):
        return _HIST_CACHE

    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT coin, exchange, ts, rate_raw, interval_h
            FROM rates
            WHERE ts >= ? AND ts < ?
            ORDER BY coin, exchange, ts
            """,
            (window_until - 30 * 86400, window_until),
        ).fetchall()
    finally:
        conn.close()

    rows_by_coin_exchange: dict[str, dict[str, list[tuple[int, float, int]]]] = {
        coin: {} for coin in COINS
    }
    for coin, exchange, ts, rate_raw, interval_h in rows:
        if ts % 3600 >= 10:
            continue
        rows_by_coin_exchange.setdefault(coin, {}).setdefault(exchange, []).append((ts, rate_raw, interval_h))

    exchanges_seen: set[str] = set()
    coins_data: list[dict[str, Any]] = []
    for coin in COINS_BY_CAP:
        by_exchange = rows_by_coin_exchange.get(coin, {})
        if not by_exchange:
            continue

        exchange_rows: list[dict[str, Any]] = []
        for exchange, points in sorted(by_exchange.items()):
            apr_values: list[float | None] = []
            for _, days in PERIODS:
                cutoff = window_until - days * 86400
                period_points = [
                    (rate_raw, interval_h)
                    for ts, rate_raw, interval_h in points
                    if cutoff <= ts < window_until
                ]
                apr_values.append(_annualize_points(period_points))
            if any(value is not None for value in apr_values):
                exchange_rows.append({
                    "exchange_code": exchange,
                    "apr": apr_values,
                })
                exchanges_seen.add(exchange)

        if exchange_rows:
            coins_data.append({
                "ticker": coin,
                "exchanges": exchange_rows,
            })

    payload = {
        "build_id": None,
        "coins": coins_data,
        "days_max": 30,
        "exchanges": sorted(exchanges_seen),
        "generated_at": now * 1000,
        "partial": False,
        "periods": [label for label, _ in PERIODS],
        "server_ts": now * 1000,
        "window_until_ms": window_until * 1000,
    }
    _HIST_CACHE = payload
    _HIST_CACHE_TS = now
    return payload
