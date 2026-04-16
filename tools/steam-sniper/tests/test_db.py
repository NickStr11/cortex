"""Tests for db.py — SQLite persistence layer.

RED phase: all tests should FAIL until db.py is implemented.
Covers DATA-01..06, BOT-01..02.
"""
from __future__ import annotations

import json
from pathlib import Path


def test_init_creates_tables(tmp_db: Path) -> None:
    """DATA-01: init_db() creates all 4 tables."""
    import sqlite3

    import db

    db.init_db()

    conn = sqlite3.connect(str(tmp_db))
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()

    assert "watchlist" in tables
    assert "price_history" in tables
    assert "alerts" in tables
    assert "exchange_rates" in tables


def test_wal_mode(tmp_db: Path) -> None:
    """DATA-02: WAL journal mode is active after init."""
    import sqlite3

    import db

    db.init_db()

    conn = sqlite3.connect(str(tmp_db))
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()

    assert mode == "wal"


def test_price_snapshot_insert(tmp_db: Path) -> None:
    """DATA-03: insert_price_snapshots writes rows to price_history."""
    import sqlite3

    import db

    db.init_db()
    db.insert_price_snapshots([("test item", 10.5)])

    conn = sqlite3.connect(str(tmp_db))
    rows = conn.execute(
        "SELECT name_lower, price_usd FROM price_history"
    ).fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0][0] == "test item"
    assert rows[0][1] == 10.5


def test_migration(tmp_db: Path, tmp_path: Path) -> None:
    """DATA-04: migrate_json_to_sqlite imports entries with anomaly detection."""
    import sqlite3

    import db

    db.init_db()

    # Create test watchlist.json with both RUB and USD targets
    test_data = {
        "buy": [
            {
                "name": "AK-47 | Redline",
                "target": 15.0,
                "added_price": 20.0,
                "added_at": "2026-01-01T00:00:00",
            }
        ],
        "sell": [
            {
                "name": "XM1014 | Tranquility",
                "target": 1500.0,
                "added_price": 12.61,
                "added_at": "2026-04-12T19:15:41",
            }
        ],
    }
    json_path = tmp_path / "watchlist.json"
    json_path.write_text(json.dumps(test_data), encoding="utf-8")

    count = db.migrate_json_to_sqlite(json_path, rate=85.0)
    assert count == 2

    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT name_lower, type, target_rub FROM watchlist ORDER BY name_lower"
    ).fetchall()
    conn.close()

    # AK-47: target=15.0 (< 100) -> 15.0 * 85.0 = 1275.0 RUB
    ak_row = [r for r in rows if r["name_lower"] == "ak-47 | redline"][0]
    assert ak_row["target_rub"] == 15.0 * 85.0

    # XM1014: target=1500.0 (> 100) -> stored as-is (already RUB)
    xm_row = [r for r in rows if r["name_lower"] == "xm1014 | tranquility"][0]
    assert xm_row["target_rub"] == 1500.0

    # Idempotency: running again should NOT duplicate rows
    count2 = db.migrate_json_to_sqlite(json_path, rate=85.0)
    assert count2 == 2
    conn = sqlite3.connect(str(tmp_db))
    total = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
    conn.close()
    assert total == 2


def test_pruning(tmp_db: Path) -> None:
    """DATA-05: prune_old_history deletes rows older than N days."""
    import sqlite3

    import db

    db.init_db()

    conn = sqlite3.connect(str(tmp_db))
    # Insert old row (100 days ago)
    conn.execute(
        "INSERT INTO price_history(name_lower, price_usd, ts) "
        "VALUES (?, ?, datetime('now', '-100 days'))",
        ("old item", 5.0),
    )
    # Insert recent row
    conn.execute(
        "INSERT INTO price_history(name_lower, price_usd, ts) "
        "VALUES (?, ?, datetime('now'))",
        ("new item", 10.0),
    )
    conn.commit()
    conn.close()

    pruned = db.prune_old_history(90)
    assert pruned == 1

    conn = sqlite3.connect(str(tmp_db))
    remaining = conn.execute("SELECT name_lower FROM price_history").fetchall()
    conn.close()
    assert len(remaining) == 1
    assert remaining[0][0] == "new item"


def test_exchange_rate_cache(tmp_db: Path) -> None:
    """DATA-06: get_cached_rate returns None on cold start, float after save_rate."""
    import db

    db.init_db()

    assert db.get_cached_rate("USD") is None

    db.save_rate("USD", 85.5)
    rate = db.get_cached_rate("USD")
    assert rate == 85.5


def test_watchlist_crud(tmp_db: Path) -> None:
    """BOT-01: upsert, get, remove watchlist items."""
    import db

    db.init_db()

    db.upsert_item(
        name="AK-47 | Redline",
        type_="buy",
        target_rub=5000.0,
        added_price_usd=15.0,
        added_at="2026-01-01T00:00:00",
        qty=1,
    )

    wl = db.get_watchlist()
    assert "buy" in wl
    assert "sell" in wl
    assert len(wl["buy"]) == 1
    assert wl["buy"][0]["name"] == "AK-47 | Redline"
    assert wl["buy"][0]["target_rub"] == 5000.0

    removed = db.remove_item("AK-47 | Redline")
    assert removed == 1

    wl = db.get_watchlist()
    assert len(wl["buy"]) == 0
    assert len(wl["sell"]) == 0


def test_alert_logging(tmp_db: Path) -> None:
    """BOT-02: log_alert inserts to alerts table."""
    import sqlite3

    import db

    db.init_db()

    db.log_alert(
        name="AWP | Asiimov",
        type_="sell",
        price_usd=25.0,
        target_rub=2000.0,
        message="Price hit target",
    )

    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM alerts").fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0]["name"] == "AWP | Asiimov"
    assert rows[0]["type"] == "sell"
    assert rows[0]["price_usd"] == 25.0
    assert rows[0]["target_rub"] == 2000.0
    assert rows[0]["message"] == "Price hit target"


# --- Tests for user_lists (LIST-01..03) ---


def test_user_lists_table_exists(tmp_db: Path) -> None:
    """LIST-01: init_db() creates user_lists table."""
    import sqlite3

    import db

    db.init_db()

    conn = sqlite3.connect(str(tmp_db))
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()

    assert "user_lists" in tables


def test_add_list_item(tmp_db: Path) -> None:
    """LIST-02: add_list_item inserts a row with correct fields."""
    import sqlite3

    import db

    db.init_db()
    db.add_list_item("lesha", "AK-47 | Redline", "favorite")

    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM user_lists").fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0]["user_id"] == "lesha"
    assert rows[0]["item_name"] == "AK-47 | Redline"
    assert rows[0]["list_type"] == "favorite"
    assert rows[0]["added_at"] is not None


def test_add_list_item_duplicate(tmp_db: Path) -> None:
    """LIST-02: adding same (user_id, item_name, list_type) twice is idempotent."""
    import sqlite3

    import db

    db.init_db()
    db.add_list_item("lesha", "AK-47 | Redline", "favorite")
    db.add_list_item("lesha", "AK-47 | Redline", "favorite")  # no raise

    conn = sqlite3.connect(str(tmp_db))
    total = conn.execute("SELECT COUNT(*) FROM user_lists").fetchone()[0]
    conn.close()

    assert total == 1


def test_remove_list_item(tmp_db: Path) -> None:
    """LIST-02: remove_list_item returns 1 on success, 0 on second call."""
    import db

    db.init_db()
    db.add_list_item("lesha", "AK-47 | Redline", "favorite")

    removed = db.remove_list_item("lesha", "AK-47 | Redline", "favorite")
    assert removed == 1

    removed2 = db.remove_list_item("lesha", "AK-47 | Redline", "favorite")
    assert removed2 == 0


def test_get_list_items_filtered(tmp_db: Path) -> None:
    """LIST-03: get_list_items filters by user_id and list_type."""
    import db

    db.init_db()
    db.add_list_item("lesha", "AK-47 | Redline", "favorite")
    db.add_list_item("lesha", "AWP | Asiimov", "favorite")
    db.add_list_item("lesha", "M4A4 | Howl", "wishlist")
    db.add_list_item("nikita", "Glock | Fade", "favorite")

    lesha_fav = db.get_list_items("lesha", "favorite")
    assert len(lesha_fav) == 2

    lesha_wish = db.get_list_items("lesha", "wishlist")
    assert len(lesha_wish) == 1

    nikita_fav = db.get_list_items("nikita", "favorite")
    assert len(nikita_fav) == 1


def test_get_list_items_all(tmp_db: Path) -> None:
    """LIST-03: get_list_items without type returns all user items."""
    import db

    db.init_db()
    db.add_list_item("lesha", "AK-47 | Redline", "favorite")
    db.add_list_item("lesha", "AWP | Asiimov", "favorite")
    db.add_list_item("lesha", "M4A4 | Howl", "wishlist")

    all_items = db.get_list_items("lesha")
    assert len(all_items) == 3
