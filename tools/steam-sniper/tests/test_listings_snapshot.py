from __future__ import annotations

import sqlite3
from pathlib import Path

from listings_snapshot import get_item_listings, snapshot_status


def _seed_snapshot(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE meta (
            key TEXT PRIMARY KEY,
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
    conn.execute(
        "INSERT INTO meta(key, value) VALUES (?, ?)",
        ("built_at", "2026-04-17T12:00:00"),
    )
    conn.execute(
        """
        INSERT INTO listings(
            id, name_lower, name, price, float_value, paint_index, paint_seed,
            stickers_json, name_tag, unlock_at, item_link
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            7,
            "awp | asiimov (field-tested)",
            "AWP | Asiimov (Field-Tested)",
            25.4,
            0.1534,
            279,
            901,
            '[{"name":"Crown","image":"https://cdn.steamstatic.com/apps/730/icons/econ/stickers/crown.png","wear":0.02,"slot":0},{"name":"Lil\' Monster","image":"https://cdn.steamstatic.com/apps/730/icons/econ/keychains/lil_monster.png","wear":0,"slot":null}]',
            "test tag",
            None,
            "steam://inspect/123",
        ),
    )
    conn.commit()
    conn.close()


def test_snapshot_status_missing(tmp_path: Path) -> None:
    path = tmp_path / "missing.db"
    status = snapshot_status(path)
    assert status == {"available": False, "built_at": "", "size_bytes": 0}


def test_get_item_listings_reads_sqlite_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "listings_snapshot.db"
    _seed_snapshot(path)

    listings, total, built_at = get_item_listings(
        "AWP | Asiimov (Field-Tested)",
        limit=20,
        path=path,
    )

    assert total == 1
    assert built_at == "2026-04-17T12:00:00"
    assert listings[0]["id"] == 7
    assert listings[0]["price"] == 25.4
    assert listings[0]["float"] == 0.1534
    assert listings[0]["name_tag"] == "test tag"
    assert listings[0]["item_link"] == "steam://inspect/123"
    assert listings[0]["stickers"][0]["name"] == "Crown"
    assert listings[0]["keychains"][0]["name"] == "Lil' Monster"


def test_get_item_listings_supports_filters(tmp_path: Path) -> None:
    path = tmp_path / "listings_snapshot.db"
    _seed_snapshot(path)

    listings, total, _ = get_item_listings(
        "AWP | Asiimov (Field-Tested)",
        limit=20,
        float_min=0.1,
        float_max=0.2,
        has_stickers="yes",
        has_keychains="yes",
        path=path,
    )

    assert total == 1
    assert len(listings) == 1
