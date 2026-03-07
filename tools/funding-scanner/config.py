from __future__ import annotations

# Top-20 coins to monitor
COINS: list[str] = [
    "BTC", "ETH", "SOL", "XRP", "DOGE",
    "ADA", "LINK", "AVAX", "DOT", "SUI",
    "NEAR", "TON", "APT", "HYPE", "TRX",
    "BCH", "FIL", "XLM", "OP", "ARB",
    "PAXG",
]

# Funding rate fetch interval (seconds)
FETCH_INTERVAL: int = 60 * 60  # 1 hour

# Alert thresholds (annualized %)
ALERT_SPREAD_MIN: float = 15.0  # alert when spread > 15%/yr
TREND_CONSECUTIVE: int = 3       # 3 consecutive increases = trend signal

# Annualization multipliers
# CEX: 8h funding → ×1095 (3×365)
# Hyperliquid: 1h funding → ×8760
# Default: 8h
ANN_8H: int = 1095
ANN_1H: int = 8760
