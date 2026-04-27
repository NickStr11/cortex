"""Tests for API layer — db query functions + FastAPI endpoints.

Covers API-01..07 requirements.
"""
from __future__ import annotations

import asyncio
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


def test_list_item_targets_and_cooldowns(tmp_db: Path) -> None:
    """List targets should persist and cooldown markers should be mutable."""
    import db

    db.init_db()
    db.add_list_item("lesha", "Kilowatt Case", "favorite")

    updated = db.set_list_item_targets(
        user_id="lesha",
        item_name="Kilowatt Case",
        list_type="favorite",
        target_below_rub=100.0,
        target_above_rub=200.0,
    )
    assert updated == 1

    item = db.get_list_items("lesha", "favorite")[0]
    assert item["target_below_rub"] == 100.0
    assert item["target_above_rub"] == 200.0
    assert item["last_notified_below_at"] is None

    db.mark_list_item_notified(int(item["id"]), "below", "2026-04-17T10:00:00+03:00")
    db.mark_list_item_notified(int(item["id"]), "above", "2026-04-17T10:10:00+03:00")
    marked = db.get_list_items("lesha", "favorite")[0]
    assert marked["last_notified_below_at"] == "2026-04-17T10:00:00+03:00"
    assert marked["last_notified_above_at"] == "2026-04-17T10:10:00+03:00"

    db.clear_list_item_notified(int(item["id"]), "below")
    cleared = db.get_list_items("lesha", "favorite")[0]
    assert cleared["last_notified_below_at"] is None
    assert cleared["last_notified_above_at"] == "2026-04-17T10:10:00+03:00"


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
        "glock-18 | vogue (field-tested)": {
            "name": "Glock-18 | Vogue (Field-Tested)",
            "price": 4.8,
            "url": "https://lis-skins.com/market/csgo/glock-18-vogue-field-tested/",
            "count": 22,
        },
        "tec-9 | remote control (field-tested)": {
            "name": "Tec-9 | Remote Control (Field-Tested)",
            "price": 2.4,
            "url": "https://lis-skins.com/market/csgo/tec-9-remote-control-field-tested/",
            "count": 18,
        },
        "awp | asiimov (field-tested)": {
            "name": "AWP | Asiimov (Field-Tested)",
            "price": 25.5,
            "url": "https://lis-skins.com/market/csgo/awp-asiimov-ft/",
            "count": 42,
        },
        "awp | asiimov (factory new)": {
            "name": "AWP | Asiimov (Factory New)",
            "price": 120.0,
            "url": "https://lis-skins.com/market/csgo/awp-asiimov-fn/",
            "count": 4,
        },
        "awp | asiimov (minimal wear)": {
            "name": "AWP | Asiimov (Minimal Wear)",
            "price": 44.0,
            "url": "https://lis-skins.com/market/csgo/awp-asiimov-mw/",
            "count": 17,
        },
        "awp | asiimov (well-worn)": {
            "name": "AWP | Asiimov (Well-Worn)",
            "price": 21.5,
            "url": "https://lis-skins.com/market/csgo/awp-asiimov-ww/",
            "count": 12,
        },
        "awp | asiimov (battle-scarred)": {
            "name": "AWP | Asiimov (Battle-Scarred)",
            "price": 18.2,
            "url": "https://lis-skins.com/market/csgo/awp-asiimov-bs/",
            "count": 8,
        },
    }
    server._usd_rub = 83.0
    server._last_update = "2026-04-12T18:00:00"

    # Disable lifespan (no real collector)
    async def noop(*_args, **_kwargs):
        pass

    _orig_collect = server._collect_once
    _orig_load_meta = server._load_item_meta_cache
    server._collect_once = noop
    server._load_item_meta_cache = noop

    from fastapi.testclient import TestClient

    with TestClient(server.app) as c:
        server._image_cache = {
            "kilowatt case": "https://images.example/kilowatt.png",
            "awp | asiimov": "https://images.example/asiimov.png",
            "glock-18 | vogue": "https://images.example/glock.png",
            "tec-9 | remote control": "https://images.example/tec9.png",
        }
        server._item_meta = {
            "awp | asiimov (field-tested)": {
                "rarity_name": "Covert",
                "rarity_label": "Тайное",
                "rarity_color": "#eb4b4b",
            },
            "glock-18 | vogue (field-tested)": {
                "rarity_name": "Classified",
                "rarity_label": "Засекреченное",
                "rarity_color": "#d32ce6",
            },
        }
        yield c

    # Restore
    server._collect_once = _orig_collect
    server._load_item_meta_cache = _orig_load_meta


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
    assert item["image_url"] == "https://images.example/kilowatt.png"


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
    assert data["results"][0]["image"] == "https://images.example/kilowatt.png"


def test_catalog_includes_image_cache_results(client) -> None:
    """GET /api/catalog should expose image URLs from the local image cache."""
    resp = client.get("/api/catalog?limit=50&offset=0&sort=name_asc&q=Kilowatt")
    assert resp.status_code == 200
    data = resp.json()
    items = {item["name"]: item for item in data["items"]}
    assert items["Kilowatt Case"]["image"] == "https://images.example/kilowatt.png"


def test_catalog_supports_model_filter(client) -> None:
    """GET /api/catalog should expose and apply per-weapon model filters."""
    resp = client.get("/api/catalog?category=pistol")
    assert resp.status_code == 200
    data = resp.json()
    model_names = {entry["name"] for entry in data["models"]}
    assert {"Glock-18", "Tec-9"} <= model_names

    resp2 = client.get("/api/catalog?category=pistol&model=Glock-18")
    assert resp2.status_code == 200
    filtered = resp2.json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["name"] == "Glock-18 | Vogue (Field-Tested)"


def test_history_empty(client) -> None:
    """GET /api/history/someitem returns empty points list."""
    resp = client.get("/api/history/nonexistent?tf=7d")
    assert resp.status_code == 200
    data = resp.json()
    assert data["points"] == []
    assert data["tf"] == "7d"


def test_item_detail_uses_streamed_listing_data(client, monkeypatch) -> None:
    """GET /api/item should format snapshot listing data into UI payload."""
    import server

    monkeypatch.setattr(server, "snapshot_get_item_listings", lambda _name, limit, **_kwargs: ([
        {
            "id": 123,
            "price": 25.4,
            "float": "0.1534",
            "paint_index": 279,
            "paint_seed": 901,
            "stickers": [{"name": "Crown", "image": "https://images.example/sticker.png"}],
            "keychains": [{"name": "Lil' Monster", "image": "https://images.example/keychain.png"}],
            "unlock_at": None,
            "item_link": "steam://inspect/123",
        }
    ][:limit], 1, "2026-04-17T08:00:00+03:00"))
    monkeypatch.setattr(server, "snapshot_status", lambda: {
        "available": True,
        "built_at": "2026-04-17T08:05:00+03:00",
        "size_bytes": 123456,
    })

    resp = client.get("/api/item/AWP%20%7C%20Asiimov%20%28Field-Tested%29")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["name"] == "AWP | Asiimov (Field-Tested)"
    assert data["summary"]["image"] == "https://images.example/asiimov.png"
    assert data["summary"]["rarity_label"] == "Тайное"
    assert data["summary"]["rarity_emphasis"] is True
    assert data["summary"]["wear_label"] == "После полевых испытаний"
    assert data["listings_total"] == 1
    assert data["listings_updated"] == "2026-04-17T08:00:00+03:00"
    assert data["snapshot_available"] is True
    assert data["snapshot_built_at"] == "2026-04-17T08:05:00+03:00"
    assert [tier["wear"] for tier in data["wear_tiers"]] == ["FN", "MW", "FT", "WW", "BS"]
    assert next(tier for tier in data["wear_tiers"] if tier["active"])["name"] == "AWP | Asiimov (Field-Tested)"
    assert data["listings"][0]["id"] == 123
    assert data["listings"][0]["price_usd"] == 25.4
    assert data["listings"][0]["keychains"][0]["name"] == "Lil' Monster"
    assert data["listings"][0]["item_link"] == "steam://inspect/123"


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


def test_patch_list_targets_and_trigger_flags(client) -> None:
    """PATCH /api/lists/target should persist thresholds and enrich GET /api/lists."""
    client.post("/api/lists", json={
        "user": "lesha",
        "item_name": "Kilowatt Case",
        "list_type": "favorite",
    })

    resp = client.patch("/api/lists/target", json={
        "user": "lesha",
        "item_name": "Kilowatt Case",
        "list_type": "favorite",
        "target_below_rub": 100.0,
        "target_above_rub": 50.0,
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp2 = client.get("/api/lists?user=lesha&type=favorite")
    assert resp2.status_code == 200
    item = resp2.json()["items"][0]
    assert item["current_price_rub"] is not None
    assert item["target_below_rub"] == 100.0
    assert item["target_above_rub"] == 50.0
    assert item["alert_below_triggered"] is True
    assert item["alert_above_triggered"] is True


def test_get_list_missing_user(client) -> None:
    """GET /api/lists without user param returns 422."""
    resp = client.get("/api/lists")
    assert resp.status_code == 422


def test_post_list_normalizes_russian_name(client, monkeypatch) -> None:
    """POST /api/lists should normalize Russian names to canonical lis-skins EN."""
    import server

    ru_name = (
        "AWP | "
        "\u0410\u0437\u0438\u043c\u043e\u0432 "
        "(\u041f\u043e\u0441\u043b\u0435 \u043f\u043e\u043b\u0435\u0432\u044b\u0445 "
        "\u0438\u0441\u043f\u044b\u0442\u0430\u043d\u0438\u0439)"
    )

    monkeypatch.setattr(server, "_steam_search", lambda _q: [{
        "hash_name": "AWP | Asiimov (Field-Tested)",
        "name_ru": ru_name,
        "type_ru": "",
        "image": "",
        "name_color": "",
    }])

    resp = client.post("/api/lists", json={
        "user": "lesha",
        "item_name": ru_name,
        "list_type": "favorite",
    })
    assert resp.status_code == 201
    assert resp.json()["item_name"] == "AWP | Asiimov (Field-Tested)"

    resp2 = client.get("/api/lists?user=lesha&type=favorite")
    data = resp2.json()
    assert data["items"][0]["item_name"] == "AWP | Asiimov (Field-Tested)"
    assert data["items"][0]["image"] == "https://images.example/asiimov.png"
    assert data["items"][0]["price_rub"] is not None


def test_post_list_preserves_russian_wear_when_steam_search_order_is_wrong(client, monkeypatch) -> None:
    """Resolver must not save Minimal Wear when the incoming name says Field-Tested."""
    import server

    ru_name = (
        "AWP | "
        "\u0410\u0437\u0438\u043c\u043e\u0432 "
        "(\u041f\u043e\u0441\u043b\u0435 \u043f\u043e\u043b\u0435\u0432\u044b\u0445 "
        "\u0438\u0441\u043f\u044b\u0442\u0430\u043d\u0438\u0439)"
    )

    monkeypatch.setattr(server, "_steam_search", lambda _q: [
        {
            "hash_name": "AWP | Asiimov (Minimal Wear)",
            "name_ru": ru_name,
            "type_ru": "",
            "image": "",
            "name_color": "",
        },
        {
            "hash_name": "AWP | Asiimov (Field-Tested)",
            "name_ru": ru_name,
            "type_ru": "",
            "image": "",
            "name_color": "",
        },
    ])

    resp = client.post("/api/lists", json={
        "user": "lesha",
        "item_name": ru_name,
        "list_type": "favorite",
    })
    assert resp.status_code == 201
    assert resp.json()["item_name"] == "AWP | Asiimov (Field-Tested)"

    resp2 = client.get("/api/lists?user=lesha&type=favorite")
    item = resp2.json()["items"][0]
    assert item["item_name"] == "AWP | Asiimov (Field-Tested)"
    assert item["price_rub"] == round(25.5 * server._lis_rate(), 2)


def test_post_list_resolves_colloquial_field_tested_without_steam(client, monkeypatch) -> None:
    """Local RU fallback should understand 'послеполевые' and keep the FT price."""
    import server

    ru_name = (
        "AWP | "
        "\u0410\u0437\u0438\u043c\u043e\u0432 "
        "(\u041f\u043e\u0441\u043b\u0435\u043f\u043e\u043b\u0435\u0432\u044b\u0435)"
    )

    monkeypatch.setattr(server, "_steam_search", lambda _q: [])

    resp = client.post("/api/lists", json={
        "user": "lesha",
        "item_name": ru_name,
        "list_type": "favorite",
    })
    assert resp.status_code == 201
    assert resp.json()["item_name"] == "AWP | Asiimov (Field-Tested)"

    resp2 = client.get("/api/lists?user=lesha&type=favorite")
    item = resp2.json()["items"][0]
    assert item["price_rub"] == round(25.5 * server._lis_rate(), 2)


def test_get_list_repairs_mojibake_name(client, monkeypatch, tmp_db: Path) -> None:
    """GET /api/lists should repair old mojibake entries in-place."""
    import db
    import server

    ru_name = (
        "AWP | "
        "\u0410\u0437\u0438\u043c\u043e\u0432 "
        "(\u041f\u043e\u0441\u043b\u0435 \u043f\u043e\u043b\u0435\u0432\u044b\u0445 "
        "\u0438\u0441\u043f\u044b\u0442\u0430\u043d\u0438\u0439)"
    )
    mojibake_name = ru_name.encode("utf-8").decode("latin-1")

    monkeypatch.setattr(server, "_steam_search", lambda _q: [{
        "hash_name": "AWP | Asiimov (Field-Tested)",
        "name_ru": ru_name,
        "type_ru": "",
        "image": "",
        "name_color": "",
    }])
    db.add_list_item(
        user_id="lesha",
        item_name=mojibake_name,
        list_type="favorite",
    )

    resp = client.get("/api/lists?user=lesha&type=favorite")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"][0]["item_name"] == "AWP | Asiimov (Field-Tested)"

    repaired = db.get_list_items("lesha", "favorite")
    assert repaired[0]["item_name"] == "AWP | Asiimov (Field-Tested)"


def test_check_list_alerts_respects_cooldown(tmp_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Server-side list alerts should send once and then respect cooldown."""
    import db
    import server

    db.init_db()
    server._prices = {
        "kilowatt case": {
            "name": "Kilowatt Case",
            "price": 0.78,
            "url": "https://lis-skins.com/market/csgo/kilowatt-case/",
            "count": 1500,
        },
    }
    server._usd_rub = 83.0
    db.add_list_item("lesha", "Kilowatt Case", "favorite")
    db.set_list_item_targets("lesha", "Kilowatt Case", "favorite", 100.0, None)

    sent_messages: list[str] = []

    async def fake_send(text: str, chat_ids=None):
        sent_messages.append(text)
        return 1

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("LESHA_TG_CHAT_ID", "461494896")
    monkeypatch.setattr(server, "_send_telegram_message", fake_send)

    asyncio.run(server._check_list_alerts())
    assert len(sent_messages) == 1
    assert "Kilowatt Case" in sent_messages[0]

    asyncio.run(server._check_list_alerts())
    assert len(sent_messages) == 1
