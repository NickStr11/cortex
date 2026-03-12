from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from beartype import beartype
from dbfread import DBF

from history_client import normalize_search_text


@dataclass(slots=True)
class ProductAgg:
    product_key: str
    id_name: int | None
    id_mak: int | None
    name: str
    maker: str
    eans: set[str] = field(default_factory=set)
    offer_count: int = 0
    best_priority: int = 999
    has_pr_all: bool = False

    @property
    def canonical_ean(self) -> str:
        return min(self.eans) if self.eans else ""


@beartype
def clean_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split()).strip()


@beartype
def to_int(value: Any) -> int | None:
    try:
        if value in (None, "", " "):
            return None
        return int(value)
    except Exception:
        return None


@beartype
def normalize_ean(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) == 14 and digits.startswith("0"):
        digits = digits[1:]
    return digits if len(digits) >= 8 else ""


@beartype
def iso_date(value: Any) -> str:
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.isoformat()
    return ""


@beartype
def make_product_key(id_name: int | None, id_mak: int | None, ean: str, name: str, maker: str) -> str:
    if id_name is not None:
        return f"{id_name}:{id_mak or 0}"
    raw = f"{ean}|{clean_text(name)}|{clean_text(maker)}"
    digest = hashlib.md5(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"u:{digest}"


@beartype
def ensure_product(
    products: dict[str, ProductAgg],
    *,
    product_key: str,
    id_name: int | None,
    id_mak: int | None,
    name: str,
    maker: str,
) -> ProductAgg:
    if product_key not in products:
        products[product_key] = ProductAgg(
            product_key=product_key,
            id_name=id_name,
            id_mak=id_mak,
            name=clean_text(name),
            maker=clean_text(maker),
        )
    row = products[product_key]
    if not row.name and name:
        row.name = clean_text(name)
    if not row.maker and maker:
        row.maker = clean_text(maker)
    return row


@beartype
def load_name_refs(sklit_root: Path) -> tuple[dict[int, str], dict[tuple[int, int], str]]:
    names: dict[int, str] = {}
    makers: dict[tuple[int, int], str] = {}

    lsprtov = sklit_root / "lsprtov.dbf"
    lsprtovmak = sklit_root / "lsprtovmak.dbf"

    for rec in DBF(str(lsprtov), load=False, ignore_missing_memofile=True, char_decode_errors="ignore"):
        id_name = to_int(rec.get("ID_NAME"))
        name = clean_text(rec.get("NAME"))
        if id_name is not None and name and id_name not in names:
            names[id_name] = name

    for rec in DBF(str(lsprtovmak), load=False, ignore_missing_memofile=True, char_decode_errors="ignore"):
        id_name = to_int(rec.get("ID_NAME"))
        id_mak = to_int(rec.get("ID_MAK"))
        maker = clean_text(rec.get("MAKER"))
        if id_name is not None and id_mak is not None and maker:
            makers[(id_name, id_mak)] = maker

    return names, makers


@beartype
def build_catalog(
    sklit_root: Path,
    names_by_id: dict[int, str],
    makers_by_ids: dict[tuple[int, int], str],
) -> tuple[dict[str, ProductAgg], list[tuple[str, str, int | None, int | None, str, str, str]]]:
    products: dict[str, ProductAgg] = {}
    aliases: list[tuple[str, str, int | None, int | None, str, str, str]] = []
    alias_seen: set[tuple[str, str, str]] = set()

    pr_all = sklit_root / "pr_all.dbf"
    lspr_ean = sklit_root / "lspr_ean.dbf"

    for rec in DBF(str(pr_all), load=False, ignore_missing_memofile=True, char_decode_errors="ignore"):
        ean = normalize_ean(rec.get("EAN13"))
        id_name = to_int(rec.get("ID_NAME"))
        id_mak = to_int(rec.get("ID_MAK"))
        if not ean:
            continue
        name = clean_text(rec.get("NAME")) or names_by_id.get(id_name or -1, "")
        maker = clean_text(rec.get("MAKER")) or makers_by_ids.get((id_name or -1, id_mak or -1), "")
        key = make_product_key(id_name, id_mak, ean, name, maker)
        row = ensure_product(products, product_key=key, id_name=id_name, id_mak=id_mak, name=name, maker=maker)
        row.eans.add(ean)
        row.offer_count += 1
        row.has_pr_all = True
        if (ean, key, "pr_all") not in alias_seen:
            aliases.append((ean, key, id_name, id_mak, row.name, row.maker, "pr_all"))
            alias_seen.add((ean, key, "pr_all"))

    for rec in DBF(str(lspr_ean), load=False, ignore_missing_memofile=True, char_decode_errors="ignore"):
        ean = normalize_ean(rec.get("EAN13"))
        id_name = to_int(rec.get("ID_NAME"))
        id_mak = to_int(rec.get("ID_MAK"))
        if not ean:
            continue
        name = names_by_id.get(id_name or -1, "")
        maker = makers_by_ids.get((id_name or -1, id_mak or -1), "") or clean_text(rec.get("NAME"))
        key = make_product_key(id_name, id_mak, ean, name, maker)
        row = ensure_product(products, product_key=key, id_name=id_name, id_mak=id_mak, name=name, maker=maker)
        row.eans.add(ean)
        if (ean, key, "lspr_ean") not in alias_seen:
            aliases.append((ean, key, id_name, id_mak, row.name, row.maker, "lspr_ean"))
            alias_seen.add((ean, key, "lspr_ean"))

    return products, aliases


@beartype
def build_alias_indexes(
    products: dict[str, ProductAgg],
    aliases: list[tuple[str, str, int | None, int | None, str, str, str]],
) -> tuple[
    dict[tuple[str, int | None], str],
    dict[str, str | None],
    dict[tuple[str, str], str],
]:
    exact_alias: dict[tuple[str, int | None], str] = {}
    ean_to_keys: dict[str, set[str]] = defaultdict(set)
    name_maker_to_key: dict[tuple[str, str], str] = {}

    for ean, product_key, _id_name, id_mak, _name, _maker, _source in aliases:
        ean_to_keys[ean].add(product_key)
        exact_alias[(ean, id_mak)] = product_key

    ean_unique: dict[str, str | None] = {}
    for ean, keys in ean_to_keys.items():
        ean_unique[ean] = next(iter(keys)) if len(keys) == 1 else None

    for product_key, row in products.items():
        norm_name = normalize_search_text(row.name)
        norm_maker = normalize_search_text(row.maker)
        if norm_name and norm_maker and (norm_name, norm_maker) not in name_maker_to_key:
            name_maker_to_key[(norm_name, norm_maker)] = product_key

    return exact_alias, ean_unique, name_maker_to_key


@beartype
def build_purchase_rows(
    sklit_root: Path,
    products: dict[str, ProductAgg],
    exact_alias: dict[tuple[str, int | None], str],
    ean_unique: dict[str, str | None],
    name_maker_to_key: dict[tuple[str, str], str],
) -> list[tuple[str, str, int | None, int | None, str, str, str, str, str, float, str, str]]:
    rows: list[tuple[str, str, int | None, int | None, str, str, str, str, str, float, str, str]] = []
    ree_tov = sklit_root / "ReeTov.DBF"

    for rec in DBF(str(ree_tov), load=False, ignore_missing_memofile=True, char_decode_errors="ignore"):
        raw_ean = normalize_ean(rec.get("SCAN_CODE")) or normalize_ean(rec.get("GTIN")) or normalize_ean(rec.get("EAN_MAK"))
        id_mak = to_int(rec.get("ID_MAK"))
        raw_name = clean_text(rec.get("TOVAR"))
        raw_maker = clean_text(rec.get("MAKER"))
        supplier = clean_text(rec.get("POST"))
        nakl_date = iso_date(rec.get("NAKL_DATE"))
        nakl_num = clean_text(rec.get("NAKL_NUM"))
        qty = float(rec.get("KOL_VO") or 0)

        product_key = ""
        if raw_ean and (raw_ean, id_mak) in exact_alias:
            product_key = exact_alias[(raw_ean, id_mak)]
        elif raw_ean and ean_unique.get(raw_ean):
            product_key = ean_unique[raw_ean] or ""
        else:
            name_maker_key = (normalize_search_text(raw_name), normalize_search_text(raw_maker))
            product_key = name_maker_to_key.get(name_maker_key, "")

        if product_key and product_key in products:
            product = products[product_key]
            canonical_ean = product.canonical_ean or raw_ean
            canonical_name = product.name or raw_name
            canonical_maker = product.maker or raw_maker
            id_name = product.id_name
            id_mak_resolved = product.id_mak
        else:
            canonical_ean = raw_ean
            canonical_name = raw_name
            canonical_maker = raw_maker
            id_name = None
            id_mak_resolved = id_mak
            product_key = make_product_key(id_name, id_mak_resolved, canonical_ean, canonical_name, canonical_maker)

        search_text = normalize_search_text(f"{canonical_name} {canonical_maker}")
        rows.append(
            (
                product_key,
                canonical_ean,
                id_name,
                id_mak_resolved,
                canonical_name,
                canonical_maker,
                raw_ean,
                supplier,
                nakl_date,
                qty,
                nakl_num,
                search_text,
            )
        )

    return rows


@beartype
def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
DROP TABLE IF EXISTS meta;
DROP TABLE IF EXISTS catalog_products;
DROP TABLE IF EXISTS catalog_aliases;
DROP TABLE IF EXISTS purchase_lines;

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE catalog_products (
    product_key TEXT PRIMARY KEY,
    id_name INTEGER,
    id_mak INTEGER,
    canonical_ean TEXT NOT NULL,
    name TEXT NOT NULL,
    maker TEXT,
    offer_count INTEGER NOT NULL DEFAULT 0,
    best_priority INTEGER NOT NULL DEFAULT 999,
    search_text TEXT NOT NULL
);

CREATE TABLE catalog_aliases (
    ean TEXT NOT NULL,
    product_key TEXT NOT NULL,
    id_name INTEGER,
    id_mak INTEGER,
    name TEXT,
    maker TEXT,
    source TEXT NOT NULL
);

CREATE TABLE purchase_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_key TEXT NOT NULL,
    canonical_ean TEXT NOT NULL,
    id_name INTEGER,
    id_mak INTEGER,
    canonical_name TEXT NOT NULL,
    canonical_maker TEXT,
    raw_ean TEXT,
    supplier TEXT,
    nakl_date TEXT,
    qty REAL NOT NULL DEFAULT 0,
    nakl_num TEXT,
    search_text TEXT NOT NULL
);

CREATE INDEX idx_catalog_products_search ON catalog_products(search_text);
CREATE INDEX idx_catalog_products_ean ON catalog_products(canonical_ean);
CREATE INDEX idx_catalog_products_id_name ON catalog_products(id_name);

CREATE INDEX idx_catalog_aliases_ean ON catalog_aliases(ean);
CREATE INDEX idx_catalog_aliases_product_key ON catalog_aliases(product_key);

CREATE INDEX idx_purchase_lines_search ON purchase_lines(search_text);
CREATE INDEX idx_purchase_lines_date ON purchase_lines(nakl_date);
CREATE INDEX idx_purchase_lines_key ON purchase_lines(product_key);
CREATE INDEX idx_purchase_lines_ean ON purchase_lines(canonical_ean);
"""
    )
    conn.commit()


@beartype
def build_analytics_db(sklit_root: Path, out_path: Path) -> dict[str, Any]:
    names_by_id, makers_by_ids = load_name_refs(sklit_root)
    products, aliases = build_catalog(sklit_root, names_by_id, makers_by_ids)
    exact_alias, ean_unique, name_maker_to_key = build_alias_indexes(products, aliases)
    purchase_rows = build_purchase_rows(sklit_root, products, exact_alias, ean_unique, name_maker_to_key)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    conn = sqlite3.connect(str(out_path))
    try:
        init_db(conn)
        conn.executemany(
            """
INSERT INTO catalog_products (
    product_key, id_name, id_mak, canonical_ean, name, maker, offer_count, best_priority, search_text
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""",
            [
                (
                    product.product_key,
                    product.id_name,
                    product.id_mak,
                    product.canonical_ean,
                    product.name,
                    product.maker,
                    product.offer_count,
                    product.best_priority,
                    normalize_search_text(f"{product.name} {product.maker}"),
                )
                for product in products.values()
                if product.canonical_ean and product.name
            ],
        )
        conn.executemany(
            """
INSERT INTO catalog_aliases (ean, product_key, id_name, id_mak, name, maker, source)
VALUES (?, ?, ?, ?, ?, ?, ?)
""",
            aliases,
        )
        conn.executemany(
            """
INSERT INTO purchase_lines (
    product_key, canonical_ean, id_name, id_mak, canonical_name, canonical_maker,
    raw_ean, supplier, nakl_date, qty, nakl_num, search_text
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""",
            purchase_rows,
        )
        meta = {
            "sklit_root": str(sklit_root),
            "catalog_products": conn.execute("SELECT COUNT(*) FROM catalog_products").fetchone()[0],
            "catalog_aliases": conn.execute("SELECT COUNT(*) FROM catalog_aliases").fetchone()[0],
            "purchase_lines": conn.execute("SELECT COUNT(*) FROM purchase_lines").fetchone()[0],
        }
        conn.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            [(key, json.dumps(value, ensure_ascii=False)) for key, value in meta.items()],
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "sklit_root": str(sklit_root),
        "out_path": str(out_path),
        "catalog_products": len(products),
        "catalog_aliases": len(aliases),
        "purchase_lines": len(purchase_rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build tg-pharma analytics SQLite from local SKLIT DBF files.")
    parser.add_argument(
        "--sklit-root",
        default=r"C:\Users\User\Desktop\SKLIT",
        help="Path to local SKLIT copy",
    )
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent / "data" / "bot_analytics.db"),
        help="Output SQLite path",
    )
    args = parser.parse_args()

    sklit_root = Path(args.sklit_root)
    out_path = Path(args.out)
    result = build_analytics_db(sklit_root, out_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
