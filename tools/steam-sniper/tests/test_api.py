"""Tests for API layer — db query functions + FastAPI endpoints.

Covers API-01..07 requirements.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


# --- DB-level tests for new query functions (Task 1) ---


def test_get_price_history_empty(tmp_db: Path) -> None:
    """No data returns empty list."""
    import db

    db.init_db()
    result = db.get_price_history("nonexistent")
    assert result == []


def test_get_price_history_with_data(tmp_db: Path) -> None:
    """Insert 3 snapshots, verify returned in ASC order."""
    import db

    db.init_db()
    db.insert_price_snapshots([
        ("test item", 10.0),
        ("test item", 12.0),
        ("test item", 11.5),
    ])
    result = db.get_price_history("test item")
    assert len(result) == 3
    prices = [r["price_usd"] for r in result]
    assert prices == [10.0, 12.0, 11.5]
    # Verify ASC order by ts
    timestamps = [r["ts"] for r in result]
    assert timestamps == sorted(timestamps)


def test_get_price_history_timeframe(tmp_db: Path) -> None:
    """Insert snapshots with different timestamps, verify '24h' filter works."""
    import db

    db.init_db()

    conn = sqlite3.connect(str(tmp_db))
    # Insert old snapshot (10 days ago)
    conn.execute(
        "INSERT INTO price_history(name_lower, price_usd, ts) "
        "VALUES (?, ?, datetime('now', '-10 days'))",
        ("test item", 5.0),
    )
    # Insert recent snapshot (1 hour ago)
    conn.execute(
        "INSERT INTO price_history(name_lower, price_usd, ts) "
        "VALUES (?, ?, datetime('now', '-1 hour'))",
        ("test item", 15.0),
    )
    conn.commit()
    conn.close()

    # 24h should return only the recent one
    result_24h = db.get_price_history("test item", "24h")
    assert len(result_24h) == 1
    assert result_24h[0]["price_usd"] == 15.0

    # 30d should return both
    result_30d = db.get_price_history("test item", "30d")
    assert len(result_30d) == 2

    # all should return both
    result_all = db.get_price_history("test item", "all")
    assert len(result_all) == 2


def test_get_portfolio_stats(tmp_db: Path) -> None:
    """Insert 2 items, pass prices dict, verify totals."""
    import db

    db.init_db()

    # Save a rate first
    db.save_rate("USD", 80.0)

    # Add two items
    db.upsert_item("Item A", "buy", 500.0, 5.0, "2026-01-01T00:00:00", qty=2)
    db.upsert_item("Item B", "sell", 1000.0, 10.0, "2026-01-01T00:00:00", qty=1)

    prices = {"item a": 6.0, "item b": 12.0}
    stats = db.get_portfolio_stats(prices)

    assert stats["total_items"] == 2
    # total_value_rub = (6.0 * 80 * 2) + (12.0 * 80 * 1) = 960 + 960 = 1920
    assert stats["total_value_rub"] == 1920.0
    # total_added_rub = (5.0 * 80 * 2) + (10.0 * 80 * 1) = 800 + 800 = 1600
    assert stats["total_added_rub"] == 1600.0
    # delta_pct = ((1920 - 1600) / 1600) * 100 = 20.0
    assert stats["delta_pct"] == 20.0


def test_get_recent_alerts(tmp_db: Path) -> None:
    """Log 2 alerts with different timestamps, verify DESC order and limit."""
    import db

    db.init_db()

    # Insert alerts with explicit different timestamps for reliable ordering
    conn = sqlite3.connect(str(tmp_db))
    conn.execute(
        "INSERT INTO alerts(name, type, price_usd, target_rub, ts, message) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("Item A", "buy", 5.0, 400.0, "2026-04-12 10:00:00", "Alert 1"),
    )
    conn.execute(
        "INSERT INTO alerts(name, type, price_usd, target_rub, ts, message) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("Item B", "sell", 10.0, 900.0, "2026-04-12 12:00:00", "Alert 2"),
    )
    conn.commit()
    conn.close()

    alerts = db.get_recent_alerts(limit=10)
    assert len(alerts) == 2
    # DESC order: Alert 2 (later timestamp) first
    assert alerts[0]["name"] == "Item B"
    assert alerts[1]["name"] == "Item A"

    # Test limit
    alerts_limited = db.get_recent_alerts(limit=1)
    assert len(alerts_limited) == 1
    assert alerts_limited[0]["name"] == "Item B"


# --- Integration tests for FastAPI endpoints (Task 3) ---


@pytest.fixture
def client(tmp_db: Path):
    """TestClient with isolated temp database and mocked prices."""
    import db
    import server

    db.init_db()

    # Mock module-level state to avoid real network calls
    server._prices = {
        "kilowatt case": {
            "name": "Kilowatt Case",
            "price": 0.78,
            "url": "https://lis-skins.com/market/csgo/kilowatt-case/",
            "count": 1500,
        },
        "awp | asiimov (field-tested)": {
            "name": "AWP | Asiimov (Field-Tested)",
            "price": 25.5,
            "url": "https://lis-skins.com/market/csgo/awp-asiimov-ft/",
            "count": 42,
        },
    }
    server._usd_rub = 83.0
    server._last_update = "2026-04-12T18:00:00"

    # Disable lifespan (no real collector)
    async def noop():
        pass

    _orig_collect = server._collect_once
    server._collect_once = noop

    from fastapi.testclient import TestClient

    with TestClient(server.app) as c:
        yield c

    # Restore
    server._collect_once = _orig_collect


def test_get_watchlist_empty(client) -> None:
    """GET /api/watchlist with empty db returns empty lists."""
    resp = client.get("/api/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    assert data["buy"] == []
    assert data["sell"] == []
    assert "usd_rub" in data
    assert "updated_at" in data


def test_post_watchlist(client) -> None:
    """POST /api/watchlist with valid body returns 201, GET shows item."""
    resp = client.post("/api/watchlist", json={
        "name": "Kilowatt Case",
        "type": "buy",
        "target_rub": 60.0,
        "qty": 2,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["ok"] is True
    assert data["name"] == "Kilowatt Case"

    # Verify item appears in GET
    resp2 = client.get("/api/watchlist")
    assert resp2.status_code == 200
    wl = resp2.json()
    assert len(wl["buy"]) == 1
    item = wl["buy"][0]
    assert item["name"] == "Kilowatt Case"
    assert item["target_rub"] == 60.0
    assert item["current_price_usd"] == 0.78
    assert item["qty"] == 2


def test_post_watchlist_missing_field(client) -> None:
    """POST without 'name' returns 422."""
    resp = client.post("/api/watchlist", json={
        "type": "buy",
        "target_rub": 60.0,
    })
    assert resp.status_code == 422


def test_delete_watchlist(client) -> None:
    """Add item, DELETE it, GET confirms removal."""
    # Add first
    client.post("/api/watchlist", json={
        "name": "Kilowatt Case",
        "type": "buy",
        "target_rub": 60.0,
    })

    # Delete
    resp = client.delete("/api/watchlist/Kilowatt Case")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True

    # Confirm removal
    resp2 = client.get("/api/watchlist")
    assert resp2.json()["buy"] == []


def test_delete_watchlist_not_found(client) -> None:
    """DELETE non-existent returns 404."""
    resp = client.delete("/api/watchlist/nonexistent item")
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_search_no_query(client) -> None:
    """GET /api/search without q returns 422."""
    resp = client.get("/api/search")
    assert resp.status_code == 422


def test_search_with_results(client) -> None:
    """Pre-populated _prices, GET /api/search?q=kilowatt returns matches."""
    resp = client.get("/api/search?q=kilowatt")
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "kilowatt"
    assert len(data["results"]) >= 1
    assert data["results"][0]["name"] == "Kilowatt Case"
    assert data["results"][0]["price"] == 0.78


def test_history_empty(client) -> None:
    """GET /api/history/someitem returns empty points list."""
    resp = client.get("/api/history/nonexistent?tf=7d")
    assert resp.status_code == 200
    data = resp.json()
    assert data["points"] == []
    assert data["tf"] == "7d"


def test_stats_empty(client) -> None:
    """GET /api/stats with empty watchlist returns zeros."""
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_items"] == 0
    assert data["total_value_rub"] == 0.0
    assert "usd_rub" in data


# --- Tests for /api/lists endpoints (LIST-02, LIST-03) ---


def test_post_list(client) -> None:
    """POST /api/lists with valid body returns 201."""
    resp = client.post("/api/lists", json={
        "user": "lesha",
        "item_name": "AK-47 | Redline",
        "list_type": "favorite",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["ok"] is True


def test_post_list_missing_field(client) -> None:
    """POST /api/lists without item_name returns 422."""
    resp = client.post("/api/lists", json={
        "user": "lesha",
    })
    assert resp.status_code == 422


def test_post_list_invalid_type(client) -> None:
    """POST /api/lists with invalid list_type returns 400."""
    resp = client.post("/api/lists", json={
        "user": "lesha",
        "item_name": "X",
        "list_type": "invalid",
    })
    assert resp.status_code == 400


def test_delete_list(client) -> None:
    """After POST, DELETE returns 200 with removed=1."""
    client.post("/api/lists", json={
        "user": "lesha",
        "item_name": "AK-47 | Redline",
        "list_type": "favorite",
    })
    resp = client.request("DELETE", "/api/lists", json={
        "user": "lesha",
        "item_name": "AK-47 | Redline",
        "list_type": "favorite",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["removed"] == 1


def test_delete_list_not_found(client) -> None:
    """DELETE without prior add returns 200 with removed=0."""
    resp = client.request("DELETE", "/api/lists", json={
        "user": "lesha",
        "item_name": "nonexistent",
        "list_type": "favorite",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["removed"] == 0


def test_get_list_filtered(client) -> None:
    """GET /api/lists?user=lesha&type=favorite returns only favorites."""
    client.post("/api/lists", json={
        "user": "lesha", "item_name": "AK-47 | Redline", "list_type": "favorite",
    })
    client.post("/api/lists", json={
        "user": "lesha", "item_name": "AWP | Asiimov", "list_type": "favorite",
    })
    client.post("/api/lists", json={
        "user": "lesha", "item_name": "M4A4 | Howl", "list_type": "wishlist",
    })

    resp = client.get("/api/lists?user=lesha&type=favorite")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2


def test_get_list_all(client) -> None:
    """GET /api/lists?user=lesha (no type) returns all items."""
    client.post("/api/lists", json={
        "user": "lesha", "item_name": "AK-47 | Redline", "list_type": "favorite",
    })
    client.post("/api/lists", json={
        "user": "lesha", "item_name": "AWP | Asiimov", "list_type": "favorite",
    })
    client.post("/api/lists", json={
        "user": "lesha", "item_name": "M4A4 | Howl", "list_type": "wishlist",
    })

    resp = client.get("/api/lists?user=lesha")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 3


def test_get_list_missing_user(client) -> None:
    """GET /api/lists without user param returns 422."""
    resp = client.get("/api/lists")
    assert resp.status_code == 422
