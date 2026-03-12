from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import httpx
from beartype import beartype


@dataclass(slots=True)
class ProductCandidate:
    ean: str
    name: str
    maker: str = ""
    id_name: int | None = None


@dataclass(slots=True)
class InventoryItem:
    ean: str
    name: str
    maker: str
    qty: int
    updated_at: str = ""


class PharmOrderError(RuntimeError):
    pass


class PharmOrderNotFound(PharmOrderError):
    pass


class PharmOrderAPI:
    @beartype
    def __init__(self, base_url: str, api_key: str, timeout: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.timeout = timeout

    @beartype
    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=self.timeout)

    @beartype
    def _params(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        params: dict[str, str] = {}
        if self.api_key:
            params["key"] = self.api_key
        if extra:
            params.update(extra)
        return params

    @beartype
    def _query_variants(self, query: str) -> list[str]:
        cleaned = " ".join(query.strip().split())
        if not cleaned:
            return []

        variants: list[str] = [cleaned]
        tokens = cleaned.split()
        last = tokens[-1]

        def push(value: str) -> None:
            normalized = " ".join(value.strip().split())
            if normalized and normalized not in variants:
                variants.append(normalized)

        if len(last) >= 6 and last[-1] in "аеиоуыэюяё":
            tokens_copy = tokens[:]
            tokens_copy[-1] = last[:-1]
            push(" ".join(tokens_copy))

        if len(last) >= 7 and re.fullmatch(r"[а-яё-]+", last, flags=re.IGNORECASE):
            push(" ".join(tokens[:-1] + [last[: max(6, len(last) - 2)]]))
            push(" ".join(tokens[:-1] + [last[: max(6, len(last) - 1)]]))

        if len(cleaned) >= 7:
            push(cleaned[: max(6, len(cleaned) - 1)])

        return variants

    @beartype
    def search_product(self, query: str, limit: int = 3) -> list[ProductCandidate]:
        query = query.strip()
        if not query:
            return []

        deduped: list[ProductCandidate] = []
        seen: set[str] = set()
        with self._client() as client:
            for variant in self._query_variants(query):
                response = client.get("/api/search", params=self._params({"q": variant}))
                response.raise_for_status()
                payload = response.json()
                results = payload.get("results", [])
                for item in results:
                    ean = str(item.get("ean", "")).strip()
                    if not ean or ean in seen:
                        continue
                    seen.add(ean)
                    offers = item.get("offers") or []
                    maker = str(item.get("maker", "")).strip()
                    if not maker and offers:
                        maker = str(offers[0].get("maker", "")).strip()
                    deduped.append(
                        ProductCandidate(
                            ean=ean,
                            name=str(item.get("name", "")).strip(),
                            maker=maker,
                            id_name=int(item["id_name"]) if item.get("id_name") is not None else None,
                        )
                    )
                    if len(deduped) >= limit:
                        return deduped
                if deduped:
                    return deduped
        return deduped

    @beartype
    def lookup_product(self, ean: str) -> ProductCandidate:
        with self._client() as client:
            response = client.get("/api/lookup", params=self._params({"ean": ean}))
            response.raise_for_status()
            payload = response.json()
        if not payload.get("found"):
            raise PharmOrderNotFound(f"Product not found for EAN {ean}")
        offers = payload.get("offers") or []
        maker = str(payload.get("maker", "")).strip()
        if not maker and offers:
            maker = str(offers[0].get("maker", "")).strip()
        return ProductCandidate(
            ean=str(payload.get("lookup_ean") or payload.get("ean") or ean).strip(),
            name=str(payload.get("name", "")).strip(),
            maker=maker,
            id_name=int(payload["id_name"]) if payload.get("id_name") is not None else None,
        )

    @beartype
    def get_inventory(self, ean: str) -> InventoryItem | None:
        with self._client() as client:
            response = client.get(f"/api/inventory/{ean}", params=self._params())
            if response.status_code == 404:
                return None
            response.raise_for_status()
            payload = response.json()
        return InventoryItem(
            ean=str(payload.get("ean", "")).strip(),
            name=str(payload.get("name", "")).strip(),
            maker=str(payload.get("maker", "")).strip(),
            qty=int(payload.get("qty", 0)),
            updated_at=str(payload.get("updated_at", "")).strip(),
        )

    @beartype
    def get_product(self, id_name: int) -> dict[str, Any]:
        with self._client() as client:
            response = client.get("/api/product", params=self._params({"id_name": str(id_name)}))
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise PharmOrderError(f"Unexpected /api/product payload for id_name={id_name}")
        return payload

    @beartype
    def history_search_count(self, query: str) -> int:
        query = query.strip()
        if not query:
            return 0
        with self._client() as client:
            response = client.get("/api/history/search", params=self._params({"q": query}))
            response.raise_for_status()
            payload = response.json()
        return int(payload.get("count", 0) or 0)

    @beartype
    def set_inventory(self, ean: str, name: str, maker: str, qty: int) -> InventoryItem:
        return self._inventory_write("/api/inventory/set", ean, name, maker, qty)

    @beartype
    def add_inventory(self, ean: str, name: str, maker: str, qty: int) -> InventoryItem:
        return self._inventory_write("/api/inventory/add", ean, name, maker, qty)

    @beartype
    def subtract_inventory(self, ean: str, name: str, maker: str, qty: int) -> InventoryItem:
        return self._inventory_write("/api/inventory/subtract", ean, name, maker, qty)

    @beartype
    def delete_inventory(self, ean: str) -> bool:
        with self._client() as client:
            response = client.delete(f"/api/inventory/{ean}", params=self._params())
            if response.status_code == 404:
                return False
            response.raise_for_status()
        return True

    @beartype
    def _inventory_write(self, path: str, ean: str, name: str, maker: str, qty: int) -> InventoryItem:
        body = {
            "ean": ean,
            "name": name,
            "maker": maker,
            "qty": int(qty),
        }
        with self._client() as client:
            response = client.post(
                path,
                params=self._params(),
                json=body,
            )
            response.raise_for_status()
            payload = response.json()
        item = payload.get("item") or {}
        return InventoryItem(
            ean=str(item.get("ean", ean)).strip(),
            name=str(item.get("name", name)).strip(),
            maker=str(item.get("maker", maker)).strip(),
            qty=int(item.get("qty", qty)),
            updated_at=str(item.get("updated_at", "")).strip(),
        )
