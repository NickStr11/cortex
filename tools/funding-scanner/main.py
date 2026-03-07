from __future__ import annotations

import asyncio

from dotenv import load_dotenv

load_dotenv()

from beartype import beartype

from alerts import format_alert_trend, format_scan_summary, send_telegram
from config import ALERT_SPREAD_MIN, COINS, TREND_CONSECUTIVE
from db import detect_spread_trend, get_stats, save_rates, save_spreads
from exchanges import FundingRate
from scanner import calculate_spreads, fetch_all_rates, format_report


@beartype
async def run() -> None:
    print("Fetching funding rates from all exchanges...")
    rates_by_coin = await fetch_all_rates()

    active = sum(1 for v in rates_by_coin.values() if v)
    print(f"Got rates for {active}/{len(rates_by_coin)} coins\n")

    # Flatten and save rates
    all_rates: list[FundingRate] = []
    for coin_rates in rates_by_coin.values():
        all_rates.extend(coin_rates)
    saved_rates = save_rates(all_rates)

    # Calculate and save spreads
    spreads = calculate_spreads(rates_by_coin)
    saved_spreads = save_spreads(spreads)

    # Print report
    report = format_report(spreads, rates_by_coin)
    print(report)

    # Trend detection + alerts
    print("\n" + "=" * 70)
    print("TREND DETECTION")
    print("=" * 70)
    trends: list[tuple[str, str, float]] = []
    for coin in COINS:
        trend = detect_spread_trend(coin, consecutive=TREND_CONSECUTIVE)
        if trend:
            current = next((s for s in spreads if s.coin == coin), None)
            spread_val = current.spread if current else 0.0
            trends.append((coin, trend, spread_val))

            arrow = "^" if trend == "up" else "v"
            label = "GROWING" if trend == "up" else "SHRINKING"
            print(f"  {arrow} {coin}: spread {label} — now {spread_val:.1f}%")

    if not trends:
        print(f"  No trends yet (need {TREND_CONSECUTIVE}+ snapshots)")

    # Stats
    stats = get_stats()
    print(f"\nDB: {stats['rates']} rates, {stats['spreads']} spreads, {stats['snapshots']} snapshots")
    print(f"Saved: {saved_rates} rates + {saved_spreads} spreads")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
