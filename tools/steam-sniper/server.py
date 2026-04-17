"""FastAPI server for Steam Sniper dashboard.

Provides REST API for watchlist CRUD, search, price history, and portfolio stats.
Background collector fetches lis-skins prices every 5 minutes.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from beartype import beartype
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import ijson
from pydantic import BaseModel

from build_image_cache import ensure_image_cache, load_image_cache
import db
from category import classify

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger("sniper.server")

# --- Constants ---

LISSKINS_URL = "https://lis-skins.com/market_export_json/csgo.json"
LISSKINS_FULL_URL = "https://lis-skins.com/market_export_json/api_csgo_full.json"
CBR_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
COLLECT_INTERVAL = 300  # 5 minutes
LISTINGS_CACHE_TTL = 900  # 15 minutes
ITEM_DETAIL_CACHE_DIR = Path(__file__).parent / "data" / "item_detail_cache"
MSK = timezone(timedelta(hours=3))

# --- Module-level state ---

_prices: dict[str, dict] = {}  # {name_lower: {name, price, url, count}}
_category_counts: dict[str, int] = {}  # {category: count} for sidebar
_image_cache: dict[str, str] = {}  # {name_lower: image_url} from ByMykel API
_usd_rub: float = 0.0
_last_update: str = ""
_collector_task: asyncio.Task | None = None


# Lis-skins uses their own USD/RUB rate ≈ CBR × 1.034 (3.4% markup).
# All prices in lis-skins JSON are USD — multiply by this to match website RUB.
# Lis-skins internal USD/RUB rate ≈ CBR × 1.0314.
# Calibrated 2026-04-13: Souvenir AWP DL FT $47619.87 = 3780541.47₽ → exact 1.031409
LIS_SKINS_RATE_MULTIPLIER = 1.0314


# --- Sync helpers (run via asyncio.to_thread) ---


def _fetch_lis_skins() -> list[dict]:
    """Fetch full lis-skins catalog. Returns raw list."""
    req = urllib.request.Request(
        LISSKINS_URL, headers={"User-Agent": "SteamSniper/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_full_listings() -> list[dict]:
    """Yield the raw lis-skins full-listing stream."""
    req = urllib.request.Request(
        LISSKINS_FULL_URL, headers={"User-Agent": "SteamSniper/1.0"}
    )
    return urllib.request.urlopen(req, timeout=120)


_WEAR_RE = re.compile(r"\s*\((Factory New|Minimal Wear|Field-Tested|Well-Worn|Battle-Scarred)\)$")

# Russian → English CS2 term dictionary for local search
_RU_EN_DICT: dict[str, str] = {
    # Skins / patterns
    "изумруд": "emerald", "изумрудный": "emerald",
    "кровавая": "crimson", "кровавая паутина": "crimson web",
    "градиент": "fade", "затухание": "fade",
    "мрамор": "marble fade", "мраморный": "marble",
    "волны": "doppler", "допплер": "doppler",
    "зверь": "hyper beast", "гиперзверь": "hyper beast",
    "азимов": "asiimov", "азимов": "asiimov",
    "вулкан": "vulcan",
    "водяной": "water elemental",
    "нео-нуар": "neo-noir", "неонуар": "neo-noir",
    "поверхностная закалка": "case hardened", "закалка": "case hardened",
    "убийство": "slaughter", "резня": "slaughter",
    "тигр": "tiger tooth", "зуб тигра": "tiger tooth",
    "ночь": "night", "ночной": "night",
    "лор": "lore", "знание": "lore",
    "дракон": "dragon", "драконлор": "dragon lore",
    "огонь": "fire", "пламя": "blaze",
    "красная линия": "redline",
    "неоновая революция": "neon revolution",
    "пустынный орёл": "desert eagle", "дигл": "desert eagle",
    "поток": "flow",
    "точечная сетка": "dot",
    "сафари": "safari",
    "городская маска": "urban masked",
    "синяя сталь": "blue steel",
    "ржавчина": "rust",
    "кислотный": "acid",
    "смерч": "whirlwind",
    # Weapons
    "калаш": "ak-47", "калашников": "ak-47",
    "автомат": "ak-47",
    "ак": "ak-47",
    "аска": "m4a1-s", "м4": "m4a",
    "авп": "awp", "авпшка": "awp",
    "дигл": "desert eagle", "пустынный": "desert",
    "пистолет": "pistol",
    "нож": "knife",
    "штык": "bayonet", "штык-нож": "bayonet",
    "бабочка": "butterfly",
    "керамбит": "karambit",
    "тычковый": "push",
    "складной": "flip",
    "охотничий": "huntsman",
    "перчатки": "gloves",
    "водительские": "driver gloves",
    "спортивные": "sport gloves",
    "мотоциклетные": "moto gloves",
    "специалиста": "specialist gloves",
    "гидра": "hydra",
    # Types
    "стикер": "sticker", "наклейка": "sticker",
    "кейс": "case", "ящик": "case",
    "ключ": "key",
    "граффити": "graffiti",
    "музыка": "music kit",
    "нашивка": "patch",
    "агент": "agent",
    "контейнер": "case",
    # Wear
    "прямо с завода": "factory new",
    "немного поношенное": "minimal wear",
    "после полевых": "field-tested",
    "поношенное": "well-worn",
    "закалённое в боях": "battle-scarred",
}


def _translate_ru_to_en(query: str) -> str:
    """Translate Russian CS2 query to English using dictionary.

    Tries longest match first, then individual words.
    Returns English query or empty string if no match.
    """
    q = query.strip().lower()

    # Try full query match first
    if q in _RU_EN_DICT:
        return _RU_EN_DICT[q]

    # Try multi-word combinations (longest first)
    words = q.split()
    result_parts: list[str] = []
    i = 0
    matched = False
    while i < len(words):
        found = False
        # Try 3-word, 2-word, then 1-word
        for length in (3, 2, 1):
            if i + length <= len(words):
                phrase = " ".join(words[i : i + length])
                if phrase in _RU_EN_DICT:
                    result_parts.append(_RU_EN_DICT[phrase])
                    i += length
                    found = True
                    matched = True
                    break
        if not found:
            # Unknown word — skip it
            i += 1

    return " ".join(result_parts) if matched else ""


def _get_item_image(name: str) -> str:
    """Lookup image from cache. Falls back to base name without wear."""
    key = name.lower()
    # Exact match (stickers, cases, agents — no wear suffix)
    img = _image_cache.get(key)
    if img:
        return img
    # Strip wear suffix: "AK-47 | Redline (Field-Tested)" -> "AK-47 | Redline"
    # Remove last parenthetical with wear name
    idx = key.rfind(" (")
    if idx > 0:
        base = key[:idx]
        img2 = _image_cache.get(base, "")
        if img2:
            return img2
    return ""


def _load_image_cache_from_file() -> dict[str, str]:
    """Load pre-built image cache from data/image_cache.json."""
    return load_image_cache()


def _fix_mojibake(text: str) -> str:
    """Recover UTF-8 Cyrillic that was mis-decoded as latin-1/cp1252."""
    if not text or not any(marker in text for marker in ("Ð", "Ñ", "â", "€", "™")):
        return text

    for encoding in ("latin-1", "cp1252"):
        try:
            decoded = text.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if any("\u0400" <= ch <= "\u04ff" for ch in decoded):
            return decoded
    return text


def _match_catalog_name(query: str) -> str | None:
    """Return canonical lis-skins name for an unambiguous search query."""
    words = query.lower().split()
    if not words:
        return None

    matches = [
        item["name"]
        for name_lower, item in _prices.items()
        if all(word in name_lower for word in words)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _normalize_spaces(text: str) -> str:
    """Collapse only real whitespace, without touching mojibake control bytes."""
    return re.sub(r"[ \t\r\n\f\v]+", " ", text).strip()


def _item_cache_path(name: str) -> Path:
    digest = hashlib.sha1(name.lower().encode("utf-8")).hexdigest()
    return ITEM_DETAIL_CACHE_DIR / f"{digest}.json"


def _load_item_cache(name: str) -> dict | None:
    path = _item_cache_path(name)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(payload["cached_at"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return None
    if datetime.now(MSK) - cached_at > timedelta(seconds=LISTINGS_CACHE_TTL):
        return None
    return payload


def _save_item_cache(name: str, payload: dict) -> None:
    ITEM_DETAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _item_cache_path(name).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def _num(v):
    """Coerce ijson numerics (Decimal) and strings into JSON-safe primitives."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    return int(f) if f.is_integer() else f


def _slim_listing(it: dict) -> dict:
    stickers_raw = it.get("stickers") or []
    stickers = [
        {
            "name": s.get("name"),
            "image": s.get("image"),
            "wear": _num(s.get("wear")),
            "slot": _num(s.get("slot")),
        }
        for s in stickers_raw
    ]
    return {
        "id": _num(it.get("id")),
        "price": float(it["price"]),
        "float": str(it["item_float"]) if it.get("item_float") is not None else None,
        "paint_index": _num(it.get("item_paint_index")),
        "paint_seed": _num(it.get("item_paint_seed")),
        "stickers": stickers,
        "unlock_at": it.get("unlock_at"),
        "item_link": it.get("item_link"),
    }


def _fetch_item_listings(name: str, *, store_limit: int = 100) -> dict:
    """Stream lis-skins full export and keep only one item's listings in memory."""
    target = name.lower()
    matched: list[dict] = []
    total = 0

    with _fetch_full_listings() as resp:
        for it in ijson.items(resp, "items.item"):
            item_name = it.get("name")
            price = it.get("price")
            if not item_name or price is None or item_name.lower() != target:
                continue
            total += 1
            if len(matched) < store_limit:
                matched.append(_slim_listing(it))

    matched.sort(key=lambda x: x["price"])
    payload = {
        "cached_at": datetime.now(MSK).isoformat(timespec="seconds"),
        "total": total,
        "listings": matched,
    }
    _save_item_cache(name, payload)
    return payload


def _get_item_listings(name: str, *, limit: int) -> tuple[list[dict], int, str]:
    cached = _load_item_cache(name)
    if cached is None:
        cached = _fetch_item_listings(name)
    return cached["listings"][:limit], cached["total"], cached["cached_at"]


def _fetch_usd_rub() -> float:
    """Fetch USD/RUB rate from CBR."""
    req = urllib.request.Request(
        CBR_URL, headers={"User-Agent": "SteamSniper/1.0"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return float(data["Valute"]["USD"]["Value"])


def _lis_rate() -> float:
    """USD/RUB rate matching lis-skins website prices."""
    return _usd_rub * LIS_SKINS_RATE_MULTIPLIER


def _calc_trend(name_lower: str) -> dict:
    """Calculate 2-week price trend. Returns {direction, pct}."""
    history = db.get_price_history(name_lower, "30d")
    if len(history) < 2:
        return {"direction": "flat", "pct": 0.0}

    # Compare last price vs price ~14 days ago (or earliest available)
    latest = history[-1]["price_usd"]
    # Find price closest to 14 days ago
    mid_idx = max(0, len(history) // 2)
    old = history[mid_idx]["price_usd"]

    if old <= 0:
        return {"direction": "flat", "pct": 0.0}

    pct = round(((latest - old) / old) * 100, 1)
    if pct > 1:
        direction = "up"
    elif pct < -1:
        direction = "down"
    else:
        direction = "flat"
    return {"direction": direction, "pct": pct}


# --- Collector ---


async def _load_image_cache() -> None:
    """Ensure image cache exists locally and load it into memory."""
    global _image_cache
    try:
        _image_cache = await asyncio.to_thread(ensure_image_cache)
        logger.info("Image cache ready: %d items", len(_image_cache))
    except Exception as e:
        _image_cache = load_image_cache()
        if _image_cache:
            logger.warning(
                "Image cache refresh failed, using local cache (%d items): %s",
                len(_image_cache),
                e,
            )
        else:
            logger.warning("Image cache unavailable: %s", e)


async def _collect_once() -> None:
    """Fetch prices + rate, snapshot watched items, prune old history."""
    global _prices, _category_counts, _image_cache, _usd_rub, _last_update

    try:
        items = await asyncio.to_thread(_fetch_lis_skins)
        _prices = {item["name"].lower(): item for item in items}
    except Exception as e:
        logger.error("Failed to fetch lis-skins: %s", e)
        return

    # Rebuild category counts for catalog sidebar
    counts: dict[str, int] = {}
    for item in _prices.values():
        cat = classify(item["name"])
        counts[cat] = counts.get(cat, 0) + 1
    _category_counts = counts


    try:
        rate = await asyncio.to_thread(_fetch_usd_rub)
        _usd_rub = rate
        db.save_rate("USD", rate)
    except Exception as e:
        logger.warning("Failed to fetch USD/RUB: %s", e)
        cached = db.get_cached_rate("USD")
        if cached:
            _usd_rub = cached

    # Snapshot watched items
    watched = db.get_watchlist_names()
    snapshots = [
        (name, _prices[name]["price"])
        for name in watched
        if name in _prices
    ]
    if snapshots:
        db.insert_price_snapshots(snapshots)

    db.prune_old_history(90)
    _last_update = datetime.now(MSK).isoformat(timespec="seconds")
    logger.info(
        "Collected %d items, %d snapshots", len(_prices), len(snapshots)
    )


async def _collector_loop() -> None:
    """Background loop: collect every COLLECT_INTERVAL seconds."""
    while True:
        await asyncio.sleep(COLLECT_INTERVAL)
        try:
            await _collect_once()
        except Exception as e:
            logger.error("Collector loop error: %s", e)


# --- Lifespan ---


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Startup: init db, first collect, start loop. Shutdown: cancel loop."""
    global _collector_task, _image_cache
    db.init_db()
    await _load_image_cache()
    await _collect_once()
    _collector_task = asyncio.create_task(_collector_loop())
    yield
    if _collector_task:
        _collector_task.cancel()


# --- App ---

app = FastAPI(title="Steam Sniper", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


# --- Service worker (root scope for PWA) ---


@app.get("/sw.js")
@beartype
def serve_service_worker() -> FileResponse:
    """Serve service worker from root scope for PWA."""
    return FileResponse(
        Path(__file__).parent / "static" / "sw.js",
        media_type="application/javascript",
    )


# --- Pydantic models ---


class WatchlistAddRequest(BaseModel):
    name: str
    type: str  # "buy" or "sell"
    target_rub: float
    qty: int = 1
    display_name: str | None = None
    category: str | None = None
    image_url: str | None = None


class ListItemRequest(BaseModel):
    user: str
    item_name: str
    list_type: str  # "favorite" or "wishlist"


# CS2 rarity → color mapping (Russian category names from Steam API)
_RARITY_COLORS: dict[str, str] = {
    "ширпотреб": "#b0c3d9",
    "промышленное": "#5e98d9",
    "армейское": "#4b69ff",
    "запрещённое": "#8847ff",
    "засекреченное": "#d32ce6",
    "тайное": "#eb4b4b",
    "контрабанда": "#e4ae39",
    "экстраординарного": "#ffd700",
    "stattrak": "#cf6a32",
    "★": "#ffd700",
}


def _rarity_color(category: str | None) -> str:
    """Extract rarity color from category string like 'Винтовка, Запрещённое'."""
    if not category:
        return "#b0c3d9"
    cat_lower = category.lower()
    for keyword, color in _RARITY_COLORS.items():
        if keyword in cat_lower:
            return color
    return "#b0c3d9"


# --- Endpoints ---


@app.get("/")
@beartype
def serve_dashboard() -> FileResponse:
    """Serve dashboard.html at root."""
    return FileResponse(Path(__file__).parent / "dashboard.html")


@app.get("/api/watchlist")
@beartype
def get_watchlist() -> dict:
    """Return watchlist with live prices and deltas (API-02)."""
    wl = db.get_watchlist()
    result: dict[str, list[dict] | float | int | str] = {
        "buy": [],
        "sell": [],
        "usd_rub": round(_lis_rate(), 2),
        "total_items_lis": len(_prices),
        "updated_at": _last_update,
    }

    for type_key in ("buy", "sell"):
        for entry in wl[type_key]:
            name_lower = entry["name_lower"]
            item_data = _prices.get(name_lower)

            current_price_usd = item_data["price"] if item_data else None
            current_price_rub = (
                current_price_usd * _lis_rate() if current_price_usd else None
            )
            added_price_usd = entry.get("added_price_usd", 0) or 0

            delta_pct = None
            if current_price_usd and added_price_usd > 0:
                delta_pct = round(
                    ((current_price_usd - added_price_usd) / added_price_usd)
                    * 100,
                    2,
                )

            # Trend: compare current vs 2 weeks ago
            trend = _calc_trend(name_lower)

            # Added price in RUB (entry price)
            added_price_rub = (
                round(added_price_usd * _lis_rate(), 2)
                if added_price_usd > 0 else None
            )

            # Steam Market URL
            steam_url = (
                "https://steamcommunity.com/market/listings/730/"
                + urllib.parse.quote(entry["name"])
                if entry["name"] else None
            )

            enriched = {
                "name": entry["name"],
                "display_name": entry.get("display_name") or entry["name"],
                "category": entry.get("category"),
                "type": entry["type"],
                "target_rub": entry["target_rub"],
                "current_price_usd": current_price_usd,
                "current_price_rub": (
                    round(current_price_rub, 2) if current_price_rub else None
                ),
                "added_price_usd": added_price_usd,
                "added_price_rub": added_price_rub,
                "delta_pct": delta_pct,
                "trend": trend,
                "qty": entry.get("qty", 1),
                "count": item_data["count"] if item_data else None,
                "url": item_data["url"] if item_data else None,
                "steam_url": steam_url,
                "image_url": entry.get("image_url") or _get_item_image(entry["name"]),
                "rarity_color": _rarity_color(entry.get("category")),
                "added_at": entry.get("added_at", ""),
            }
            result[type_key].append(enriched)  # type: ignore[union-attr]

    return result


@app.post("/api/watchlist", status_code=201)
@beartype
def add_to_watchlist(body: WatchlistAddRequest) -> dict:
    """Add item to watchlist (API-03)."""
    item_data = _prices.get(body.name.lower())
    added_price_usd = item_data["price"] if item_data else 0.0

    db.upsert_item(
        name=body.name,
        type_=body.type,
        target_rub=body.target_rub,
        added_price_usd=added_price_usd,
        added_at=datetime.now(MSK).isoformat(),
        qty=body.qty,
        display_name=body.display_name,
        category=body.category,
        image_url=body.image_url or _get_item_image(body.name),
    )
    return {"ok": True, "name": body.name}


@app.delete("/api/watchlist/{name}")
@beartype
def delete_from_watchlist(name: str) -> JSONResponse:
    """Remove item from watchlist (API-04)."""
    count = db.remove_item(name)
    if count == 0:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse({"ok": True, "removed": count})


# --- Russian search via Steam Market API ---

_STEAM_SEARCH_URL = (
    "https://steamcommunity.com/market/search/render/"
    "?query={q}&appid=730&norender=1&count=50&l=russian"
)
_STEAM_IMG = "https://community.fastly.steamstatic.com/economy/image/"


def _steam_search(q: str) -> list[dict]:
    """Query Steam Market with pagination, return enriched results."""
    from urllib.parse import quote

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36",
        "Accept": "application/json",
    }
    results: list[dict] = []
    # Steam returns ~10 per page despite count=50; paginate to cover all
    for start in range(0, 100, 10):
        url = _STEAM_SEARCH_URL.format(q=quote(q)) + f"&start={start}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            batch = data.get("results", [])
            if not batch:
                break
            for r in batch:
                ad = r.get("asset_description", {})
                icon = ad.get("icon_url", "")
                results.append({
                    "hash_name": r.get("hash_name", ""),
                    "name_ru": r.get("name", ""),
                    "type_ru": ad.get("type", ""),
                    "image": f"{_STEAM_IMG}{icon}/128fx128f" if icon else "",
                    "name_color": ad.get("name_color", ""),
                })
            total = data.get("total_count", 0)
            if start + len(batch) >= total:
                break
        except Exception as e:
            logger.warning("Steam search page %d failed: %s", start, e)
            break
    return results


def _resolve_item_name(name: str) -> str:
    """Normalize list item names to canonical lis-skins English names."""
    raw = name.strip()
    if not raw:
        return name

    for exact_candidate in (raw, _normalize_spaces(raw)):
        item = _prices.get(exact_candidate.lower())
        if item:
            return item["name"]

    candidates = [raw]
    fixed = _fix_mojibake(raw)
    if fixed != raw:
        candidates.append(fixed)

    for candidate in candidates:
        candidate = _normalize_spaces(candidate)
        item = _prices.get(candidate.lower())
        if item:
            return item["name"]

        if any("\u0400" <= c <= "\u04ff" for c in candidate):
            for steam_item in _steam_search(candidate):
                lis_item = _prices.get(steam_item["hash_name"].lower())
                if lis_item:
                    return lis_item["name"]

            en_query = _translate_ru_to_en(candidate)
            if en_query:
                matched = _match_catalog_name(en_query)
                if matched:
                    return matched

    return raw


@app.get("/api/search")
@beartype
def search_items(q: str = Query(min_length=2)) -> dict:
    """Search lis-skins catalog (API-05). Supports Russian via Steam Market."""
    has_cyrillic = any("\u0400" <= c <= "\u04ff" for c in q)

    out: list[dict] = []

    if has_cyrillic:
        # Steam Market → get EN names + images + RU names
        steam_items = _steam_search(q)
        seen: set[str] = set()
        for si in steam_items:
            lis_item = _prices.get(si["hash_name"].lower())
            key = si["hash_name"].lower()
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "name": si["hash_name"],
                "name_ru": si["name_ru"],
                "type_ru": si["type_ru"],
                "image": si["image"] or _get_item_image(si["hash_name"]),
                "name_color": si["name_color"],
                "price": lis_item["price"] if lis_item else None,
                "price_rub": (
                    round(lis_item["price"] * _lis_rate(), 2)
                    if lis_item else None
                ),
                "count": lis_item["count"] if lis_item else 0,
                "url": lis_item["url"] if lis_item else "",
                "on_lis_skins": lis_item is not None,
            })
    else:
        # English — direct match in lis-skins cache
        words = q.lower().split()
        matches = []
        for name_lower, item in _prices.items():
            if all(w in name_lower for w in words):
                matches.append(item)
        matches.sort(key=lambda x: x["price"])
        for item in matches[:24]:
            out.append({
                "name": item["name"],
                "name_ru": "",
                "type_ru": "",
                "image": _get_item_image(item["name"]),
                "name_color": "",
                "price": item["price"],
                "price_rub": round(item["price"] * _lis_rate(), 2),
                "count": item.get("count", 0),
                "url": item.get("url", ""),
                "on_lis_skins": True,
            })

    return {"results": out[:24], "query": q}


# Valid sort options for catalog
_CATALOG_SORTS = {"name_asc", "name_desc", "price_asc", "price_desc", "count_desc"}


@app.get("/api/catalog")
@beartype
def get_catalog(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    category: str | None = Query(default=None),
    sort: str = Query(default="name_asc"),
    q: str | None = Query(default=None),
) -> dict:
    """Browse full catalog with pagination, filtering, sorting, and search."""
    rate = _lis_rate()

    # Build enriched list from in-memory prices
    items: list[dict] = []
    for item in _prices.values():
        cat = classify(item["name"])

        # Category filter
        if category and cat != category:
            continue

        item_dict = {
            "name": item["name"],
            "category": cat,
            "price_usd": item["price"],
            "price_rub": round(item["price"] * rate, 2),
            "count": item.get("count", 0),
            "url": item.get("url", ""),
            "image": _get_item_image(item["name"]),
            "available": item.get("count", 0) > 0,
        }
        # Add trend for case items (used by cases tab)
        if cat == "case":
            item_dict["trend"] = _calc_trend(item["name"].lower())
        items.append(item_dict)

    # Search filter
    if q:
        has_cyrillic = any("\u0400" <= c <= "\u04ff" for c in q)
        if has_cyrillic:
            # Translate Russian terms to English, then search locally
            en_query = _translate_ru_to_en(q.lower())
            if en_query:
                words = en_query.lower().split()
                items = [
                    it for it in items
                    if all(w in it["name"].lower() for w in words)
                ]
            else:
                # No translation found — fallback to Steam Market API
                steam_results = _steam_search(q)
                en_names = {sr["hash_name"].lower() for sr in steam_results}
                items = [it for it in items if it["name"].lower() in en_names]
        else:
            # English — direct substring match
            words = q.lower().split()
            items = [
                it for it in items
                if all(w in it["name"].lower() for w in words)
            ]

    # Sort
    if sort not in _CATALOG_SORTS:
        sort = "name_asc"

    sort_keys: dict[str, tuple] = {
        "name_asc": (lambda x: x["name"].lower(), False),
        "name_desc": (lambda x: x["name"].lower(), True),
        "price_asc": (lambda x: x["price_usd"], False),
        "price_desc": (lambda x: x["price_usd"], True),
        "count_desc": (lambda x: x["count"], True),
    }
    key_fn, reverse = sort_keys[sort]
    items.sort(key=key_fn, reverse=reverse)

    total = len(items)
    page = items[offset : offset + limit]

    return {
        "items": page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "categories": _category_counts,
    }


@app.get("/api/item/{name}")
@beartype
def get_item_detail(name: str, limit: int = Query(default=20, ge=1, le=100)) -> dict:
    """Return detailed listings for a single skin — lis-skins item page mirror.

    Body: summary (aggregated price/count/image/category) + up to `limit`
    individual listings sorted by price (float, stickers, paint index).
    """
    rate = _lis_rate()
    key = name.lower()

    summary_src = _prices.get(key, {})
    summary = {
        "name": summary_src.get("name", name),
        "url": summary_src.get("url", ""),
        "count": summary_src.get("count", 0),
        "price_usd": summary_src.get("price"),
        "price_rub": (
            round(summary_src["price"] * rate, 2)
            if summary_src.get("price") is not None else None
        ),
        "image": _get_item_image(summary_src.get("name", name)),
        "category": classify(summary_src.get("name", name)) if summary_src else "",
        "rarity_color": _rarity_color(summary_src.get("category")),
    }

    try:
        listings_raw, total_available, listings_updated = _get_item_listings(name, limit=limit)
    except Exception as e:
        logger.warning("Item detail stream fetch failed for %s: %s", name, e)
        listings_raw, total_available, listings_updated = [], 0, ""
    listings = [
        {
            "id": lst["id"],
            "price_usd": lst["price"],
            "price_rub": round(lst["price"] * rate, 2),
            "float": lst.get("float"),
            "paint_index": lst.get("paint_index"),
            "paint_seed": lst.get("paint_seed"),
            "stickers": lst.get("stickers") or [],
            "unlock_at": lst.get("unlock_at"),
            "item_link": lst.get("item_link"),
        }
        for lst in listings_raw
    ]

    return {
        "summary": summary,
        "listings": listings,
        "listings_total": total_available,
        "listings_updated": listings_updated,
    }


@app.get("/api/history/{name}")
@beartype
def get_history(name: str, tf: str = "7d") -> dict:
    """Return price history for charting (API-06)."""
    points = db.get_price_history(name, tf)
    return {"name": name, "tf": tf, "points": points}


@app.get("/api/debug")
def debug_info() -> dict:
    """Debug endpoint for image cache status."""
    return {"image_cache_size": len(_image_cache), "prices_size": len(_prices), "rate": _lis_rate()}


@app.get("/api/stats")
@beartype
def get_stats() -> dict:
    """Return portfolio stats (API-07)."""
    prices_map = {name: item["price"] for name, item in _prices.items()}
    stats = db.get_portfolio_stats(prices_map, rate=_lis_rate())
    stats["usd_rub"] = round(_lis_rate(), 2)
    stats["total_lis_skins"] = len(_prices)
    stats["last_update"] = _last_update
    return stats


@app.get("/api/alerts")
@beartype
def get_alerts(limit: int = Query(default=20, le=100)) -> dict:
    """Return recent alerts for activity feed (UI-05)."""
    alerts = db.get_recent_alerts(limit)
    return {"alerts": alerts}


# --- Personal Lists (favorites / wishlist) ---


@app.post("/api/lists", status_code=201, response_model=None)
@beartype
def add_list_item_endpoint(body: ListItemRequest) -> JSONResponse | dict:
    """Add item to user's personal list (LIST-02)."""
    if body.list_type not in ("favorite", "wishlist"):
        return JSONResponse({"error": "list_type must be 'favorite' or 'wishlist'"}, status_code=400)
    resolved_name = _resolve_item_name(body.item_name)
    db.add_list_item(user_id=body.user, item_name=resolved_name, list_type=body.list_type)
    return {"ok": True, "item_name": resolved_name}


@app.delete("/api/lists")
@beartype
def remove_list_item_endpoint(body: ListItemRequest) -> dict:
    """Remove item from user's personal list (LIST-02)."""
    count = db.remove_list_item(user_id=body.user, item_name=body.item_name, list_type=body.list_type)
    if count == 0:
        resolved_name = _resolve_item_name(body.item_name)
        if resolved_name != body.item_name:
            count = db.remove_list_item(
                user_id=body.user,
                item_name=resolved_name,
                list_type=body.list_type,
            )
    return {"ok": True, "removed": count}


@app.get("/api/lists")
@beartype
def get_list_items_endpoint(user: str = Query(...), type: str | None = Query(default=None)) -> dict:
    """Return user's list items, optionally filtered by type (LIST-03)."""
    items = db.get_list_items(user_id=user, list_type=type)
    enriched: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        original_name = item["item_name"]
        name = _resolve_item_name(original_name)
        if name != original_name:
            db.rename_list_item(
                user_id=user,
                old_name=original_name,
                new_name=name,
                list_type=item["list_type"],
            )
            item = {**item, "item_name": name}

        dedupe_key = (item["list_type"], name.lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        item_data = _prices.get(name.lower())
        enriched.append({
            **item,
            "image": _get_item_image(name),
            "price_rub": (
                round(item_data["price"] * _lis_rate(), 2)
                if item_data else None
            ),
            "count": item_data["count"] if item_data else None,
            "category": classify(name),
            "url": item_data["url"] if item_data else "",
        })
    return {"items": enriched}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8100, reload=False)
