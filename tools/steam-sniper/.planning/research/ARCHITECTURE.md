# Architecture: v2.0 Integration Plan

**Domain:** CS2 skin catalog + dual lists + case tracking + PWA + Chrome extension
**Researched:** 2026-04-13
**Scope:** How new features integrate with existing FastAPI + vanilla JS + SQLite architecture

## Existing Architecture (v1.0 -- what we have now)

```
┌──────────────────────────────────────────────────────┐
│                  VPS :8100                            │
│                                                      │
│  ┌──────────┐    ┌──────────────────────────────┐   │
│  │ Telegram  │    │ FastAPI server.py             │   │
│  │ Bot       │    │   /api/watchlist (CRUD)       │   │
│  │ main.py   │    │   /api/search (lis-skins EN   │   │
│  │ (polling) │    │     + Steam Market RU)        │   │
│  └────┬──────┘    │   /api/history/{name}         │   │
│       │           │   /api/stats, /api/alerts     │   │
│       │           │   Background: _collect_once() │   │
│       │           │     -> 24k items in _prices    │   │
│       │           │     -> snapshots for watched   │   │
│       │           └──────────┬───────────────────┘   │
│       │                      │                       │
│       └──────────────────────┤                       │
│                              │                       │
│                     ┌────────▼────────┐              │
│                     │ SQLite (WAL)    │              │
│                     │ - watchlist     │              │
│                     │ - price_history │              │
│                     │ - alerts        │              │
│                     │ - exchange_rates│              │
│                     └─────────────────┘              │
└──────────────────────────────────────────────────────┘
```

**Key facts about current state:**
- `_prices` dict: 24k items in server.py memory, refreshed every 5 min
- `watchlist` table: ~20 items, type buy/sell, one flat list
- `price_history`: snapshots only for watched items (not all 24k)
- Dashboard: single page, ~1200 lines HTML/CSS/JS in one file
- No category data in lis-skins JSON (only name, price, url, count)
- Search: EN via in-memory `_prices`, RU via Steam Market API
- No user concept (shared watchlist, no auth)

## New Features: Integration Analysis

### Feature 1: Full Catalog Browsing (24k items)

**Challenge:** Currently 24k items live only in `_prices` dict (server memory). No API exposes the full catalog. Dashboard only shows search results (max 24) and watchlist.

**Integration approach:**

```
NEW ENDPOINT: GET /api/catalog?category=rifle&page=1&per_page=50&sort=price&q=ak

Server-side pagination from _prices dict (already in memory).
No new DB table needed -- _prices is refreshed every 5 min and is the source of truth.
```

**Why server-side pagination, not dump all 24k to browser:**
- 24k items JSON = ~3-5 MB raw. Acceptable for initial load, but UX is bad (render 24k cards = DOM explosion).
- Server returns 50 items per page with filters applied = fast, lightweight responses.
- `_prices` dict is already indexed by name_lower. Add a secondary index for categories.

**New server-side data structure:**

```python
# In server.py, alongside _prices:
_catalog_by_category: dict[str, list[dict]] = {}  # {category: [items]}
_all_categories: list[str] = []  # sorted category names

# Built during _collect_once() from item names
```

**Category parsing from item names:**
Lis-skins JSON has no category field. Categories must be parsed from item names. CS2 naming follows predictable patterns:

```
"AK-47 | Redline (Field-Tested)"     -> weapon: "AK-47", type: "Rifle"
"★ Butterfly Knife | Fade (FN)"      -> weapon: "Butterfly Knife", type: "Knife"
"Kilowatt Case"                       -> type: "Case"
"Sticker | Natus Vincere"            -> type: "Sticker"
"Operation Breakout Weapon Case"      -> type: "Case"
"Sealed Graffiti | ..."              -> type: "Graffiti"
"Music Kit | ..."                     -> type: "Music Kit"
```

**Implementation:** A `_parse_category(name: str) -> str` function with prefix matching:
- Names starting with weapon prefix (AK-47, M4A4, AWP, etc.) -> map to weapon type (Rifle, Sniper, Pistol)
- Names starting with special markers -> Knife, Gloves, Sticker, Case, etc.
- ~15 rules cover 95%+ of items. Fallback: "Other"

**What changes:**
| Component | Change Type | Details |
|-----------|-------------|---------|
| server.py | NEW endpoint | `GET /api/catalog` with pagination, category filter, sort |
| server.py | MODIFY `_collect_once()` | Build `_catalog_by_category` after fetching prices |
| server.py | NEW function | `_parse_category(name)` for item classification |
| dashboard.html | NEW section | Catalog tab/view with grid, category sidebar, pagination |
| db.py | No change | Catalog is served from memory, not DB |

### Feature 2: Dual Personal Lists (Favorites + Wishlist)

**Challenge:** Current `watchlist` table has `type` field for buy/sell distinction. New lists are orthogonal: favorites = "I own this", wishlist = "I want this". These are NOT the same as buy/sell alerts.

**Schema evolution -- two options:**

**Option A (recommended): New `user_lists` table**
```sql
CREATE TABLE IF NOT EXISTS user_lists (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL DEFAULT 'shared',
    name_lower  TEXT NOT NULL,
    name        TEXT NOT NULL,
    list_type   TEXT NOT NULL CHECK(list_type IN ('favorite', 'wishlist')),
    added_at    TEXT NOT NULL DEFAULT (datetime('now')),
    notes       TEXT,
    image_url   TEXT,
    UNIQUE(user_id, name_lower, list_type)
);
CREATE INDEX IF NOT EXISTS idx_ul_user_type ON user_lists(user_id, list_type);
```

**Why separate table, not reuse watchlist:**
- Watchlist items have `target_rub`, `type` (buy/sell), `added_price_usd`, `qty` -- alert-specific fields.
- Favorites/wishlist are simpler: just "this item is in my list". No price target.
- An item can be in favorites AND have a sell alert in watchlist simultaneously.
- Clean separation: watchlist = price alerts, user_lists = personal organization.

**Option B (not recommended): Add `list_type` column to watchlist**
Would overload the watchlist table with two different concepts. Queries become confusing. Rejected.

**What changes:**
| Component | Change Type | Details |
|-----------|-------------|---------|
| db.py | NEW table | `user_lists` with favorite/wishlist distinction |
| db.py | NEW functions | `add_to_list()`, `remove_from_list()`, `get_list()`, `is_in_list()` |
| server.py | NEW endpoints | `POST/DELETE /api/lists/{list_type}/{name}`, `GET /api/lists/{list_type}` |
| dashboard.html | MODIFY cards | Add heart/star buttons on every card (catalog + watchlist) |
| dashboard.html | NEW views | Favorites tab, Wishlist tab |
| main.py (bot) | Optional | `/fav`, `/wish` commands (can defer) |

**Data flow for list buttons:**
```
User clicks heart on catalog card
  -> POST /api/lists/favorite/AK-47%20%7C%20Redline%20(Field-Tested)
  -> db.add_to_list(user_id='shared', name_lower=..., list_type='favorite')
  -> UI updates: heart fills in
  
Catalog card render checks:
  -> On load: GET /api/lists/favorite (returns set of name_lower)
  -> Frontend caches as Set for O(1) lookup
  -> Each card checks: isFavorite(name_lower) ? filled heart : empty heart
```

### Feature 3: Case Tracking (separate tab)

**What:** Cases are a subset of the catalog (~3000 items with "Case" in name). Dedicated view because Lesha tracks case prices specifically.

**Integration:** This is NOT a new data source. Cases are already in `_prices` dict. Just a filtered view.

**What changes:**
| Component | Change Type | Details |
|-----------|-------------|---------|
| server.py | MODIFY `_parse_category()` | Ensure "Case" category correctly identified |
| server.py | Possibly no change | `GET /api/catalog?category=case` already covers this if catalog endpoint is built |
| dashboard.html | NEW tab/view | Cases tab showing case items with price trends |

**Dependency:** Requires catalog endpoint (Feature 1) to exist first. Cases tab = catalog filtered to category=case.

### Feature 4: PWA Manifest (iPhone home screen)

**What:** Add `manifest.json` + service worker so Lesha can "Add to Home Screen" on iPhone and get an app-like experience.

**Integration:**

```
NEW FILES:
  manifest.json      -- PWA manifest (name, icons, theme_color, display: standalone)
  sw.js              -- minimal service worker (cache dashboard shell, not API data)
  icons/             -- 192x192 and 512x512 PNG icons
  
MODIFY:
  dashboard.html     -- add <link rel="manifest"> and service worker registration
  server.py          -- mount /static for manifest.json, sw.js, icons
```

**Service worker strategy: Network-first, cache shell only**
- Cache: dashboard.html, CSS (if extracted), icons, Lightweight Charts JS (CDN)
- DO NOT cache API responses (prices must be live)
- Offline: show cached shell with "No connection" message
- This is a thin PWA -- the value is "Add to Home Screen" UX, not offline functionality

**FastAPI static serving:**
```python
from fastapi.staticfiles import StaticFiles

# Mount static directory for PWA assets
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve manifest.json at root level (required by PWA spec)
@app.get("/manifest.json")
def serve_manifest():
    return FileResponse(Path(__file__).parent / "static" / "manifest.json")

# Service worker must be served from root scope
@app.get("/sw.js")
def serve_sw():
    return FileResponse(
        Path(__file__).parent / "static" / "sw.js",
        media_type="application/javascript",
    )
```

**What changes:**
| Component | Change Type | Details |
|-----------|-------------|---------|
| server.py | MODIFY | Mount `/static`, add `/manifest.json` and `/sw.js` routes |
| dashboard.html | MODIFY | Add `<link rel="manifest">`, meta tags, SW registration |
| NEW static/ | NEW directory | `manifest.json`, `sw.js`, `icons/` |

### Feature 5: Chrome Extension for lis-skins.com

**What:** Content script that injects "Add to Dashboard" buttons on lis-skins.com item pages. Click -> sends item to dashboard's `/api/lists/{type}` or `/api/watchlist`.

**Architecture:**

```
┌─────────────────────────────────────────┐
│  lis-skins.com (browser tab)            │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ Content Script (content.js)     │    │
│  │ - Injects buttons on item page  │    │
│  │ - Reads item name/price from DOM│    │
│  │ - Sends to background worker    │    │
│  └──────────┬──────────────────────┘    │
│             │ chrome.runtime.sendMessage │
└─────────────┼───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│  Service Worker (background.js)         │
│  - Receives item data                  │
│  - POST to dashboard API               │
│  - Shows notification on success       │
└─────────────┬───────────────────────────┘
              │ fetch()
              ▼
┌──────────────────────────────────────┐
│  VPS :8100                           │
│  POST /api/lists/wishlist/{name}     │
│  or POST /api/watchlist              │
└──────────────────────────────────────┘
```

**Manifest V3 structure:**
```json
{
  "manifest_version": 3,
  "name": "Steam Sniper",
  "version": "1.0",
  "permissions": [],
  "host_permissions": [
    "https://lis-skins.com/*",
    "http://194.87.140.204:8100/*"
  ],
  "content_scripts": [{
    "matches": ["https://lis-skins.com/market/csgo/*"],
    "js": ["content.js"],
    "run_at": "document_idle"
  }],
  "background": {
    "service_worker": "background.js"
  },
  "icons": {
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

**Content script logic:**
1. Detect item page on lis-skins.com
2. Parse item name and price from page DOM
3. Inject floating button: "Add to Sniper" with sub-options (Favorite / Wishlist / Watch)
4. On click -> `chrome.runtime.sendMessage({action, item})`
5. Background service worker -> `fetch('http://194.87.140.204:8100/api/...')`

**What changes:**
| Component | Change Type | Details |
|-----------|-------------|---------|
| NEW extension/ | NEW directory | `manifest.json`, `content.js`, `background.js`, `icons/` |
| server.py | No change | CORS already `allow_origins=["*"]` -- extension can POST |

**Key constraint:** Extension communicates with VPS by IP:port. No HTTPS. Chrome allows this for extensions via `host_permissions`. Works for private use.

## Component Map: New vs Modified

```
tools/steam-sniper/
├── server.py              MODIFY  (+catalog endpoint, +list endpoints, +static mount, +SW/manifest routes)
├── db.py                  MODIFY  (+user_lists table, +list CRUD functions, +category helpers)
├── main.py                MINOR   (+optional /fav /wish commands)
├── dashboard.html         MAJOR   (+catalog view, +tabs, +list buttons, +PWA meta, +SW registration)
├── deploy.py              MODIFY  (+push static/ dir, +push extension/ dir)
├── static/                NEW DIR
│   ├── manifest.json      NEW     (PWA manifest)
│   ├── sw.js              NEW     (service worker)
│   └── icons/             NEW     (PWA icons 192x192, 512x512)
├── extension/             NEW DIR (Chrome extension, not deployed to VPS -- user installs locally)
│   ├── manifest.json      NEW     (Manifest V3)
│   ├── content.js         NEW     (injects buttons on lis-skins.com)
│   ├── background.js      NEW     (handles API calls to dashboard)
│   └── icons/             NEW
└── data/
    └── sniper.db          MODIFY  (+user_lists table via migration)
```

## Database Schema Evolution

```sql
-- EXISTING (no changes):
-- watchlist, price_history, alerts, exchange_rates

-- NEW:
CREATE TABLE IF NOT EXISTS user_lists (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL DEFAULT 'shared',
    name_lower  TEXT NOT NULL,
    name        TEXT NOT NULL,
    list_type   TEXT NOT NULL CHECK(list_type IN ('favorite', 'wishlist')),
    added_at    TEXT NOT NULL DEFAULT (datetime('now')),
    notes       TEXT,
    image_url   TEXT,
    UNIQUE(user_id, name_lower, list_type)
);
CREATE INDEX IF NOT EXISTS idx_ul_user_type ON user_lists(user_id, list_type);
```

**Migration:** Add `CREATE TABLE IF NOT EXISTS` to `db.init_db()`. Safe for existing DBs -- won't touch existing tables.

## API Surface: New Endpoints

| Endpoint | Method | Purpose | Returns |
|----------|--------|---------|---------|
| `/api/catalog` | GET | Paginated catalog browse | `{items: [...], total, page, categories: [...]}` |
| `/api/catalog/categories` | GET | List all categories with counts | `{categories: [{name, count}, ...]}` |
| `/api/lists/{list_type}` | GET | Get user's favorites or wishlist | `{items: [...]}` |
| `/api/lists/{list_type}/{name}` | POST | Add item to list | `{ok: true}` |
| `/api/lists/{list_type}/{name}` | DELETE | Remove item from list | `{ok: true}` |
| `/manifest.json` | GET | PWA manifest | JSON file |
| `/sw.js` | GET | Service worker | JS file |

**Query parameters for `/api/catalog`:**
- `category` -- filter by category (e.g., "Rifle", "Case", "Knife")
- `q` -- search within catalog (text match)
- `page` -- pagination (default 1)
- `per_page` -- items per page (default 50, max 100)
- `sort` -- price_asc, price_desc, name_asc (default: price_asc)
- `min_price` / `max_price` -- price range filter (USD)

## Frontend Architecture: Tab-Based Navigation

Current dashboard is a single view (hero stats -> search -> watchlist -> activity feed). v2 needs multiple views.

**Approach: Client-side tabs with hash routing**

```
#/watchlist    -- existing watchlist view (default)
#/catalog      -- full catalog with categories
#/favorites    -- personal favorites list
#/wishlist     -- wishlist
#/cases        -- case tracking (= catalog filtered to cases)
```

**Why hash routing, not separate pages:**
- Single HTML file already works. No reason to introduce multi-page routing.
- All data comes from API -- tab switch = different API call, same render pattern.
- Hash changes don't reload the page. Browser back/forward works.
- No build tools needed.

**Implementation pattern:**
```javascript
// Simple hash router
const routes = {
  '': renderWatchlist,
  '#/watchlist': renderWatchlist,
  '#/catalog': renderCatalog,
  '#/favorites': () => renderList('favorite'),
  '#/wishlist': () => renderList('wishlist'),
  '#/cases': () => renderCatalog('case'),
};

window.addEventListener('hashchange', () => {
  const route = routes[location.hash] || renderWatchlist;
  route();
});
```

**Tab bar (new HTML element, inserted after header):**
```html
<nav class="tabs">
  <a href="#/watchlist" class="tab active">Watchlist</a>
  <a href="#/catalog" class="tab">Catalog</a>
  <a href="#/favorites" class="tab">Favorites</a>
  <a href="#/wishlist" class="tab">Wishlist</a>
  <a href="#/cases" class="tab">Cases</a>
</nav>
```

**Catalog view -- lazy load with pagination:**
```
┌──────────────────────────────────────────────┐
│ [Categories sidebar]  │ [Item grid]          │
│                       │                      │
│  All (24,000)         │  ┌────┐ ┌────┐ ┌──┐ │
│  Rifle (2,100)        │  │card│ │card│ │  │ │
│  Pistol (1,800)       │  └────┘ └────┘ └──┘ │
│  Knife (1,500)        │  ┌────┐ ┌────┐ ┌──┐ │
│  Case (3,200)         │  │card│ │card│ │  │ │
│  Sticker (8,000)      │  └────┘ └────┘ └──┘ │
│  ...                  │                      │
│                       │  [< 1 2 3 ... 48 >]  │
└───────────────────────┴──────────────────────┘
```

**Each card shows:**
- Item name
- Current price (RUB)
- Stock count
- Heart button (toggle favorite)
- Star button (toggle wishlist)
- Click -> open detail modal (with chart, add to watchlist option)

## Data Flow Changes

### Current (v1.0):
```
Browser                    Server                  External
  |--- GET /api/watchlist -->|                        |
  |<-- {buy:[], sell:[]}  ---|                        |
  |--- GET /api/search?q= ->|                        |
  |<-- {results:[]}       ---|--- Steam Market API -->|
  |                          |<-- search results   ---|
  |                          |--- lis-skins JSON ---->| (every 5 min)
  |                          |<-- 24k items        ---|
```

### New (v2.0):
```
Browser                    Server                  External
  |--- GET /api/catalog?.. ->|                        |
  |<-- {items:[], total}  ---|                        |
  |                          |                        |
  |--- GET /api/lists/fav -->|                        |
  |<-- {items:[]}         ---|                        |
  |                          |                        |
  |--- POST /api/lists/.. -->|                        |
  |<-- {ok: true}         ---|                        |
  |                          |                        |
  |  (existing flows unchanged)                       |
  |                          |--- lis-skins JSON ---->| (every 5 min)
  |                          |<-- 24k items        ---|

Chrome Extension           Server
  |--- POST /api/lists/.. -->|
  |<-- {ok: true}         ---|
```

**Key point:** No new external data sources. Everything operates on the existing `_prices` dict and SQLite. The catalog endpoint just exposes what's already in memory.

## Build Order (dependency-driven)

```
Phase A: Category Parser + Catalog Endpoint
  ├── Add _parse_category() to server.py
  ├── Build _catalog_by_category index in _collect_once()
  ├── Add GET /api/catalog with pagination, filters, sort
  ├── Add GET /api/catalog/categories
  └── Verify: curl /api/catalog?category=rifle returns correct items
  
Phase B: Dual Lists (DB + API)
  ├── Add user_lists table to db.py init_db()
  ├── Add db functions: add_to_list, remove_from_list, get_list, get_list_names
  ├── Add API endpoints: GET/POST/DELETE /api/lists/{type}/{name}
  └── Verify: curl POST/GET/DELETE list operations work
  DEPENDS ON: nothing (parallel with Phase A)

Phase C: Dashboard Tabs + Catalog View
  ├── Add tab navigation bar to dashboard.html
  ├── Add hash router
  ├── Build catalog view (category sidebar + paginated grid)
  ├── Add favorite/wishlist toggle buttons on cards
  └── Verify: browsing catalog, switching tabs, toggling lists
  DEPENDS ON: Phase A + Phase B (needs both catalog and list APIs)

Phase D: Cases Tab
  ├── Cases tab = catalog view filtered to category=case
  ├── Possibly custom sort/display for cases
  └── Verify: cases tab shows ~3000 case items
  DEPENDS ON: Phase C (reuses catalog view)

Phase E: PWA
  ├── Create static/manifest.json
  ├── Create static/sw.js (minimal, cache shell only)
  ├── Create static/icons/ (192, 512 PNG)
  ├── Add meta tags to dashboard.html
  ├── Add SW registration to dashboard.html
  ├── Add routes in server.py (/manifest.json, /sw.js, mount /static)
  └── Verify: "Add to Home Screen" works on iPhone
  DEPENDS ON: Phase C (dashboard should be functional first)

Phase F: Chrome Extension
  ├── Create extension/manifest.json (Manifest V3)
  ├── Create extension/content.js (inject buttons on lis-skins)
  ├── Create extension/background.js (POST to dashboard API)
  ├── Test locally via chrome://extensions (Developer Mode)
  └── Verify: click button on lis-skins.com -> item appears in dashboard list
  DEPENDS ON: Phase B (needs list API endpoints)
```

**Parallel work possible:**
- Phase A and Phase B are independent -- can build simultaneously
- Phase E can be built any time after Phase C
- Phase F can be built any time after Phase B

**Critical path:** A -> C -> D (catalog must exist before views that use it)

## Anti-Patterns to Avoid

### Anti-Pattern: Loading all 24k items to browser
**What:** Dumping the entire catalog JSON to the frontend and filtering client-side.
**Why bad:** 3-5 MB transfer, DOM explosion rendering 24k cards, sluggish UX, pointless since server already has data in memory.
**Instead:** Server-side pagination. 50 items per page. Category filtering on server. Frontend renders only what's visible.

### Anti-Pattern: Storing catalog in SQLite
**What:** Inserting all 24k items into a `catalog` table and querying for catalog browsing.
**Why bad:** Duplicate data (items already in `_prices` dict). Writes 24k rows every 5 min for no reason. DB bloat.
**Instead:** Serve catalog from `_prices` dict (in-memory). DB is only for user data (watchlist, lists, price history).

### Anti-Pattern: Complex service worker caching
**What:** Caching API responses in service worker for offline access.
**Why bad:** Prices go stale in 5 minutes. Cached price data is misleading. Offline price dashboard is useless.
**Instead:** Cache only the app shell (HTML, CSS, icons, chart library). API calls always go to network.

### Anti-Pattern: Extension popup instead of content script
**What:** Building the extension as a popup that opens a mini-dashboard.
**Why bad:** User has to open popup, search for item, then add. Defeats the purpose.
**Instead:** Content script injects buttons directly on lis-skins.com item pages. One click to add.

## Performance Considerations

| Concern | Approach | Expected Performance |
|---------|----------|---------------------|
| Catalog pagination (24k items) | Server-side filter + slice from `_prices` dict | <10ms per request (dict operations, no DB) |
| Category classification | Run once per collect cycle (every 5 min) | ~50ms for 24k items (string prefix matching) |
| List toggle (favorite/wishlist) | SQLite INSERT/DELETE | <5ms (single row operation) |
| List status check on catalog load | One `GET /api/lists/favorite` returns all names -> cache as Set | O(1) lookup per card |
| PWA install | manifest.json + minimal SW | ~5KB total new assets |
| Chrome extension | Content script injects 1-2 buttons | Negligible DOM overhead |

## Sources

- [FastAPI Static Files docs](https://fastapi.tiangolo.com/tutorial/static-files/) -- StaticFiles mounting pattern (HIGH confidence)
- [Chrome Extensions Manifest V3](https://developer.chrome.com/docs/extensions/develop/migrate/what-is-mv3) -- extension architecture (HIGH confidence)
- [MDN PWA Service Workers tutorial](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Tutorials/js13kGames/Offline_Service_workers) -- SW caching strategies (HIGH confidence)
- [PWA Minimus checklist](https://mobiforge.com/design-development/pwa-minimus-a-minimal-pwa-checklist) -- minimal PWA requirements (MEDIUM confidence)
- [SQLite pagination techniques](https://sqlite.work/optimizing-row-number-and-pagination-performance-in-sqlite-queries/) -- LIMIT/OFFSET patterns (HIGH confidence)
- [ByMykel/CSGO-API](https://github.com/ByMykel/CSGO-API) -- CS2 item categories reference (MEDIUM confidence)
- CS2 weapon naming patterns from [cs.money](https://cs.money/blog/cs-go-skins/skins-rarity-types-in-cs2/) and [totalcsgo.com](https://totalcsgo.com/skins/weapons) (MEDIUM confidence)
