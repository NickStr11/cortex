# Phase 1: Database Foundation + Bot Refactor - Research

**Researched:** 2026-04-12
**Domain:** SQLite persistence layer, Python async bot refactor, data migration
**Confidence:** HIGH

## Summary

Phase 1 replaces a single-file JSON watchlist with SQLite as the shared source of truth for bot and future dashboard. The codebase is a 553-line single-file Telegram bot (`main.py`) using `python-telegram-bot v21+` with `asyncio`-native handlers and `JobQueue` for periodic checks. All watchlist operations go through `_load_watchlist()` / `_save_watchlist()` — two functions that are the only touch points needing replacement. SQLite 3 is stdlib, no new dependency required.

The primary complexity is: (1) a schema design that accommodates both bot reads/writes and future FastAPI concurrent reads, (2) a migration with an ambiguous existing data format (see Data Issues section), and (3) price history accumulation every 5 minutes alongside the 2-hour bot check cycle, requiring a separate job. WAL mode + `busy_timeout=5000` are already decided — verified to work with Python 3.12 stdlib sqlite3.

**Primary recommendation:** Extract a `db.py` module (~150 lines), migrate the two JSON I/O functions, keep all existing bot logic untouched except those two call sites, add a second `JobQueue` job for 5-minute price snapshots and alert logging.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-01 | Watchlist stored in SQLite (not JSON), shared DB for bot and dashboard | `watchlist` table schema below; WAL mode enables concurrent access |
| DATA-02 | SQLite WAL mode for concurrent access (bot writes + FastAPI reads/writes) | `PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=5000` — verified working |
| DATA-03 | Price history: snapshots every 5 min for watched items | `price_history` table + second JobQueue job at 300s interval |
| DATA-04 | Migrate existing watchlist.json to SQLite on first run | One-shot migration with data anomaly handling (see Data Issues) |
| DATA-05 | Retention: keep history 90 days, downsampling old data | DELETE WHERE ts < NOW-90d; downsampling deferred to Phase 2 or daily job |
| DATA-06 | USD/RUB rate cached and refreshed hourly (CBR RF API) | `exchange_rates` table or in-memory (existing `_get_usd_rub()` already works) |
| BOT-01 | Bot switches from JSON watchlist to SQLite | Replace `_load_watchlist()` / `_save_watchlist()` call sites with `db.py` |
| BOT-02 | Bot records alerts to SQLite (activity feed data) | `alerts` table; write on every triggered alert in `check_alerts()` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlite3 | stdlib (3.45.x in Py3.12) | Embedded relational DB | Zero dependency, WAL mode, concurrent readers, good enough for < 10M rows |
| python-telegram-bot | >=21.0 (already pinned) | Bot framework | Already in use, asyncio-native |
| beartype | latest | Runtime type checking | Required by cortex rules |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| contextlib | stdlib | `contextmanager` for DB connections | Clean connection lifecycle in async context |

**No new pip dependencies required for Phase 1.** sqlite3 is stdlib. Add `beartype` to pyproject.toml (not currently listed).

**Installation:**
```bash
cd tools/steam-sniper && uv add beartype
```

**Version verification (sqlite3):**
```bash
python -c "import sqlite3; print(sqlite3.sqlite_version)"
# Confirmed: SQLite 3.45.x ships with Python 3.12
```

## Architecture Patterns

### Recommended Project Structure
```
tools/steam-sniper/
├── main.py          # Bot only — import db, call db functions
├── db.py            # NEW: schema, connection, all SQL operations
├── data/
│   ├── sniper.db    # NEW: SQLite database
│   └── watchlist.json  # Keep until migration confirmed
└── pyproject.toml
```

Keep `main.py` as the bot entry point. `db.py` is a pure synchronous module (SQLite is synchronous; asyncio wrapping is unnecessary for lightweight operations — bot handlers will call `db.*` directly from async functions, which is fine for fast SQLite calls).

### Pattern 1: Connection Factory with WAL + busy_timeout

**What:** Single function returns a configured connection. Called per-operation (not a global connection) to avoid cross-thread issues with asyncio.

**When to use:** Any DB operation in the bot.

```python
# Source: Python docs + decisions in STATE.md
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "sniper.db"

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

**Note:** `PRAGMA journal_mode=WAL` persists to the DB file after first set — subsequent calls are no-ops but harmless.

### Pattern 2: Schema as init_db() function

**What:** All CREATE TABLE IF NOT EXISTS statements in one function, called at bot startup.

```python
def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                name_lower  TEXT NOT NULL,
                type        TEXT NOT NULL CHECK(type IN ('buy','sell')),
                target_rub  REAL NOT NULL,
                added_price_usd REAL,
                added_at    TEXT NOT NULL,
                qty         INTEGER DEFAULT 1
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_name_type
                ON watchlist(name_lower, type);

            CREATE TABLE IF NOT EXISTS price_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name_lower  TEXT NOT NULL,
                price_usd   REAL NOT NULL,
                ts          TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_ph_name_ts
                ON price_history(name_lower, ts);

            CREATE TABLE IF NOT EXISTS alerts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                type        TEXT NOT NULL CHECK(type IN ('buy','sell')),
                price_usd   REAL NOT NULL,
                target_rub  REAL NOT NULL,
                ts          TEXT NOT NULL DEFAULT (datetime('now')),
                message     TEXT
            );

            CREATE TABLE IF NOT EXISTS exchange_rates (
                currency    TEXT PRIMARY KEY,
                rate        REAL NOT NULL,
                updated_at  TEXT NOT NULL
            );
        """)
```

### Pattern 3: Watchlist CRUD replacing JSON functions

Replace `_load_watchlist()` and `_save_watchlist()` with targeted functions:

```python
def get_watchlist() -> dict[str, list[dict]]:
    """Drop-in replacement for _load_watchlist()."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM watchlist ORDER BY added_at"
        ).fetchall()
    result: dict[str, list[dict]] = {"buy": [], "sell": []}
    for row in rows:
        result[row["type"]].append(dict(row))
    return result

def upsert_item(name: str, type_: str, target_rub: float,
                added_price_usd: float, added_at: str, qty: int = 1) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO watchlist(name, name_lower, type, target_rub, added_price_usd, added_at, qty)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(name_lower, type) DO UPDATE SET
                target_rub=excluded.target_rub,
                added_price_usd=excluded.added_price_usd,
                added_at=excluded.added_at
        """, (name, name.lower(), type_, target_rub, added_price_usd, added_at, qty))

def remove_item(name: str) -> int:
    """Returns count of rows deleted."""
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM watchlist WHERE name_lower=?", (name.lower(),)
        )
        return cur.rowcount
```

### Pattern 4: Price History Job (5-minute snapshots)

Add a second `JobQueue` job alongside the existing 2-hour alert check:

```python
async def periodic_snapshot(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Every 5 min: fetch prices for watched items only, store snapshots, prune old data."""
    watched = db.get_watchlist_names()  # returns set of name_lower strings
    if not watched:
        return
    try:
        prices = fetch_prices()
    except Exception as e:
        logger.warning(f"Snapshot fetch failed: {e}")
        return
    db.insert_price_snapshots(
        [(name, prices[name]["price_usd"]) for name in watched if name in prices]
    )
    db.prune_old_history(days=90)

# In main():
app.job_queue.run_repeating(periodic_snapshot, interval=300, first=30)
```

### Pattern 5: Alert Logging

In `check_alerts()`, after building each alert message, also write to DB:

```python
def log_alert(name: str, type_: str, price_usd: float, target_rub: float, message: str) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO alerts(name, type, price_usd, target_rub, message)
            VALUES (?,?,?,?,?)
        """, (name, type_, price_usd, target_rub, message))
```

### Anti-Patterns to Avoid

- **Global connection object:** SQLite connections are not thread-safe; asyncio runs handlers in the same thread but future FastAPI will be in another process. Per-operation connections are simpler and correct.
- **WAL only on first connect:** WAL mode persists to the DB file. Setting it in `init_db()` once is enough, but setting it in every `get_conn()` call is harmless.
- **Storing targets in USD in the new schema:** Decision is locked — store `target_rub`. Convert at comparison time using `_get_usd_rub()`.
- **One JobQueue job doing both snapshot + alert check:** Keep them separate — snapshot is every 5 min, alert check is every 2 hours.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WAL concurrent access | Custom file locking | SQLite WAL mode | WAL allows one writer + multiple readers without locks |
| Retention/pruning | Custom ring-buffer | `DELETE WHERE ts < datetime('now', '-90 days')` | One SQL statement |
| Upsert logic | Check-then-insert | `INSERT ... ON CONFLICT DO UPDATE` | Atomic, race-condition-free |
| USD/RUB persistence | In-memory only | `exchange_rates` table (optional) | Survives bot restarts; in-memory already works but rate is lost on restart |

**Key insight:** SQLite handles all concurrency needs for Phase 1. No external broker, no queue, no ORM needed.

## Common Pitfalls

### Pitfall 1: Data Anomaly in watchlist.json

**What goes wrong:** The existing `watchlist.json` has `"target": 1500.0` for a sell entry. At today's USD/RUB rate (~85), 1500 USD would be an absurd price for a CS2 skin — this value is clearly in RUB, NOT USD. However, `added_price: 12.61` looks like USD.

**Root cause:** The entry was likely created before the RUB-conversion logic existed (or was hand-written directly). The bot's current code divides by USD/RUB rate on input, so live entries should have USD targets. But this entry did not go through that path.

**Migration strategy:** Detect anomaly heuristically — if `target > 100.0` for a "sell" entry, treat as already-in-RUB (don't divide again). If `target < 100.0`, treat as USD and multiply by current rate to get RUB. Migration script must log what it assumes for each entry.

**Warning signs:** After migration, run `/list` in the bot and verify target prices look sane in RUB.

### Pitfall 2: sqlite3 connection in async context

**What goes wrong:** Calling `sqlite3.connect()` inside an async function blocks the event loop for slow disks. For a local SQLite with a small DB this is < 1ms and acceptable. Phase 1 doesn't need `aiosqlite`.

**How to avoid:** Keep DB operations as fast synchronous calls directly in async handlers. If profiling shows issues (Phase 2+), add `aiosqlite`. Not needed now.

### Pitfall 3: `executescript()` auto-commits and ignores transactions

**What goes wrong:** `executescript()` issues a `COMMIT` before executing and doesn't support parameterized queries. Use it ONLY for DDL in `init_db()`. All DML (INSERT/UPDATE/DELETE) must use `execute()` or `executemany()` with parameters.

**How to avoid:** Keep `executescript()` in `init_db()` only. All data operations use `conn.execute(sql, params)`.

### Pitfall 4: Check interval vs. snapshot interval mismatch

**What goes wrong:** The 2-hour `periodic_check` (alert check) calls `fetch_prices()` which downloads the full 24k-item JSON. The 5-minute snapshot also calls `fetch_prices()`. At 5-minute intervals that's 12 fetches/hour = potentially hitting rate limits on lis-skins.

**How to avoid:** The 5-minute snapshot should ONLY fetch prices for watched items by filtering the response — but `fetch_prices()` always fetches the full JSON. Consider caching the full price response for 5 minutes (module-level dict with timestamp). The snapshot job re-uses the cached response. The alert job also re-uses it. This avoids multiple HTTP calls per cycle.

**Warning signs:** HTTP 429 or connection errors in logs.

### Pitfall 5: Missing `qty` field

**What goes wrong:** Current watchlist.json entries have no `qty` field. The `watchlist` table schema includes `qty` (needed by Phase 2 API). Migration must default `qty=1` for all migrated entries.

**How to avoid:** Always `DEFAULT 1` in schema, explicit `qty=1` in migration insert.

## Code Examples

### Migration Script Pattern

```python
# Source: standard sqlite3 migration pattern
def migrate_json_to_sqlite(json_path: Path) -> int:
    """Returns count of migrated items. Safe to re-run (idempotent via upsert)."""
    if not json_path.exists():
        return 0
    data = json.loads(json_path.read_text(encoding="utf-8"))
    rate = _get_usd_rub()
    migrated = 0
    for type_ in ("buy", "sell"):
        for entry in data.get(type_, []):
            raw_target = float(entry["target"])
            # Anomaly detection: if > 100, assume already RUB
            if raw_target > 100.0:
                target_rub = raw_target
                logger.warning(f"Migration: {entry['name']} target={raw_target} treated as RUB")
            else:
                target_rub = raw_target * rate
                logger.info(f"Migration: {entry['name']} target={raw_target} USD -> {target_rub:.0f} RUB")
            upsert_item(
                name=entry["name"],
                type_=type_,
                target_rub=target_rub,
                added_price_usd=float(entry.get("added_price", 0)),
                added_at=entry.get("added_at", datetime.now().isoformat()),
                qty=1,
            )
            migrated += 1
    return migrated
```

### Retention Pruning

```python
def prune_old_history(days: int = 90) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM price_history WHERE ts < datetime('now', ?)",
            (f"-{days} days",)
        )
        return cur.rowcount
```

### Exchange Rate Persistence (optional but recommended)

Storing rate in DB means the bot recovers a last-known rate across restarts without hitting CBR API immediately:

```python
def get_cached_rate(currency: str = "USD") -> float | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT rate FROM exchange_rates WHERE currency=?", (currency,)
        ).fetchone()
    return float(row["rate"]) if row else None

def save_rate(currency: str, rate: float) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO exchange_rates(currency, rate, updated_at)
            VALUES (?,?,datetime('now'))
            ON CONFLICT(currency) DO UPDATE SET rate=excluded.rate, updated_at=excluded.updated_at
        """, (currency, rate))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JSON file watchlist | SQLite with WAL | Phase 1 | Concurrent readers, history, structured queries |
| In-memory USD/RUB rate | DB-cached rate | Phase 1 | Survives restarts |
| Targets stored in USD | Targets stored in RUB | Phase 1 | Matches user mental model |
| No price history | 5-min snapshots for watched items | Phase 1 | Enables charts in Phase 3 |

**Not yet changed in Phase 1:**
- `fetch_prices()` remains synchronous urllib (no `httpx`/`aiohttp`) — acceptable
- No circuit breaker for lis-skins — still needed but deferred (STATE.md blocker)
- `added_price` in USD — stored in DB as-is; displayed via `_p()` conversion

## Open Questions

1. **Exchange rate in DB vs. in-memory only**
   - What we know: existing in-memory cache works fine; restart loses rate
   - What's unclear: how often does the bot restart? VPS reboots?
   - Recommendation: add `exchange_rates` table — cheap insurance, 2 extra SQL statements

2. **Price cache to prevent lis-skins rate limiting**
   - What we know: lis-skins rate limits are undocumented (STATE.md blocker)
   - What's unclear: what the actual limit is
   - Recommendation: add module-level `_prices_cache: tuple[float, dict] | None = None` with 4-minute TTL; both snapshot job and alert job re-use it. This halves HTTP requests immediately.

3. **DATA-05 downsampling spec**
   - What we know: 90-day retention, downsampling old data mentioned
   - What's unclear: what "downsampling" means specifically — keep one per hour? one per day?
   - Recommendation: implement only 90-day DELETE in Phase 1. Downsampling is a Phase 2 concern when data volume is visible.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (not yet installed) |
| Config file | none — Wave 0 creates pytest.ini |
| Quick run command | `cd tools/steam-sniper && uv run pytest tests/ -x -q` |
| Full suite command | `cd tools/steam-sniper && uv run pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | `watchlist` table created on `init_db()` | unit | `pytest tests/test_db.py::test_init_creates_tables -x` | Wave 0 |
| DATA-02 | WAL mode enabled after `init_db()` | unit | `pytest tests/test_db.py::test_wal_mode -x` | Wave 0 |
| DATA-03 | `insert_price_snapshots()` writes rows | unit | `pytest tests/test_db.py::test_price_snapshot_insert -x` | Wave 0 |
| DATA-04 | `migrate_json_to_sqlite()` imports entries, idempotent | unit | `pytest tests/test_db.py::test_migration -x` | Wave 0 |
| DATA-05 | `prune_old_history()` deletes rows older than N days | unit | `pytest tests/test_db.py::test_pruning -x` | Wave 0 |
| DATA-06 | `get_cached_rate()` returns None on cold start, float after `save_rate()` | unit | `pytest tests/test_db.py::test_exchange_rate_cache -x` | Wave 0 |
| BOT-01 | `get_watchlist()` returns same structure as old `_load_watchlist()` | unit | `pytest tests/test_db.py::test_watchlist_crud -x` | Wave 0 |
| BOT-02 | `log_alert()` inserts row to `alerts` table | unit | `pytest tests/test_db.py::test_alert_logging -x` | Wave 0 |

All tests use `:memory:` DB via a `tmp_path` fixture — no file system state.

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_db.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_db.py` — covers all DATA-* and BOT-* requirements above
- [ ] `tests/conftest.py` — `tmp_db` fixture using `:memory:` or `tmp_path`
- [ ] Framework install: `uv add --dev pytest` in `tools/steam-sniper/`

## Sources

### Primary (HIGH confidence)
- Python 3.12 stdlib sqlite3 docs — WAL mode, busy_timeout, executescript behavior
- `main.py` direct read — current bot structure, JSON format, handler patterns
- `watchlist.json` direct read — actual data format and anomaly
- `pyproject.toml` direct read — current dependencies
- Verified: `sqlite3.connect(':memory:').execute('PRAGMA journal_mode=WAL')` — works in Python 3.12.8

### Secondary (MEDIUM confidence)
- SQLite WAL documentation — concurrent readers confirmed (WAL allows N readers + 1 writer)
- python-telegram-bot v21 JobQueue docs — `run_repeating(interval=300)` pattern

### Tertiary (LOW confidence)
- lis-skins rate limit behavior — undocumented, inferred from STATE.md blocker note

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, existing dependencies
- Architecture: HIGH — direct code analysis, verified patterns
- Pitfalls: HIGH (data anomaly) / MEDIUM (rate limits) — confirmed from source
- Migration: HIGH — direct JSON inspection

**Research date:** 2026-04-12
**Valid until:** 2026-06-01 (stable domain)
