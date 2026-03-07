"""Backfill 30 days of settled funding rates from all exchanges."""
from __future__ import annotations

import asyncio
import time

import httpx
from beartype import beartype

from config import ANN_1H, ANN_8H, COINS

# KuCoin BTC -> XBT
_KUCOIN_MAP: dict[str, str] = {"BTC": "XBT"}

# EdgeX contract IDs
_EDGEX_CONTRACTS: dict[str, str] = {
    "10000001": "BTC", "10000002": "ETH", "10000003": "SOL",
    "10000006": "LINK", "10000007": "AVAX", "10000009": "XRP",
    "10000017": "TON",
}
_EDGEX_COIN_TO_ID: dict[str, str] = {v: k for k, v in _EDGEX_CONTRACTS.items()}

DAYS = 30
SINCE_MS = int((time.time() - DAYS * 86400) * 1000)
SINCE_S = int(time.time() - DAYS * 86400)


@beartype
def _ann(rate: float, interval_h: int) -> float:
    """Annualize a per-interval rate to %/yr."""
    return rate * int(365 * 24 / max(interval_h, 1)) * 100


# ---------------------------------------------------------------------------
# Fetch functions — each returns [(ts_seconds, exchange, coin, rate_raw, rate_ann, interval_h)]
# ---------------------------------------------------------------------------
Row = tuple[int, str, str, float, float, int]


async def _binance(client: httpx.AsyncClient) -> list[Row]:
    rows: list[Row] = []
    for coin in COINS:
        resp = await client.get(
            "https://fapi.binance.com/fapi/v1/fundingRate",
            params={"symbol": f"{coin}USDT", "startTime": SINCE_MS, "limit": 1000},
        )
        if resp.status_code != 200:
            continue
        for item in resp.json():
            r = float(item["fundingRate"])
            ts = int(item["fundingTime"]) // 1000
            rows.append((ts, "BINANCE", coin, r, _ann(r, 8), 8))
    print(f"  BINANCE: {len(rows)} rates")
    return rows


async def _bybit(client: httpx.AsyncClient) -> list[Row]:
    rows: list[Row] = []
    for coin in COINS:
        end_time: int | None = None
        while True:
            params: dict[str, str | int] = {
                "category": "linear", "symbol": f"{coin}USDT", "limit": 200,
            }
            if end_time:
                params["endTime"] = end_time
            resp = await client.get(
                "https://api.bybit.com/v5/market/funding/history", params=params,
            )
            if resp.status_code != 200:
                break
            items = resp.json().get("result", {}).get("list", [])
            if not items:
                break
            for item in items:
                r = float(item["fundingRate"])
                ts = int(item["fundingRateTimestamp"]) // 1000
                if ts >= SINCE_S:
                    rows.append((ts, "BYBIT", coin, r, _ann(r, 8), 8))
            oldest_ts = int(items[-1]["fundingRateTimestamp"])
            if oldest_ts // 1000 < SINCE_S or len(items) < 200:
                break
            end_time = oldest_ts - 1
    print(f"  BYBIT: {len(rows)} rates")
    return rows


async def _okx(client: httpx.AsyncClient) -> list[Row]:
    rows: list[Row] = []
    for coin in COINS:
        resp = await client.get(
            "https://www.okx.com/api/v5/public/funding-rate-history",
            params={"instId": f"{coin}-USDT-SWAP", "limit": 100},
        )
        if resp.status_code != 200:
            continue
        for item in resp.json().get("data", []):
            r = float(item["fundingRate"])
            ts = int(item["fundingTime"]) // 1000
            if ts >= SINCE_S:
                rows.append((ts, "OKX", coin, r, _ann(r, 8), 8))
    print(f"  OKX: {len(rows)} rates")
    return rows


async def _kucoin(client: httpx.AsyncClient) -> list[Row]:
    rows: list[Row] = []
    for coin in COINS:
        sym = f"{_KUCOIN_MAP.get(coin, coin)}USDTM"
        resp = await client.get(
            f"https://api-futures.kucoin.com/api/v1/contract/funding-rates",
            params={"symbol": sym, "from": SINCE_MS, "to": int(time.time() * 1000)},
        )
        if resp.status_code != 200:
            continue
        for item in resp.json().get("data", []):
            r = float(item["fundingRate"])
            ts = int(item["timepoint"]) // 1000
            rows.append((ts, "KUCOIN", coin, r, _ann(r, 8), 8))
    print(f"  KUCOIN: {len(rows)} rates")
    return rows


async def _bitget(client: httpx.AsyncClient) -> list[Row]:
    rows: list[Row] = []
    for coin in COINS:
        resp = await client.get(
            "https://api.bitget.com/api/v2/mix/market/history-fund-rate",
            params={"symbol": f"{coin}USDT", "productType": "USDT-FUTURES", "pageSize": 100},
        )
        if resp.status_code != 200:
            continue
        for item in resp.json().get("data", []):
            r = float(item["fundingRate"])
            ts = int(item["fundingTime"]) // 1000
            if ts >= SINCE_S:
                rows.append((ts, "BITGET", coin, r, _ann(r, 8), 8))
    print(f"  BITGET: {len(rows)} rates")
    return rows


async def _gate(client: httpx.AsyncClient) -> list[Row]:
    rows: list[Row] = []
    for coin in COINS:
        resp = await client.get(
            "https://api.gateio.ws/api/v4/futures/usdt/funding_rate",
            params={"contract": f"{coin}_USDT", "limit": 1000},
        )
        if resp.status_code != 200:
            continue
        for item in resp.json():
            r = float(item["r"])
            ts = int(item["t"])  # already seconds
            if ts >= SINCE_S:
                rows.append((ts, "GATE", coin, r, _ann(r, 8), 8))
    print(f"  GATE: {len(rows)} rates")
    return rows


async def _mexc(client: httpx.AsyncClient) -> list[Row]:
    rows: list[Row] = []
    for coin in COINS:
        # Fetch multiple pages to get 30 days
        for page in range(1, 6):
            resp = await client.get(
                "https://contract.mexc.com/api/v1/contract/funding_rate/history",
                params={"symbol": f"{coin}_USDT", "page_num": page, "page_size": 100},
            )
            if resp.status_code != 200:
                break
            data = resp.json().get("data", {})
            items = data.get("resultList", [])
            if not items:
                break
            for item in items:
                r = float(item["fundingRate"])
                ts = int(item["settleTime"]) // 1000
                if ts >= SINCE_S:
                    rows.append((ts, "MEXC", coin, r, _ann(r, 8), 8))
            # Stop if we've gone past our window
            oldest = min(int(i["settleTime"]) // 1000 for i in items)
            if oldest < SINCE_S:
                break
    print(f"  MEXC: {len(rows)} rates")
    return rows


async def _hyperliquid(client: httpx.AsyncClient) -> list[Row]:
    rows: list[Row] = []
    for coin in COINS:
        # Paginate: API returns ~500 per request, need ~720 for 30 days
        start_ms = SINCE_MS
        while True:
            resp = await client.post(
                "https://api.hyperliquid.xyz/info",
                json={"type": "fundingHistory", "coin": coin, "startTime": start_ms},
            )
            if resp.status_code != 200:
                break
            items = resp.json()
            if not items:
                break
            for item in items:
                r = float(item["fundingRate"])
                ts = int(item["time"]) // 1000
                rows.append((ts, "HYPERLIQUID", coin, r, _ann(r, 1), 1))
            # Move start past last returned item
            last_ms = int(items[-1]["time"])
            if last_ms <= start_ms:
                break
            start_ms = last_ms + 1
            if len(items) < 500:
                break  # Got all data
    print(f"  HYPERLIQUID: {len(rows)} rates")
    return rows


async def _paradex(client: httpx.AsyncClient) -> list[Row]:
    rows: list[Row] = []
    for coin in COINS:
        seen_ts: set[int] = set()
        cursor: str | None = None
        # Paradex streams every 5s; paginate with cursor to cover 30 days.
        # We bucket to 8h settlement windows (max ~90 per coin).
        # Each page of 1000 entries covers ~83min; need ~520 pages for 30d.
        # Limit to 50 pages (~3 days) per coin for practical speed.
        for _ in range(50):  # safety limit
            params: dict[str, str | int] = {
                "market": f"{coin}-USD-PERP", "page_size": 1000,
            }
            if cursor:
                params["cursor"] = cursor
            else:
                params["start_time"] = SINCE_S
            resp = await client.get(
                "https://api.prod.paradex.trade/v1/funding/data", params=params,
            )
            if resp.status_code != 200:
                break
            body = resp.json()
            items = body.get("results", [])
            if not items:
                break
            for item in items:
                r = float(item.get("funding_rate_8h", item.get("funding_rate", "0")))
                ts = int(item["created_at"]) // 1000
                # Bucket to 8h settlement windows
                bucket = ts - (ts % (8 * 3600))
                if bucket not in seen_ts:
                    seen_ts.add(bucket)
                    period_h = int(item.get("funding_period_hours", 8))
                    rows.append((bucket, "PARADEX", coin, r, _ann(r, period_h), period_h))
            cursor = body.get("next")
            if not cursor:
                break
            # Stop if we've covered all settlement windows (~90 per 30 days)
            if len(seen_ts) >= 90:
                break
    print(f"  PARADEX: {len(rows)} rates")
    return rows


async def _edgex(client: httpx.AsyncClient) -> list[Row]:
    rows: list[Row] = []
    for coin in COINS:
        cid = _EDGEX_COIN_TO_ID.get(coin)
        if not cid:
            continue
        # Paginate to get full 30 days (4h interval = ~180 entries per coin)
        offset_data: str | None = None
        for _ in range(5):  # max 5 pages
            params: dict[str, str | int] = {
                "contractId": cid, "size": 200,
                "filterSettlementFundingRate": "true",
            }
            if offset_data:
                params["offsetData"] = offset_data
            resp = await client.get(
                "https://pro.edgex.exchange/api/v1/public/funding/getFundingRatePage",
                params=params,
            )
            if resp.status_code != 200:
                break
            data = resp.json().get("data", {})
            items = data.get("dataList", [])
            if not items:
                break
            for item in items:
                r = float(item["fundingRate"])
                ts = int(item["fundingTimestamp"]) // 1000
                interval_min = int(item.get("fundingRateIntervalMin", 240))
                interval_h = max(interval_min // 60, 1)
                if ts >= SINCE_S:
                    rows.append((ts, "EDGEX", coin, r, _ann(r, interval_h), interval_h))
            offset_data = data.get("nextPageOffsetData")
            if not offset_data:
                break
            # Stop if we've reached beyond our window
            oldest_ts = int(items[-1]["fundingTimestamp"]) // 1000
            if oldest_ts < SINCE_S:
                break
    print(f"  EDGEX: {len(rows)} rates")
    return rows


async def _pacifica(client: httpx.AsyncClient) -> list[Row]:
    rows: list[Row] = []
    for coin in COINS:
        resp = await client.get(
            "https://api.pacifica.fi/api/v1/funding_rate/history",
            params={"symbol": coin, "limit": 1000},
        )
        if resp.status_code != 200:
            continue
        for item in resp.json().get("data", []):
            r = float(item["funding_rate"])
            ts = int(item["created_at"]) // 1000
            if ts >= SINCE_S:
                rows.append((ts, "PACIFICA", coin, r, _ann(r, 1), 1))
    print(f"  PACIFICA: {len(rows)} rates")
    return rows


async def _extended(client: httpx.AsyncClient) -> list[Row]:
    rows: list[Row] = []
    now_ms = int(time.time() * 1000)
    for coin in COINS:
        resp = await client.get(
            f"https://api.starknet.extended.exchange/api/v1/info/{coin}-USD/funding",
            params={"startTime": SINCE_MS, "endTime": now_ms, "limit": 1000},
        )
        if resp.status_code != 200:
            continue
        for item in resp.json().get("data", []):
            r = float(item["f"])
            ts = int(item["T"]) // 1000
            rows.append((ts, "EXTENDED", coin, r, _ann(r, 1), 1))
    print(f"  EXTENDED: {len(rows)} rates")
    return rows


async def backfill() -> None:
    """Fetch 30 days of settled rates from all exchanges and save to DB."""
    import sqlite3
    from db import DB_PATH, get_connection

    # Ensure tables + unique index exist
    conn = get_connection()
    conn.close()

    print(f"Backfilling {DAYS} days of settled funding rates...")
    print(f"  Since: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(SINCE_S))}")
    print(f"  Coins: {len(COINS)}")
    print()

    all_rows: list[Row] = []

    async with httpx.AsyncClient(timeout=30) as client:
        fetchers = [
            _binance, _bybit, _okx, _kucoin, _bitget, _gate, _mexc,
            _hyperliquid, _paradex, _edgex, _pacifica, _extended,
        ]
        results = await asyncio.gather(
            *[f(client) for f in fetchers],
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"  ERROR in {fetchers[i].__name__}: {result}")
            else:
                all_rows.extend(result)

    print(f"\nTotal: {len(all_rows)} rates")

    # Insert into DB
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    inserted = 0
    batch_size = 1000
    for i in range(0, len(all_rows), batch_size):
        batch = all_rows[i:i + batch_size]
        cur = conn.executemany(
            "INSERT OR IGNORE INTO rates (ts, exchange, coin, rate_raw, rate_ann, interval_h) VALUES (?,?,?,?,?,?)",
            batch,
        )
        inserted += cur.rowcount
    conn.commit()
    conn.close()

    print(f"Inserted: {inserted} new rates (skipped {len(all_rows) - inserted} duplicates)")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(backfill())
