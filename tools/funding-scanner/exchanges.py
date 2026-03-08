from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import httpx
from beartype import beartype

from config import ANN_1H, ANN_8H, COINS

_KUCOIN_SYMBOL_MAP: dict[str, str] = {"BTC": "XBT"}
_USER_AGENT = {"User-Agent": "Mozilla/5.0"}


@beartype
def _kucoin_symbol(coin: str) -> str:
    return f"{_KUCOIN_SYMBOL_MAP.get(coin, coin)}USDTM"


@beartype
def _annualizer(interval_h: int) -> int:
    if interval_h <= 1:
        return ANN_1H
    if interval_h == 8:
        return ANN_8H
    return int(365 * 24 / interval_h)


@beartype
def _to_float(value: str | float | int | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


@beartype
def _to_int(value: str | int | None) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


@dataclass(frozen=True, slots=True)
class FundingRate:
    exchange: str
    coin: str
    rate: float
    rate_ann: float
    interval_h: int
    price: float | None = None
    next_funding_ts: int | None = None


@runtime_checkable
class Exchange(Protocol):
    name: str
    exchange_type: str

    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]: ...


class Binance:
    name = "BINANCE"
    exchange_type = "CEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        premium_resp = await client.get(
            "https://fapi.binance.com/fapi/v1/premiumIndex",
            headers=_USER_AGENT,
        )
        premium_resp.raise_for_status()
        funding_info_resp = await client.get(
            "https://fapi.binance.com/fapi/v1/fundingInfo",
            headers=_USER_AGENT,
        )
        funding_info_resp.raise_for_status()

        interval_by_symbol = {
            item["symbol"]: int(item.get("fundingIntervalHours", 8))
            for item in funding_info_resp.json()
        }

        results: list[FundingRate] = []
        for item in premium_resp.json():
            symbol = item["symbol"]
            for coin in COINS:
                if symbol != f"{coin}USDT":
                    continue
                interval_h = interval_by_symbol.get(symbol, 8)
                rate = float(item["lastFundingRate"])
                results.append(FundingRate(
                    exchange=self.name,
                    coin=coin,
                    rate=rate,
                    rate_ann=rate * _annualizer(interval_h) * 100,
                    interval_h=interval_h,
                    price=_to_float(item.get("markPrice")),
                    next_funding_ts=_to_int(item.get("nextFundingTime")),
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
            headers=_USER_AGENT,
        )
        resp.raise_for_status()
        results: list[FundingRate] = []
        for item in resp.json()["result"]["list"]:
            symbol = item["symbol"]
            for coin in COINS:
                if symbol != f"{coin}USDT":
                    continue
                interval_h = int(item.get("fundingIntervalHour", "8"))
                rate = float(item.get("fundingRate", "0"))
                results.append(FundingRate(
                    exchange=self.name,
                    coin=coin,
                    rate=rate,
                    rate_ann=rate * _annualizer(interval_h) * 100,
                    interval_h=interval_h,
                    price=_to_float(item.get("markPrice") or item.get("lastPrice")),
                    next_funding_ts=_to_int(item.get("nextFundingTime")),
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
            rate_resp = await client.get(
                "https://www.okx.com/api/v5/public/funding-rate",
                params={"instId": inst_id},
                headers=_USER_AGENT,
            )
            if rate_resp.status_code != 200:
                continue
            rate_data = rate_resp.json().get("data", [])
            if not rate_data:
                continue

            mark_resp = await client.get(
                "https://www.okx.com/api/v5/public/mark-price",
                params={"instType": "SWAP", "instId": inst_id},
                headers=_USER_AGENT,
            )
            mark_price: float | None = None
            if mark_resp.status_code == 200:
                mark_data = mark_resp.json().get("data", [])
                if mark_data:
                    mark_price = _to_float(mark_data[0].get("markPx"))

            data = rate_data[0]
            rate = float(data["fundingRate"])
            results.append(FundingRate(
                exchange=self.name,
                coin=coin,
                rate=rate,
                rate_ann=rate * ANN_8H * 100,
                interval_h=8,
                price=mark_price,
                next_funding_ts=_to_int(data.get("fundingTime")),
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
                f"https://api-futures.kucoin.com/api/v1/contracts/{sym}",
                headers=_USER_AGENT,
            )
            if resp.status_code != 200:
                continue
            data = resp.json().get("data")
            if not data:
                continue
            granularity_ms = data.get("currentFundingRateGranularity") or data.get("fundingRateGranularity") or 28_800_000
            interval_h = max(int(granularity_ms) // 3_600_000, 1)
            rate = float(data.get("fundingFeeRate", 0))
            results.append(FundingRate(
                exchange=self.name,
                coin=coin,
                rate=rate,
                rate_ann=rate * _annualizer(interval_h) * 100,
                interval_h=interval_h,
                price=_to_float(data.get("markPrice")),
                next_funding_ts=_to_int(data.get("nextFundingRateDateTime")),
            ))
        return results


class Bitget:
    name = "BITGET"
    exchange_type = "CEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        results: list[FundingRate] = []
        for coin in COINS:
            fund_resp = await client.get(
                "https://api.bitget.com/api/v2/mix/market/current-fund-rate",
                params={"symbol": f"{coin}USDT", "productType": "usdt-futures"},
                headers=_USER_AGENT,
            )
            ticker_resp = await client.get(
                "https://api.bitget.com/api/v2/mix/market/ticker",
                params={"symbol": f"{coin}USDT", "productType": "usdt-futures"},
                headers=_USER_AGENT,
            )
            if fund_resp.status_code != 200:
                continue
            fund_data = fund_resp.json().get("data", [])
            if not fund_data:
                continue
            ticker_data = ticker_resp.json().get("data", []) if ticker_resp.status_code == 200 else []
            ticker = ticker_data[0] if ticker_data else {}
            item = fund_data[0]
            interval_h = int(item.get("fundingRateInterval", "8"))
            rate = float(item.get("fundingRate", "0"))
            results.append(FundingRate(
                exchange=self.name,
                coin=coin,
                rate=rate,
                rate_ann=rate * _annualizer(interval_h) * 100,
                interval_h=interval_h,
                price=_to_float(ticker.get("markPrice") or ticker.get("lastPr")),
                next_funding_ts=_to_int(item.get("nextUpdate")),
            ))
        return results


class Gate:
    name = "GATE"
    exchange_type = "CEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        resp = await client.get(
            "https://api.gateio.ws/api/v4/futures/usdt/tickers",
            headers=_USER_AGENT,
        )
        resp.raise_for_status()
        results: list[FundingRate] = []
        for item in resp.json():
            contract = item.get("contract", "")
            for coin in COINS:
                if contract != f"{coin}_USDT":
                    continue
                rate = float(item.get("funding_rate", "0"))
                results.append(FundingRate(
                    exchange=self.name,
                    coin=coin,
                    rate=rate,
                    rate_ann=rate * ANN_8H * 100,
                    interval_h=8,
                    price=_to_float(item.get("mark_price") or item.get("last")),
                ))
                break
        return results


class MEXC:
    name = "MEXC"
    exchange_type = "CEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        resp = await client.get(
            "https://futures.mexc.com/api/v1/contract/ticker",
            headers=_USER_AGENT,
        )
        resp.raise_for_status()
        payload = resp.json().get("data", [])
        if isinstance(payload, dict):
            payload = [payload]

        results: list[FundingRate] = []
        for item in payload:
            symbol = item.get("symbol", "")
            for coin in COINS:
                if symbol != f"{coin}_USDT":
                    continue
                rate = float(item.get("fundingRate", "0"))
                results.append(FundingRate(
                    exchange=self.name,
                    coin=coin,
                    rate=rate,
                    rate_ann=rate * ANN_8H * 100,
                    interval_h=8,
                    price=_to_float(item.get("fairPrice") or item.get("lastPrice")),
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
            headers=_USER_AGENT,
        )
        resp.raise_for_status()
        meta, ctxs = resp.json()
        universe = meta["universe"] if isinstance(meta, dict) else meta
        results: list[FundingRate] = []
        for asset_meta, ctx in zip(universe, ctxs):
            coin = asset_meta["name"]
            if coin not in COINS:
                continue
            rate = float(ctx["funding"])
            results.append(FundingRate(
                exchange=self.name,
                coin=coin,
                rate=rate,
                rate_ann=rate * ANN_1H * 100,
                interval_h=1,
                price=_to_float(ctx.get("markPx") or ctx.get("midPx") or ctx.get("oraclePx")),
            ))
        return results


class Paradex:
    name = "PARADEX"
    exchange_type = "DEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        results: list[FundingRate] = []
        for coin in COINS:
            market = f"{coin}-USD-PERP"
            funding_resp = await client.get(
                "https://api.prod.paradex.trade/v1/funding/data",
                params={"market": market, "page_size": 1},
                headers=_USER_AGENT,
            )
            summary_resp = await client.get(
                "https://api.prod.paradex.trade/v1/markets/summary",
                params={"market": market},
                headers=_USER_AGENT,
            )
            if funding_resp.status_code != 200:
                continue
            funding_data = funding_resp.json().get("results", [])
            if not funding_data:
                continue
            summary_data = summary_resp.json().get("results", []) if summary_resp.status_code == 200 else []
            summary = summary_data[0] if summary_data else {}
            item = funding_data[0]
            interval_h = int(item.get("funding_period_hours", 8))
            rate = float(item.get("funding_rate", "0"))
            created_at = _to_int(item.get("created_at"))
            next_funding_ts = created_at + interval_h * 3600 * 1000 if created_at else None
            results.append(FundingRate(
                exchange=self.name,
                coin=coin,
                rate=rate,
                rate_ann=rate * _annualizer(interval_h) * 100,
                interval_h=interval_h,
                price=_to_float(summary.get("mark_price") or summary.get("last_traded_price")),
                next_funding_ts=next_funding_ts,
            ))
        return results


class EdgeX:
    name = "EDGEX"
    exchange_type = "DEX"

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
        for contract_id, coin in self._CONTRACT_MAP.items():
            if coin not in COINS:
                continue
            resp = await client.get(
                "https://pro.edgex.exchange/api/v1/public/funding/getLatestFundingRate",
                params={"contractId": contract_id},
                headers=_USER_AGENT,
            )
            if resp.status_code != 200:
                continue
            data = resp.json().get("data", [])
            if not data:
                continue
            item = data[0]
            interval_h = max(int(item.get("fundingRateIntervalMin", 480)) // 60, 1)
            # EdgeX exposes both the last settled rate and the next forecast.
            # The reference panel tracks the forecast for the upcoming payment.
            rate = float(item.get("forecastFundingRate") or item.get("fundingRate") or "0")
            funding_time = _to_int(item.get("fundingTime"))
            next_funding_ts = funding_time + interval_h * 3600 * 1000 if funding_time else None
            results.append(FundingRate(
                exchange=self.name,
                coin=coin,
                rate=rate,
                rate_ann=rate * _annualizer(interval_h) * 100,
                interval_h=interval_h,
                price=_to_float(item.get("markPrice") or item.get("oraclePrice")),
                next_funding_ts=next_funding_ts,
            ))
        return results


class Pacifica:
    name = "PACIFICA"
    exchange_type = "DEX"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        resp = await client.get(
            "https://api.pacifica.fi/api/v1/info/prices",
            headers=_USER_AGENT,
        )
        if resp.status_code != 200:
            return []
        data = resp.json().get("data", [])
        results: list[FundingRate] = []
        for item in data:
            symbol = item.get("symbol", "")
            if symbol not in COINS:
                continue
            # Pacifica publishes both the settled hourly funding and the next estimate.
            # The reference panel compares venues on the upcoming payment.
            rate = float(item.get("next_funding") or item.get("funding") or "0")
            results.append(FundingRate(
                exchange=self.name,
                coin=symbol,
                rate=rate,
                rate_ann=rate * ANN_1H * 100,
                interval_h=1,
                price=_to_float(item.get("mark") or item.get("mid") or item.get("oracle")),
            ))
        return results


class Extended:
    name = "EXTENDED"
    exchange_type = "DEX"

    _BASE = "https://api.starknet.extended.exchange/api/v1"

    @beartype
    async def fetch_funding_rates(self, client: httpx.AsyncClient) -> list[FundingRate]:
        results: list[FundingRate] = []
        for coin in COINS:
            resp = await client.get(
                f"{self._BASE}/info/markets/{coin}-USD/stats",
                headers=_USER_AGENT,
            )
            if resp.status_code != 200:
                continue
            item = resp.json().get("data", {})
            if not item:
                continue
            rate = float(item.get("fundingRate", "0"))
            results.append(FundingRate(
                exchange=self.name,
                coin=coin,
                rate=rate,
                rate_ann=rate * ANN_1H * 100,
                interval_h=1,
                price=_to_float(item.get("markPrice") or item.get("indexPrice")),
                next_funding_ts=_to_int(item.get("nextFundingRate")),
            ))
        return results


ALL_EXCHANGES: list[Exchange] = [
    Binance(),
    Bybit(),
    OKX(),
    KuCoin(),
    Bitget(),
    Gate(),
    MEXC(),
    Hyperliquid(),
    Paradex(),
    EdgeX(),
    Pacifica(),
    Extended(),
]
