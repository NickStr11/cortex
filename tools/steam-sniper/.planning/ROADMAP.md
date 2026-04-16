# Roadmap: Steam Sniper Dashboard

## Milestones

- v1.0 MVP Dashboard + Bot - Phases 1-4 (shipped 2026-04-12)
- v2.0 Зеркало lis-skins - Phases 5-10 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3...): Planned milestone work
- Decimal phases (e.g., 5.1): Urgent insertions (marked with INSERTED)

<details>
<summary>v1.0 MVP Dashboard + Bot (Phases 1-4) - SHIPPED 2026-04-12</summary>

### Phase 1: Database Foundation + Bot Refactor
**Goal**: Single source of truth (SQLite) exists and both bot and future dashboard can read/write it
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, BOT-01, BOT-02
**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md -- SQLite schema, db.py module with all CRUD, migration, tests
- [x] 01-02-PLAN.md -- Bot refactor (JSON -> SQLite) + alert logging + snapshot job

### Phase 2: API Server + Collector
**Goal**: All watchlist and price data is accessible via REST API, with prices auto-updating every 5 minutes
**Depends on**: Phase 1
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, API-07
**Plans:** 1 plan

Plans:
- [x] 02-01: FastAPI server + collector background loop + REST endpoints

### Phase 3: Dashboard UI + Charts
**Goal**: Lesha opens the dashboard in a browser and sees everything needed to make buy/sell decisions
**Depends on**: Phase 2
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, CHART-01, CHART-02, CHART-03
**Plans:** 2 plans

Plans:
- [x] 03-01-PLAN.md -- Rewire dashboard to API, add hero stats, activity feed, add/delete, theme fix
- [x] 03-02-PLAN.md -- TradingView Lightweight Charts v5 -- price history, timeframes, stats

### Phase 4: VPS Deployment
**Goal**: Dashboard and bot are running in production on VPS, accessible from anywhere, surviving reboots
**Depends on**: Phase 3
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04
**Plans:** 1 plan

Plans:
- [x] 04-01-PLAN.md -- Deploy script (paramiko) + systemd units for dashboard + bot

</details>

### v2.0 Зеркало lis-skins (In Progress)

**Milestone Goal:** Превратить watchlist-дашборд в полное зеркало lis-skins с каталогом, категориями, двумя персональными списками и мобильным доступом.

- [x] **Phase 5: Dashboard Split** - ES modules + tab router (prep before feature work)
- [x] **Phase 6: Category Parser + Catalog API** - Backend: category detection + paginated catalog endpoint
- [x] **Phase 7: Dual Lists DB + API** - Backend: user_lists table + CRUD endpoints
- [x] **Phase 8: Dashboard Tabs + Catalog + Lists UI** - Frontend: catalog view, sidebar, list buttons, list tabs
- [ ] **Phase 9: Cases Tab + PWA** - Cases tab + HTTPS + PWA manifest + service worker
- [x] **Phase 10: Chrome Extension** - Manifest V3 extension for lis-skins.com (completed 2026-04-13)

## Phase Details

### Phase 5: Dashboard Split
**Goal**: Dashboard codebase is modular and ready for feature additions without fighting a 1373-line monolith
**Depends on**: Phase 4 (v1.0 complete)
**Requirements**: REF-01, REF-02
**Success Criteria** (what must be TRUE):
  1. Dashboard loads and all v1.0 functionality works identically (watchlist, search, charts, stats)
  2. JavaScript is split into separate ES modules (router, charts, watchlist, etc.) imported by main entry point
  3. Tab navigation works via hash-based routing (e.g., #watchlist, #catalog) with browser back/forward support
**Plans**: 2 plans

Plans:
- [x] 05-01-PLAN.md -- Static infrastructure + CSS extraction + ES module split
- [x] 05-02-PLAN.md -- Hash-based tab router + tab navigation UI

### Phase 6: Category Parser + Catalog API
**Goal**: Server can classify any CS2 item into a category and serve the full 24k catalog with pagination, filtering, and sorting
**Depends on**: Phase 5
**Requirements**: CAT-01, CAT-02, CAT-05
**Success Criteria** (what must be TRUE):
  1. GET /api/catalog returns paginated items (limit/offset) with category field on each item
  2. GET /api/catalog?category=knife returns only knives (same for all 11+ categories)
  3. GET /api/catalog?sort=price_asc returns items sorted by price ascending (and other sort options work)
  4. GET /api/catalog?q=dragon returns items matching search query within the catalog
**Plans**: 1 plan

Plans:
- [x] 06-01-PLAN.md -- Category parser (lookup dict) + catalog API endpoint with pagination/filter/sort

**Note:** Can execute in PARALLEL with Phase 7 (no dependencies between them).

### Phase 7: Dual Lists DB + API
**Goal**: Users have two separate personal lists (favorites + wishlist) stored in the database with full CRUD via API
**Depends on**: Phase 5
**Requirements**: LIST-01, LIST-02, LIST-03
**Success Criteria** (what must be TRUE):
  1. user_lists table exists in SQLite (separate from watchlist), storing user_id, item_name, list_type, added_at
  2. POST /api/lists adds an item to a list; DELETE /api/lists removes it -- changes persist across restarts
  3. GET /api/lists?user=lesha&type=favorite returns only Lesha's favorites (same for wishlist)
**Plans**: 1 plan

Plans:
- [x] 07-01-PLAN.md -- user_lists SQLite table + db CRUD + POST/DELETE/GET /api/lists endpoints

**Note:** Can execute in PARALLEL with Phase 6 (no dependencies between them).

### Phase 8: Dashboard Tabs + Catalog + Lists UI
**Goal**: User navigates between tabs, browses the full catalog with category sidebar, and manages personal lists visually
**Depends on**: Phase 6 + Phase 7 (needs both catalog API and lists API)
**Requirements**: CAT-03, CAT-04, LIST-04, LIST-05, LIST-06
**Success Criteria** (what must be TRUE):
  1. Catalog tab shows item cards with price, image, category, and availability -- paginated (no browser freeze on 24k items)
  2. Sidebar lists all categories with item counts; clicking a category filters the catalog view
  3. Each catalog card has heart (favorite) and star (wishlist) toggle buttons that add/remove with one click
  4. "Favorites" and "Wishlist" tabs show only items in the respective personal list
  5. Cards in catalog view show visual indicator when an item is already in a list (filled heart/star)
**Plans**: 2 plans

Plans:
- [x] 08-01-PLAN.md -- Catalog tab: item cards + pagination + category sidebar + sort + search
- [x] 08-02-PLAN.md -- List toggle buttons + favorites/wishlist tabs + card indicators

### Phase 9: Cases Tab + PWA
**Goal**: Cases have a dedicated browsing tab, and the dashboard is installable as a home screen app on iPhone
**Depends on**: Phase 8
**Requirements**: CASE-01, CASE-02, PWA-01, PWA-02, PWA-03
**Success Criteria** (what must be TRUE):
  1. "Cases" tab shows only case items with price, availability, and price trend indicator
  2. Dashboard is served over HTTPS (nginx reverse proxy + Let's Encrypt on VPS)
  3. iPhone user can add dashboard to home screen and it opens in standalone mode (no Safari chrome)
  4. Static assets (JS, CSS, icons) are cached by service worker; HTML and API calls use network-first strategy
**Plans**: 2 plans

Plans:
- [x] 09-01-PLAN.md -- Cases tab (filtered catalog view with price trend badges)
- [x] 09-02-PLAN.md -- PWA manifest + service worker + icons + nginx HTTPS reverse proxy

### Phase 10: Chrome Extension
**Goal**: User can add items to their Sniper lists directly from lis-skins.com without switching to the dashboard
**Depends on**: Phase 7 (needs list API only)
**Requirements**: EXT-01, EXT-02, EXT-03, EXT-04
**Success Criteria** (what must be TRUE):
  1. Extension installs in Chrome (unpacked, Manifest V3) and activates on lis-skins.com pages
  2. "Add to Sniper" button appears on item pages at lis-skins.com
  3. Clicking the button adds the item to a list via dashboard API (POST /api/lists) through background service worker
  4. User sees success or error notification after clicking (visual feedback within 2 seconds)
**Plans**: 1 plan

Plans:
- [ ] 10-01-PLAN.md -- Manifest V3 extension (content script + background worker + lis-skins DOM injection)

## Progress

**Execution Order:**
Phases 6 and 7 can run in parallel. Phase 8 depends on both. Phase 10 can start after Phase 7.

5 -> 6 (parallel with 7) -> 8 -> 9
5 -> 7 (parallel with 6) -> 10

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Database Foundation | v1.0 | 2/2 | Complete | 2026-04-12 |
| 2. API Server + Collector | v1.0 | 1/1 | Complete | 2026-04-12 |
| 3. Dashboard UI + Charts | v1.0 | 2/2 | Complete | 2026-04-12 |
| 4. VPS Deployment | v1.0 | 1/1 | Complete | 2026-04-12 |
| 5. Dashboard Split | v2.0 | 2/2 | Complete | 2026-04-13 |
| 6. Category Parser + Catalog API | v2.0 | 1/1 | Complete | 2026-04-13 |
| 7. Dual Lists DB + API | v2.0 | 1/1 | Complete | 2026-04-13 |
| 8. Dashboard Tabs + Catalog + Lists UI | v2.0 | 2/2 | Complete | 2026-04-13 |
| 9. Cases Tab + PWA | v2.0 | 2/2 | Complete | 2026-04-13 |
| 10. Chrome Extension | 1/1 | Complete    | 2026-04-13 | - |
