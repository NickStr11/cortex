"""Build and query the local item-detail snapshot database."""
from __future__ import annotations

import json
import logging
import sqlite3
import urllib.request
from datetime import datetime
from pathlib import Path

import ijson

logger = logging.getLogger("sniper.listings_snapshot")

LISSKINS_FULL_URL = "https://lis-skins.com/market_export_json/api_csgo_full.json"
SNAPSHOT_DB_PATH = Path(__file__).parent / "data" / "listings_snapshot.db"
USER_AGENT = "SteamSniper/1.0"


def _coerce_num(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    return int(number) if number.is_integer() else number


def _normalize_stickers(stickers: list[dict] | None) -> str:
    if not stickers:
        return "[]"
    payload = []
    for sticker in stickers:
        payload.append(
            {
                "name": sticker.get("name"),
                "image": sticker.get("image"),
                "wear": _coerce_num(sticker.get("wear")),
                "slot": _coerce_num(sticker.get("slot")),
            }
        )
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _listing_row(item: dict) -> tuple:
    return (
        int(_coerce_num(item["id"])),
        item["name"].lower(),
        item["name"],
        float(item["price"]),
        _coerce_num(item.get("item_float")),
        _coerce_num(item.get("item_paint_index")),
        _coerce_num(item.get("item_paint_seed")),
        _normalize_stickers(item.get("stickers")),
        item.get("name_tag"),
        item.get("unlock_at"),
        item.get("item_link"),
    )


def _open_readonly(path: Path = SNAPSHOT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def snapshot_status(path: Path = SNAPSHOT_DB_PATH) -> dict:
    """Return basic snapshot metadata for API/debug responses."""
    if not path.exists():
        return {"available": False, "built_at": "", "size_bytes": 0}

    built_at = ""
    try:
        with _open_readonly(path) as conn:
            row = conn.execute(
                "SELECT value FROM meta WHERE key='built_at'"
            ).fetchone()
            if row:
                built_at = row["value"]
    except sqlite3.Error:
        built_at = ""

    if not built_at:
        built_at = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")

    return {
        "available": True,
        "built_at": built_at,
        "size_bytes": path.stat().st_size,
    }


def _normalize_filter_flag(value: str) -> str:
    normalized = str(value or "all").strip().lower()
    return normalized if normalized in {"all", "yes", "no"} else "all"


def _attachments_sql(flag: str, attachment_path: str) -> tuple[str, list[str]]:
    if flag == "yes":
        return "stickers_json LIKE ?", [f"%{attachment_path}%"]
    if flag == "no":
        return "stickers_json NOT LIKE ?", [f"%{attachment_path}%"]
    return "", []


def _split_attachments(attachments: list[dict]) -> tuple[list[dict], list[dict]]:
    stickers: list[dict] = []
    keychains: list[dict] = []
    for attachment in attachments:
        image = str(attachment.get("image") or "")
        target = keychains if "/econ/keychains/" in image else stickers
        target.append(attachment)
    return stickers, keychains


def get_item_listings(
    name: str,
    limit: int,
    *,
    sort: str = "price_asc",
    float_min: float | None = None,
    float_max: float | None = None,
    has_stickers: str = "all",
    has_keychains: str = "all",
    path: Path = SNAPSHOT_DB_PATH,
) -> tuple[list[dict], int, str]:
    """Read one item's listings from the snapshot DB."""
    status = snapshot_status(path)
    if not status["available"]:
        return [], 0, ""

    sort_key = str(sort or "price_asc").lower()
    if sort_key not in {"price_asc", "price_desc", "float_asc", "float_desc"}:
        sort_key = "price_asc"
    order_sql = {
        "price_asc": "price ASC, id ASC",
        "price_desc": "price DESC, id DESC",
        "float_asc": "CASE WHEN float_value IS NULL THEN 1 ELSE 0 END, float_value ASC, price ASC",
        "float_desc": "CASE WHEN float_value IS NULL THEN 1 ELSE 0 END, float_value DESC, price ASC",
    }[sort_key]

    has_stickers = _normalize_filter_flag(has_stickers)
    has_keychains = _normalize_filter_flag(has_keychains)

    clauses = ["name_lower = ?"]
    params: list[object] = [name.lower()]
    if float_min is not None:
        clauses.append("float_value IS NOT NULL AND float_value >= ?")
        params.append(float(float_min))
    if float_max is not None:
        clauses.append("float_value IS NOT NULL AND float_value <= ?")
        params.append(float(float_max))

    stickers_clause, stickers_params = _attachments_sql(has_stickers, "/econ/stickers/")
    if stickers_clause:
        clauses.append(stickers_clause)
        params.extend(stickers_params)

    keychains_clause, keychains_params = _attachments_sql(has_keychains, "/econ/keychains/")
    if keychains_clause:
        clauses.append(keychains_clause)
        params.extend(keychains_params)

    where_sql = " AND ".join(clauses)

    with _open_readonly(path) as conn:
        rows = conn.execute(
            f"""
            SELECT id, price, float_value, paint_index, paint_seed, stickers_json,
                   name_tag, unlock_at, item_link
            FROM listings
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        total = conn.execute(
            f"SELECT COUNT(*) AS count FROM listings WHERE {where_sql}",
            params,
        ).fetchone()["count"]

    listings = []
    for row in rows:
        attachments = json.loads(row["stickers_json"] or "[]")
        stickers, keychains = _split_attachments(attachments)
        listings.append(
            {
                "id": row["id"],
                "price": row["price"],
                "float": row["float_value"],
                "paint_index": row["paint_index"],
                "paint_seed": row["paint_seed"],
                "stickers": stickers,
                "keychains": keychains,
                "name_tag": row["name_tag"],
                "unlock_at": row["unlock_at"],
                "item_link": row["item_link"],
            }
        )

    return listings, int(total), status["built_at"]


def build_snapshot(
    output_path: Path = SNAPSHOT_DB_PATH,
    *,
    source_url: str = LISSKINS_FULL_URL,
    batch_size: int = 2000,
) -> dict:
    """Download lis-skins full export and rebuild the snapshot DB atomically."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()

    conn = sqlite3.connect(str(tmp_path), timeout=30.0)
    total_rows = 0
    started_at = datetime.now().isoformat(timespec="seconds")

    try:
        conn.executescript(
            """
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            PRAGMA temp_store=MEMORY;
            CREATE TABLE meta (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE listings (
                id            INTEGER PRIMARY KEY,
                name_lower    TEXT NOT NULL,
                name          TEXT NOT NULL,
                price         REAL NOT NULL,
                float_value   REAL,
                paint_index   INTEGER,
                paint_seed    INTEGER,
                stickers_json TEXT NOT NULL,
                name_tag      TEXT,
                unlock_at     TEXT,
                item_link     TEXT
            );
            """
        )

        batch: list[tuple] = []
        req = urllib.request.Request(source_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=300) as resp:
            for item in ijson.items(resp, "items.item", use_float=True):
                item_name = item.get("name")
                price = item.get("price")
                item_id = item.get("id")
                if not item_name or price is None or item_id is None:
                    continue
                batch.append(_listing_row(item))
                total_rows += 1
                if len(batch) >= batch_size:
                    conn.executemany(
                        """
                        INSERT INTO listings(
                            id, name_lower, name, price, float_value, paint_index,
                            paint_seed, stickers_json, name_tag, unlock_at, item_link
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        batch,
                    )
                    batch.clear()

        if batch:
            conn.executemany(
                """
                INSERT INTO listings(
                    id, name_lower, name, price, float_value, paint_index,
                    paint_seed, stickers_json, name_tag, unlock_at, item_link
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                batch,
            )

        conn.executescript(
            """
            CREATE INDEX idx_listings_name_price ON listings(name_lower, price);
            CREATE INDEX idx_listings_name ON listings(name_lower);
            """
        )
        built_at = datetime.now().isoformat(timespec="seconds")
        conn.executemany(
            "INSERT INTO meta(key, value) VALUES (?, ?)",
            [
                ("built_at", built_at),
                ("source_url", source_url),
                ("started_at", started_at),
                ("rows", str(total_rows)),
            ],
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    tmp_path.replace(output_path)
    logger.info("Snapshot built: %s rows -> %s", total_rows, output_path)
    return {
        "rows": total_rows,
        "built_at": built_at,
        "path": str(output_path),
        "size_bytes": output_path.stat().st_size,
    }
