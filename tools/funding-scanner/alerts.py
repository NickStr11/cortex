from __future__ import annotations

import os

import httpx
from beartype import beartype

TG_BOT_TOKEN: str = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID: str = os.environ.get("TG_CHAT_ID", "691773226")


@beartype
async def send_telegram(text: str) -> bool:
    """Send message via Telegram bot. Returns True on success."""
    if not TG_BOT_TOKEN:
        print("  [TG] No TG_BOT_TOKEN set, skipping alert")
        return False

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json={
            "chat_id": TG_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        })
        if resp.status_code == 200:
            return True
        print(f"  [TG] Error {resp.status_code}: {resp.text[:200]}")
        return False


@beartype
def format_alert_spread(coin: str, spread: float, long_ex: str, long_rate: float,
                         short_ex: str, short_rate: float) -> str:
    return (
        f"<b>💰 {coin} spread {spread:.1f}%/yr</b>\n"
        f"Long: {long_ex} ({long_rate:+.1f}%)\n"
        f"Short: {short_ex} ({short_rate:+.1f}%)"
    )


@beartype
def format_alert_trend(coin: str, direction: str, spread: float,
                        long_ex: str, short_ex: str) -> str:
    arrow = "📈" if direction == "up" else "📉"
    label = "РАСТЁТ" if direction == "up" else "ПАДАЕТ"
    return (
        f"{arrow} <b>{coin}: спред {label}</b> (3+ снапшотов)\n"
        f"Текущий спред: {spread:.1f}%/yr\n"
        f"Пара: {long_ex} ↔ {short_ex}"
    )


@beartype
def format_scan_summary(active_exchanges: int, total_rates: int,
                         top_spreads: list[tuple[str, float]],
                         trends: list[tuple[str, str, float]]) -> str:
    lines = [f"<b>📊 Funding Scanner</b> | {active_exchanges} бирж, {total_rates} рейтов\n"]

    lines.append("<b>Top-5 спредов:</b>")
    for coin, spread in top_spreads[:5]:
        lines.append(f"  {coin}: {spread:.1f}%/yr")

    if trends:
        lines.append("\n<b>Тренды:</b>")
        for coin, direction, spread in trends:
            arrow = "↑" if direction == "up" else "↓"
            lines.append(f"  {arrow} {coin}: {spread:.1f}%/yr")

    return "\n".join(lines)
