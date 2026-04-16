# Milestones: Steam Sniper Dashboard

## v1.0 — MVP Dashboard + Bot

**Shipped:** 2026-04-12
**Phases:** 1–4 (6 plans total)
**Requirements:** 30/30 complete

### What shipped
- SQLite shared database (WAL mode, bot + dashboard)
- Migration from JSON watchlist
- Price history snapshots (5 min intervals, 90-day retention)
- USD/RUB exchange rate (ЦБ РФ)
- FastAPI REST API (watchlist CRUD, search 24k items, history, stats)
- Web dashboard: watchlist table, search, add/delete, hero stats, activity feed
- TradingView Lightweight Charts (24h/7d/30d/all)
- Dark theme, orange accent, gaming aesthetic
- VPS deployment (194.87.140.204:8100), systemd services
- Telegram bot refactored to SQLite

### Key decisions
- Lis-skins only (single marketplace)
- SQLite over JSON for concurrent access
- No auth (private URL, 2 users)
- Prices in RUB (user mental model)
- Collector inside FastAPI process

### Last phase
Phase 4 (VPS Deployment) — completed 2026-04-12
