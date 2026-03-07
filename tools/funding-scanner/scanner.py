from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx
from beartype import beartype

from config import COINS
from exchanges import ALL_EXCHANGES, Exchange, FundingRate


@dataclass(frozen=True, slots=True)
class Spread:
    coin: str
    long_exchange: str   # exchange where you go long (lower/negative rate)
    short_exchange: str  # exchange where you go short (higher rate)
    long_rate: float     # annualized %
    short_rate: float    # annualized %
    spread: float        # annualized % (short_rate - long_rate)


@beartype
async def fetch_all_rates() -> dict[str, list[FundingRate]]:
    """Fetch funding rates from all exchanges. Returns {coin: [rates]}."""
    rates_by_coin: dict[str, list[FundingRate]] = {c: [] for c in COINS}

    async with httpx.AsyncClient(timeout=15.0) as client:
        tasks = [_safe_fetch(ex, client) for ex in ALL_EXCHANGES]
        results = await asyncio.gather(*tasks)

    for exchange_rates in results:
        for fr in exchange_rates:
            if fr.coin in rates_by_coin:
                rates_by_coin[fr.coin].append(fr)

    return rates_by_coin


@beartype
async def _safe_fetch(exchange: Exchange, client: httpx.AsyncClient) -> list[FundingRate]:  # type: ignore[type-arg]
    """Fetch with error handling — never crash the whole scan."""
    try:
        return await exchange.fetch_funding_rates(client)
    except Exception as e:
        print(f"  [{exchange.name}] error: {e}")
        return []


@beartype
def calculate_spreads(rates_by_coin: dict[str, list[FundingRate]]) -> list[Spread]:
    """For each coin, find the best long/short pair with max spread."""
    spreads: list[Spread] = []

    for coin, rates in rates_by_coin.items():
        if len(rates) < 2:
            continue

        # Find min rate (long side) and max rate (short side)
        sorted_rates = sorted(rates, key=lambda r: r.rate_ann)
        lowest = sorted_rates[0]
        highest = sorted_rates[-1]

        spread_val = highest.rate_ann - lowest.rate_ann
        if spread_val > 0:
            spreads.append(Spread(
                coin=coin,
                long_exchange=lowest.exchange,
                short_exchange=highest.exchange,
                long_rate=lowest.rate_ann,
                short_rate=highest.rate_ann,
                spread=spread_val,
            ))

    return sorted(spreads, key=lambda s: s.spread, reverse=True)


@beartype
def format_report(spreads: list[Spread], rates_by_coin: dict[str, list[FundingRate]]) -> str:
    """Format human-readable report."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("FUNDING RATE SCANNER — SPREAD REPORT")
    lines.append("=" * 70)
    lines.append("")

    # Count active exchanges
    active_exchanges: set[str] = set()
    total_rates = 0
    for rates in rates_by_coin.values():
        for r in rates:
            active_exchanges.add(r.exchange)
            total_rates += 1
    lines.append(f"Exchanges: {len(active_exchanges)} active | Rates: {total_rates} total")
    lines.append("")

    # Top spreads table
    lines.append(f"{'Coin':<6} {'Long (buy)':<22} {'Short (sell)':<22} {'Spread':>10}")
    lines.append("-" * 62)

    for s in spreads:
        long_str = f"{s.long_exchange}({s.long_rate:+.1f}%)"
        short_str = f"{s.short_exchange}({s.short_rate:+.1f}%)"
        lines.append(f"{s.coin:<6} {long_str:<22} {short_str:<22} {s.spread:>9.1f}%")

    lines.append("")

    # Per-exchange breakdown
    lines.append("=" * 70)
    lines.append("PER-EXCHANGE RATES (annualized %)")
    lines.append("=" * 70)
    lines.append("")

    for coin in COINS:
        rates = rates_by_coin.get(coin, [])
        if not rates:
            continue
        rate_strs = [f"{r.exchange}:{r.rate_ann:+.1f}%" for r in sorted(rates, key=lambda r: r.rate_ann)]
        lines.append(f"{coin:<6} {' | '.join(rate_strs)}")

    return "\n".join(lines)
