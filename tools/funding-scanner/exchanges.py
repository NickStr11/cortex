from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import httpx
from beartype import beartype

from config import ANN_1H, ANN_8H, COINS

# KuCoin uses XBT instead of BTC
_KUCOIN_SYMBOL_MAP: dict[str, str] = {"BTC": "XBT"}


def _kucoin_symbol(coin: str) -> str:
    return f"{_KUCOIN_SYMBOL_MAP.get(coin, coin)}USDTM"


@dataclass(frozen=True, slots=True)
class FundingRate:
    exchange: str
    coin: str
    rate: float        # raw per-interval rate (e.g. 0.0001)
    rate_ann: float    # annualized %
    interval_h: int    # funding interval in hours (1, 4, 8)


@runtime_checkable
class Exchange(Protocol):
    name: str
    exchange_type: str  # "CEX" or "DEX"

    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]: ...


# ---------------------------------------------------------------------------
# CEX exchanges
# ---------------------------------------------------------------------------

class Binance:
    name = "BINANCE"
    exchange_type = "CEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        resp = await client.get("https://fapi.binance.com/fapi/v1/premiumIndex")
        resp.raise_for_status()
        results: list[FundingRate] = []
        for item in resp.json():
            symbol: str = item["symbol"]
            for coin in COINS:
                if symbol == f"{coin}USDT":
                    rate = float(item["lastFundingRate"])
                    results.append(FundingRate(
                        exchange=self.name, coin=coin,
                        rate=rate, rate_ann=rate * ANN_8H * 100,
                        interval_h=8,
                    ))
                    break
        return results


class Bybit:
    name = "BYBIT"
    exchange_type = "CEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        resp = await client.get(
            "https://api.bybit.com/v5/market/tickers",
            params={"category": "linear"},
        )
        resp.raise_for_status()
        results: list[FundingRate] = []
        for item in resp.json()["result"]["list"]:
            symbol: str = item["symbol"]
            for coin in COINS:
                if symbol == f"{coin}USDT":
                    rate = float(item.get("fundingRate", "0"))
                    results.append(FundingRate(
                        exchange=self.name, coin=coin,
                        rate=rate, rate_ann=rate * ANN_8H * 100,
                        interval_h=8,
                    ))
                    break
        return results


class OKX:
    name = "OKX"
    exchange_type = "CEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        results: list[FundingRate] = []
        for coin in COINS:
            inst_id = f"{coin}-USDT-SWAP"
            resp = await client.get(
                "https://www.okx.com/api/v5/public/funding-rate",
                params={"instId": inst_id},
            )
            if resp.status_code != 200:
                continue
            data = resp.json().get("data", [])
            if not data:
                continue
            rate = float(data[0]["fundingRate"])
            results.append(FundingRate(
                exchange=self.name, coin=coin,
                rate=rate, rate_ann=rate * ANN_8H * 100,
                interval_h=8,
            ))
        return results


class KuCoin:
    name = "KUCOIN"
    exchange_type = "CEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        results: list[FundingRate] = []
        for coin in COINS:
            sym = _kucoin_symbol(coin)
            resp = await client.get(
                f"https://api-futures.kucoin.com/api/v1/funding-rate/{sym}/current",
            )
            if resp.status_code != 200:
                continue
            data = resp.json().get("data")
            if not data:
                continue
            rate = float(data.get("value", 0))
            results.append(FundingRate(
                exchange=self.name, coin=coin,
                rate=rate, rate_ann=rate * ANN_8H * 100,
                interval_h=8,
            ))
        return results


class Bitget:
    name = "BITGET"
    exchange_type = "CEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        results: list[FundingRate] = []
        for coin in COINS:
            resp = await client.get(
                "https://api.bitget.com/api/v2/mix/market/current-fund-rate",
                params={"symbol": f"{coin}USDT", "productType": "usdt-futures"},
            )
            if resp.status_code != 200:
                continue
            data = resp.json().get("data", [])
            if not data:
                continue
            rate = float(data[0].get("fundingRate", "0"))
            # Bitget returns fundingRateInterval in hours (e.g. "8")
            interval_h = int(data[0].get("fundingRateInterval", "8"))
            ann = int(365 * 24 / max(interval_h, 1))
            results.append(FundingRate(
                exchange=self.name, coin=coin,
                rate=rate, rate_ann=rate * ann * 100,
                interval_h=interval_h,
            ))
        return results


class Gate:
    name = "GATE"
    exchange_type = "CEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        # Batch endpoint — all tickers in one call
        resp = await client.get("https://api.gateio.ws/api/v4/futures/usdt/tickers")
        resp.raise_for_status()
        results: list[FundingRate] = []
        for item in resp.json():
            contract: str = item.get("contract", "")
            for coin in COINS:
                if contract == f"{coin}_USDT":
                    rate = float(item.get("funding_rate", "0"))
                    results.append(FundingRate(
                        exchange=self.name, coin=coin,
                        rate=rate, rate_ann=rate * ANN_8H * 100,
                        interval_h=8,
                    ))
                    break
        return results


class MEXC:
    name = "MEXC"
    exchange_type = "CEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        # New domain since Jan 2026
        resp = await client.get("https://futures.mexc.com/api/v1/contract/ticker")
        resp.raise_for_status()
        results: list[FundingRate] = []
        for item in resp.json().get("data", []):
            symbol: str = item.get("symbol", "")
            for coin in COINS:
                if symbol == f"{coin}_USDT":
                    rate = float(item.get("fundingRate", "0"))
                    results.append(FundingRate(
                        exchange=self.name, coin=coin,
                        rate=rate, rate_ann=rate * ANN_8H * 100,
                        interval_h=8,
                    ))
                    break
        return results


class Hyperliquid:
    name = "HYPERLIQUID"
    exchange_type = "DEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        resp = await client.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "metaAndAssetCtxs"},
        )
        resp.raise_for_status()
        data = resp.json()
        meta = data[0]["universe"]
        ctxs = data[1]
        results: list[FundingRate] = []
        for asset_meta, ctx in zip(meta, ctxs):
            coin = asset_meta["name"]
            if coin in COINS:
                rate = float(ctx["funding"])
                results.append(FundingRate(
                    exchange=self.name, coin=coin,
                    rate=rate, rate_ann=rate * ANN_1H * 100,
                    interval_h=1,
                ))
        return results


# ---------------------------------------------------------------------------
# DEX exchanges
# ---------------------------------------------------------------------------

class Paradex:
    name = "PARADEX"
    exchange_type = "DEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        results: list[FundingRate] = []
        for coin in COINS:
            market = f"{coin}-USD-PERP"
            resp = await client.get(
                "https://api.prod.paradex.trade/v1/funding/data",
                params={"market": market, "page_size": 1},
            )
            if resp.status_code != 200:
                continue
            data = resp.json().get("results", [])
            if not data:
                continue
            rate = float(data[0].get("funding_rate", "0"))
            interval = int(data[0].get("funding_period_hours", 8))
            ann = ANN_1H if interval <= 1 else ANN_8H
            results.append(FundingRate(
                exchange=self.name, coin=coin,
                rate=rate, rate_ann=rate * ann * 100,
                interval_h=interval,
            ))
        return results


class EdgeX:
    name = "EDGEX"
    exchange_type = "DEX"

    # EdgeX uses contractId — no public list endpoint, mapped by oracle price.
    _CONTRACT_MAP: dict[str, str] = {
        "10000001": "BTC",
        "10000002": "ETH",
        "10000003": "SOL",
        "10000006": "LINK",
        "10000007": "AVAX",
        "10000009": "XRP",
        "10000017": "TON",
    }

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        results: list[FundingRate] = []
        for cid, coin in self._CONTRACT_MAP.items():
            if coin not in COINS:
                continue
            resp = await client.get(
                "https://pro.edgex.exchange/api/v1/public/funding/getLatestFundingRate",
                params={"contractId": cid},
            )
            if resp.status_code != 200:
                continue
            data = resp.json().get("data", [])
            if not data:
                continue
            rate = float(data[0].get("fundingRate", "0"))
            # EdgeX returns fundingRateIntervalMin (e.g. 240 = 4h)
            interval_min = int(data[0].get("fundingRateIntervalMin", 480))
            interval_h = max(interval_min // 60, 1)
            ann = int(365 * 24 / interval_h)
            results.append(FundingRate(
                exchange=self.name, coin=coin,
                rate=rate, rate_ann=rate * ann * 100,
                interval_h=interval_h,
            ))
        return results


class Pacifica:
    name = "PACIFICA"
    exchange_type = "DEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        # Batch endpoint — returns all markets with funding
        resp = await client.get("https://api.pacifica.fi/api/v1/info/prices")
        if resp.status_code != 200:
            return []
        data = resp.json().get("data", [])
        results: list[FundingRate] = []
        for item in data:
            symbol: str = item.get("symbol", "")
            if symbol in COINS:
                rate = float(item.get("funding", "0"))
                results.append(FundingRate(
                    exchange=self.name, coin=symbol,
                    rate=rate, rate_ann=rate * ANN_1H * 100,
                    interval_h=1,
                ))
        return results


class Extended:
    name = "EXTENDED"
    exchange_type = "DEX"

    # Starknet domain is the active one
    _BASE = "https://api.starknet.extended.exchange/api/v1"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        now_ms = int(time.time() * 1000)
        one_hour_ago = now_ms - 3600_000
        results: list[FundingRate] = []
        for coin in COINS:
            market = f"{coin}-USD"
            resp = await client.get(
                f"{self._BASE}/info/{market}/funding",
                params={"startTime": one_hour_ago, "endTime": now_ms, "limit": 1},
            )
            if resp.status_code != 200:
                continue
            data = resp.json().get("data", [])
            if not data:
                continue
            rate = float(data[-1].get("f", "0"))
            results.append(FundingRate(
                exchange=self.name, coin=coin,
                rate=rate, rate_ann=rate * ANN_1H * 100,
                interval_h=1,
            ))
        return results


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_EXCHANGES: list[Exchange] = [  # type: ignore[type-abstract]
    # CEX
    Binance(),
    Bybit(),
    OKX(),
    KuCoin(),
    Bitget(),
    Gate(),
    MEXC(),
    # DEX
    Hyperliquid(),
    Paradex(),
    EdgeX(),
    Pacifica(),
    Extended(),
]
