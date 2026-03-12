from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from beartype import beartype
from dbfread import DBF

from history_client import normalize_search_text


@dataclass(slots=True)
class AliasRow:
    ean: str
    id_name: int | None
    id_mak: int | None
    canonical_name: str
    canonical_maker: str
    source: str


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
def load_names(sklit_root: Path) -> dict[int, str]:
    table = sklit_root / "lsprtov.dbf"
    names: dict[int, str] = {}
    for record in DBF(str(table), load=False, ignore_missing_memofile=True, char_decode_errors="ignore"):
        id_name = to_int(record.get("ID_NAME"))
        name = clean_text(record.get("NAME"))
        if id_name is not None and name and id_name not in names:
            names[id_name] = name
    return names


@beartype
def load_makers(sklit_root: Path) -> dict[tuple[int, int], str]:
    table = sklit_root / "lsprtovmak.dbf"
    makers: dict[tuple[int, int], str] = {}
    for record in DBF(str(table), load=False, ignore_missing_memofile=True, char_decode_errors="ignore"):
        id_name = to_int(record.get("ID_NAME"))
        id_mak = to_int(record.get("ID_MAK"))
        maker = clean_text(record.get("MAKER"))
        if id_name is None or id_mak is None or not maker:
            continue
        makers[(id_name, id_mak)] = maker
    return makers


@beartype
def build_alias_rows(
    sklit_root: Path,
    names_by_id: dict[int, str],
    makers_by_ids: dict[tuple[int, int], str],
) -> list[AliasRow]:
    rows: list[AliasRow] = []
    seen: set[tuple[str, int | None, int | None, str]] = set()
    table = sklit_root / "lspr_ean.dbf"

    for record in DBF(str(table), load=False, ignore_missing_memofile=True, char_decode_errors="ignore"):
        ean = normalize_ean(record.get("EAN13"))
        id_name = to_int(record.get("ID_NAME"))
        id_mak = to_int(record.get("ID_MAK"))
        if not ean:
            continue
        canonical_name = names_by_id.get(id_name or -1, "") or clean_text(record.get("NAME"))
        canonical_maker = makers_by_ids.get((id_name or -1, id_mak or -1), "") or clean_text(record.get("MAKER"))
        row = AliasRow(
            ean=ean,
            id_name=id_name,
            id_mak=id_mak,
            canonical_name=canonical_name,
            canonical_maker=canonical_maker,
            source="lspr_ean",
        )
        dedupe_key = (row.ean, row.id_name, row.id_mak, row.source)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        rows.append(row)

    return rows


@beartype
def build_ean_history_rows(sklit_root: Path) -> list[tuple[str, int | None, str, str]]:
    table = sklit_root / "HISTEAN.DBF"
    if not table.exists():
        return []

    rows: list[tuple[str, int | None, str, str]] = []
    seen: set[tuple[str, int | None, str]] = set()

    for record in DBF(str(table), load=False, ignore_missing_memofile=True, char_decode_errors="ignore"):
        ean = normalize_ean(record.get("EAN13") or record.get("EAN"))
        id_tov = to_int(record.get("ID_TOV"))
        seen_date = iso_date(record.get("DATE") or record.get("DATA"))
        if not ean:
            continue
        key = (ean, id_tov, seen_date)
        if key in seen:
            continue
        seen.add(key)
        rows.append((ean, id_tov, seen_date, "histean"))

    return rows


@beartype
def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
DROP TABLE IF EXISTS meta;
DROP TABLE IF EXISTS product_names;
DROP TABLE IF EXISTS product_makers;
DROP TABLE IF EXISTS product_aliases;
DROP TABLE IF EXISTS ean_history;

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE product_names (
    id_name INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    search_text TEXT NOT NULL
);

CREATE TABLE product_makers (
    id_name INTEGER NOT NULL,
    id_mak INTEGER NOT NULL,
    maker TEXT NOT NULL,
    search_text TEXT NOT NULL,
    PRIMARY KEY (id_name, id_mak)
);

CREATE TABLE product_aliases (
    ean TEXT NOT NULL,
    id_name INTEGER,
    id_mak INTEGER,
    canonical_name TEXT,
    canonical_maker TEXT,
    source TEXT NOT NULL,
    search_name TEXT NOT NULL,
    search_maker TEXT NOT NULL,
    PRIMARY KEY (ean, id_name, id_mak, source)
);

CREATE TABLE ean_history (
    ean TEXT NOT NULL,
    id_tov INTEGER,
    seen_date TEXT,
    source TEXT NOT NULL
);

CREATE INDEX idx_product_aliases_ean ON product_aliases(ean);
CREATE INDEX idx_product_aliases_id_name ON product_aliases(id_name);
CREATE INDEX idx_product_aliases_name_maker ON product_aliases(search_name, search_maker);
CREATE INDEX idx_ean_history_ean ON ean_history(ean);
CREATE INDEX idx_ean_history_id_tov ON ean_history(id_tov);
"""
    )


@beartype
def populate_db(
    conn: sqlite3.Connection,
    *,
    names_by_id: dict[int, str],
    makers_by_ids: dict[tuple[int, int], str],
    alias_rows: list[AliasRow],
    ean_history_rows: list[tuple[str, int | None, str, str]],
    sklit_root: Path,
) -> None:
    conn.executemany(
        "INSERT INTO product_names (id_name, name, search_text) VALUES (?, ?, ?)",
        [
            (id_name, name, normalize_search_text(name))
            for id_name, name in sorted(names_by_id.items())
            if name
        ],
    )
    conn.executemany(
        "INSERT INTO product_makers (id_name, id_mak, maker, search_text) VALUES (?, ?, ?, ?)",
        [
            (id_name, id_mak, maker, normalize_search_text(maker))
            for (id_name, id_mak), maker in sorted(makers_by_ids.items())
            if maker
        ],
    )
    conn.executemany(
        """
INSERT INTO product_aliases (
    ean,
    id_name,
    id_mak,
    canonical_name,
    canonical_maker,
    source,
    search_name,
    search_maker
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""".strip(),
        [
            (
                row.ean,
                row.id_name,
                row.id_mak,
                row.canonical_name,
                row.canonical_maker,
                row.source,
                normalize_search_text(row.canonical_name),
                normalize_search_text(row.canonical_maker),
            )
            for row in alias_rows
        ],
    )
    if ean_history_rows:
        conn.executemany(
            "INSERT INTO ean_history (ean, id_tov, seen_date, source) VALUES (?, ?, ?, ?)",
            ean_history_rows,
        )

    meta = {
        "schema_version": "1",
        "sklit_root": str(sklit_root),
        "names_count": str(len(names_by_id)),
        "makers_count": str(len(makers_by_ids)),
        "aliases_count": str(len(alias_rows)),
        "ean_history_count": str(len(ean_history_rows)),
    }
    conn.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", sorted(meta.items()))


@beartype
def build_refs_db(sklit_root: Path, output_path: Path, include_ean_history: bool = False) -> dict[str, Any]:
    if not sklit_root.exists():
        raise FileNotFoundError(f"SKLIT root not found: {sklit_root}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    names_by_id = load_names(sklit_root)
    makers_by_ids = load_makers(sklit_root)
    alias_rows = build_alias_rows(sklit_root, names_by_id, makers_by_ids)
    ean_history_rows = build_ean_history_rows(sklit_root) if include_ean_history else []

    conn = sqlite3.connect(str(output_path))
    try:
        init_db(conn)
        populate_db(
            conn,
            names_by_id=names_by_id,
            makers_by_ids=makers_by_ids,
            alias_rows=alias_rows,
            ean_history_rows=ean_history_rows,
            sklit_root=sklit_root,
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "output": str(output_path),
        "names_count": len(names_by_id),
        "makers_count": len(makers_by_ids),
        "aliases_count": len(alias_rows),
        "ean_history_count": len(ean_history_rows),
        "include_ean_history": include_ean_history,
        "size_bytes": output_path.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build small bot_refs.db from SKLIT DBF files")
    parser.add_argument("--sklit-root", default=r"C:\Users\User\Desktop\SKLIT")
    parser.add_argument("--output", default=str(Path(__file__).resolve().parent / "data" / "bot_refs.db"))
    parser.add_argument("--with-ean-history", action="store_true")
    args = parser.parse_args()

    result = build_refs_db(
        sklit_root=Path(args.sklit_root).expanduser(),
        output_path=Path(args.output).expanduser(),
        include_ean_history=bool(args.with_ean_history),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
