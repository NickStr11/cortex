---
phase: 01-database-foundation-bot-refactor
plan: 02
subsystem: database
tags: [sqlite, telegram-bot, migration, price-snapshot, alert-logging]

requires:
  - phase: 01-01
    provides: db.py module with 4-table schema, CRUD, migration, exchange rate cache

provides:
  - "main.py fully rewired to db.py — JSON persistence removed"
  - "Price snapshot job (5-min interval) accumulating history in price_history table"
  - "Alert logging to alerts table on every triggered condition"
  - "USD/RUB rate persisted to exchange_rates table on every CBR fetch"
  - "watchlist.json auto-migrated and renamed to .bak on first startup"
affects: [phase-02-dashboard]

tech-stack:
  added: []
  patterns: [price-cache-with-ttl, upsert-on-conflict-via-db-module, target-rub-at-insertion]

key-files:
  created: []
  modified:
    - main.py

key-decisions:
  - "Targets stored as RUB at insertion time — no USD conversion in commands, only at alert comparison"
  - "4-minute price cache (_CACHE_TTL=240) shared by periodic_check and periodic_snapshot to reduce lis-skins hammering"
  - "Migration renames watchlist.json to .bak (not delete) — safe recovery if needed"

patterns-established:
  - "All bot persistence goes through db.py — main.py has zero direct SQLite calls"
  - "price cache: module-level tuple (timestamp, dict) checked before every fetch"

requirements-completed: [BOT-01, BOT-02]

duration: ~10min
completed: 2026-04-12
---

# Phase 01 Plan 02: Bot Refactor Summary

**main.py rewired from JSON to SQLite via db.py: all watchlist ops, price snapshots every 5 min, alert logging, exchange rate persistence, and watchlist.json migration on first boot**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-12T18:00:00Z
- **Completed:** 2026-04-12T18:10:00Z
- **Tasks:** 2 (1 auto + 1 human-verify, approved without live test)
- **Files modified:** 1

## Accomplishments
- Deleted _load_watchlist(), _save_watchlist(), WATCHLIST_PATH — JSON persistence gone
- All 5 bot commands (/buy, /sell, /list, /remove, /check) and handle_price_reply use db.py exclusively
- periodic_snapshot() job: records prices for all watched items every 300s, prunes history >90 days
- check_alerts() calls db.log_alert() on every triggered condition
- _get_usd_rub() persists fetched rate via db.save_rate() and loads from DB on cold start
- db.init_db() + migrate_json_to_sqlite() called at main() startup

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewire main.py — replace JSON with db.py, add snapshot job, alert logging, migration** - `aa97b4f` (feat)
2. **Task 2: Verify bot works with SQLite** - human-verify checkpoint, approved by user (skip live test)

## Files Created/Modified
- `main.py` - Full SQLite refactor: JSON functions deleted, all persistence via db module, price cache, snapshot job, migration call

## Decisions Made
- Targets stored in RUB at insertion (target_rub parameter) — comparison converts live USD price at check time via `item["price"] * rate <= entry["target_rub"]`
- 4-minute price cache shared between periodic_check and periodic_snapshot — reduces lis-skins API load
- Migration renames source file to .bak rather than deleting — allows manual recovery

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Bot runs entirely on SQLite. Price history accumulates from first startup.
- Phase 02 (dashboard) can now read watchlist + price_history directly from sniper.db without touching main.py
- sniper.db path: tools/steam-sniper/data/sniper.db (WAL mode, concurrent reads safe)

## Self-Check: PASSED

- main.py verified: contains `import db`, `db.init_db()`, `db.migrate_json_to_sqlite`, `db.get_watchlist()`, `db.upsert_item(`, `db.remove_item(`, `db.log_alert(`, `db.save_rate(`, `db.get_cached_rate(`, `async def periodic_snapshot(`, `db.insert_price_snapshots(`, `db.prune_old_history(`, `interval=300`, `.json.bak`, `target_rub`
- Commit aa97b4f confirmed in git log

---
*Phase: 01-database-foundation-bot-refactor*
*Completed: 2026-04-12*
