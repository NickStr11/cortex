---
phase: 1
slug: database-foundation-bot-refactor
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (not yet installed) |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `cd tools/steam-sniper && uv run pytest tests/ -x -q` |
| **Full suite command** | `cd tools/steam-sniper && uv run pytest tests/ -v` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_db.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | DATA-01, DATA-02 | unit | `pytest tests/test_db.py::test_init_creates_tables -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | DATA-03 | unit | `pytest tests/test_db.py::test_price_snapshot_insert -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | DATA-04 | unit | `pytest tests/test_db.py::test_migration -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | DATA-05 | unit | `pytest tests/test_db.py::test_pruning -x` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 1 | DATA-06 | unit | `pytest tests/test_db.py::test_exchange_rate_cache -x` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 2 | BOT-01 | unit | `pytest tests/test_db.py::test_watchlist_crud -x` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 2 | BOT-02 | unit | `pytest tests/test_db.py::test_alert_logging -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_db.py` — stubs for DATA-01..06, BOT-01..02
- [ ] `tests/conftest.py` — `tmp_db` fixture using `:memory:` or `tmp_path`
- [ ] `uv add --dev pytest` — framework install

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bot starts with SQLite and responds to /list | BOT-01 | Requires live Telegram bot + token | Start bot locally, send /list, verify response |
| watchlist.json migration on first run | DATA-04 | Needs real JSON file + visual confirmation | Run bot, check SQLite has entries, /list shows correct targets |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
