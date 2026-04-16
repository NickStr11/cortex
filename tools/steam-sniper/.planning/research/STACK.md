# Stack Research: v2.0 Additions

**Project:** Steam Sniper Dashboard
**Researched:** 2026-04-13
**Confidence:** HIGH
**Scope:** Only NEW stack additions for v2.0 milestone. Existing stack (FastAPI, SQLite, vanilla JS, TradingView LC, Telegram bot) is validated and unchanged.

## What's New in v2.0

Four capabilities that need stack decisions:

1. **Catalog browsing** -- 24k items, categories, filtering, pagination
2. **Dual lists** -- favorites (have) + wishlist (want to buy) in SQLite
3. **PWA** -- manifest + service worker for iPhone home screen
4. **Chrome extension** -- Manifest V3, inject button on lis-skins.com pages

## Stack Additions

### Backend: Zero New Dependencies

No new Python packages needed. Everything is achievable with existing FastAPI + sqlite3.

| What | How | Why No New Dep |
|------|-----|----------------|
| Catalog API (paginated) | `GET /api/catalog?page=1&per_page=50&category=rifle&q=ak-47` | Simple OFFSET/LIMIT on in-memory `_prices` dict. 24k items filter in <5ms in Python. |
| Category extraction | Parse item name: `"AK-47 \| Redline (Field-Tested)"` -> weapon=AK-47, wear=FT | Regex, 5 lines of code. CS2 naming is predictable: `WEAPON \| SKIN (WEAR)` for weapons, `★ Knife`, `★ Gloves` for specials. |
| Dual list endpoints | `POST /api/lists/{list_type}`, `DELETE`, `GET` | Existing `db.py` pattern. New table, same sqlite3 approach. |
| PWA static files | `app.mount("/static", StaticFiles(...))` | Already available via `fastapi.staticfiles`. |
| Chrome extension API | `POST /api/lists/add-from-extension` with CORS | Existing CORS middleware (`allow_origins=["*"]`) already covers this. |

**Why not FTS5:** 24k items fit in memory (~15MB). The server already loads all items into `_prices` dict. Server-side filtering on this dict is instant. FTS5 would require maintaining a separate virtual table for data that refreshes every 5 minutes. Overengineering.

**Why not fastapi-pagination:** Our pagination is trivial (slice a filtered list, return total count). Adding a library for `items[offset:offset+limit]` is absurd.

### Frontend: Two Small Additions

| Technology | How Added | Purpose | Why |
|------------|-----------|---------|-----|
| Virtual scroll (custom, ~80 lines) | Inline in dashboard.html | Render 24k catalog items without creating 24k DOM nodes | Only render visible rows (~20-30) + buffer. Fixed-height rows make calculation trivial. No library needed -- the pattern is `scrollTop / rowHeight = startIndex`. |
| Debounced search input | Inline, ~10 lines | Prevent API spam while typing in catalog search | `setTimeout` + `clearTimeout`. Standard pattern. |

**Why not a virtual scroll library (HyperList, etc.):** Our items are fixed-height cards in a grid. The math is `visibleStart = Math.floor(scrollTop / cardHeight)`. A library adds a dependency for what's genuinely 80 lines of vanilla JS. If items were variable height, we'd need a library.

**Why not Web Workers for filtering:** 24k items * ~100 bytes = ~2.4MB. `Array.filter()` on this takes <10ms on any modern device. Web Workers add complexity (message passing, serialization) for a problem that doesn't exist.

### PWA: manifest.json + service-worker.js (No Dependencies)

PWA requires no npm packages, no build tools, no frameworks. It's two static files + a few meta tags.

| File | Purpose | Size |
|------|---------|------|
| `static/manifest.json` | App metadata for "Add to Home Screen" | ~20 lines JSON |
| `static/sw.js` | Cache dashboard shell for instant load | ~40 lines JS |
| `static/icon-192.png` | PWA icon (required minimum) | 1 file |
| `static/icon-512.png` | PWA icon (splash screen) | 1 file |
| `static/apple-touch-icon.png` | iOS home screen icon (180x180) | 1 file |

**Manifest minimal config:**
```json
{
  "name": "Steam Sniper",
  "short_name": "Sniper",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#060a12",
  "theme_color": "#ff906a",
  "icons": [
    { "src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

**Service worker strategy: Network-First for API, Cache-First for shell.**

```javascript
// sw.js -- ~40 lines
const CACHE = 'sniper-v1';
const SHELL = ['/', '/static/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)));
});

self.addEventListener('fetch', e => {
  if (e.request.url.includes('/api/')) return; // APIs always go to network
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
```

**iOS-specific meta tags (in dashboard.html `<head>`):**
```html
<link rel="manifest" href="/static/manifest.json">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Steam Sniper">
<link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
```

**iOS PWA caveats (2025-2026):**
- iOS 16.4+ supports push notifications in PWAs, but we don't need them (Telegram bot handles alerts)
- Storage quota ~50MB, aggressively evicted after 7 days of non-use. Fine -- our cache is just the HTML shell
- No background sync. Fine -- real-time data comes from API on each open
- HTTPS required for service worker. If VPS is HTTP-only, service worker won't register on iPhone. **HTTPS via nginx + Let's Encrypt becomes mandatory for PWA on iPhone.**

### Chrome Extension: Manifest V3 (Pure JS, No Build Tools)

Standalone directory, not bundled into the Python project. Ships as unpacked extension (2 users, no Chrome Web Store needed).

| File | Purpose |
|------|---------|
| `extension/manifest.json` | Manifest V3 config |
| `extension/content.js` | Inject "Add to Sniper" button on lis-skins.com item pages |
| `extension/icon-48.png` | Extension icon |
| `extension/icon-128.png` | Extension icon |

**Manifest V3 config:**
```json
{
  "manifest_version": 3,
  "name": "Steam Sniper",
  "version": "1.0",
  "description": "Add items from lis-skins.com to Steam Sniper dashboard",
  "permissions": ["activeTab"],
  "content_scripts": [{
    "matches": ["*://lis-skins.com/*"],
    "js": ["content.js"],
    "css": []
  }],
  "icons": {
    "48": "icon-48.png",
    "128": "icon-128.png"
  }
}
```

**Content script approach:**
1. Detect item page on lis-skins.com (URL pattern or DOM selector)
2. Extract item name from page title / DOM element
3. Inject floating button "Add to Sniper" in corner
4. On click: `fetch("http://VPS_IP:8100/api/lists/wishlist", { method: "POST", body: { name: itemName } })`
5. Show success/error toast

**Key decisions:**
- `"permissions": ["activeTab"]` -- minimal permissions, no broad host access
- Content script auto-injects on `lis-skins.com/*` -- no popup needed
- Direct API call to VPS -- no background service worker needed for the extension
- Extension NOT published to Chrome Web Store -- loaded as unpacked via `chrome://extensions`

**Lis-skins.com DOM:** Exact selectors need to be discovered by inspecting the site. Item name is reliably in the page title and likely in an `<h1>` or similar. The content script should be defensive (check if element exists before injecting).

## SQLite Schema Additions

### New table: `user_lists`

```sql
CREATE TABLE IF NOT EXISTS user_lists (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,          -- exact lis-skins item name
    name_lower  TEXT NOT NULL,          -- lowercase for matching
    list_type   TEXT NOT NULL CHECK(list_type IN ('favorite', 'wishlist')),
    user_id     TEXT NOT NULL DEFAULT 'default',  -- 'nikita' or 'lesha'
    added_at    TEXT NOT NULL DEFAULT (datetime('now')),
    notes       TEXT,                   -- optional user notes
    UNIQUE(name_lower, list_type, user_id)
);
CREATE INDEX IF NOT EXISTS idx_lists_user_type ON user_lists(user_id, list_type);
```

**Why separate from `watchlist` table:**
- `watchlist` has price targets, alert logic, buy/sell semantics
- `user_lists` is simple bookmarking -- no targets, no alerts
- Different query patterns: watchlist joins with price_history for alerts; user_lists just tags items
- Mixing them would require `list_type IN ('buy', 'sell', 'favorite', 'wishlist')` and make the alert logic messier

**Why `user_id` as TEXT, not a users table:**
- Two users, no auth. `user_id` is passed as query param or header (e.g., `?user=lesha`)
- No user registration, no passwords. A foreign key to a users table is overengineering for 2 hardcoded users

## Catalog Browsing Architecture

### Data Flow (server side)

```
lis-skins JSON (every 5 min) -> _prices dict (24k items in memory)
                                      |
                                      v
GET /api/catalog?category=rifle&q=ak&page=1&per_page=50&sort=price_asc
                                      |
                                      v
                              1. Filter _prices by category regex
                              2. Filter by search query (substring match)
                              3. Sort (price, name, count)
                              4. Slice [offset:offset+limit]
                              5. Return {items: [...], total: N, page: 1}
```

### Category Parsing from Item Names

CS2 item names follow predictable patterns:

| Pattern | Category | Example |
|---------|----------|---------|
| `★ Karambit \| ...` | Knives | `★ Karambit \| Doppler (Factory New)` |
| `★ Sport Gloves \| ...` | Gloves | `★ Sport Gloves \| Hedge Maze (Field-Tested)` |
| `AK-47 \| ...` | Rifles | `AK-47 \| Redline (Field-Tested)` |
| `Sticker \| ...` | Stickers | `Sticker \| Cloud9 (Holo) \| Katowice 2014` |
| `...Case` | Cases | `Kilowatt Case` |
| `USP-S \| ...` | Pistols | `USP-S \| Kill Confirmed (Minimal Wear)` |
| `M4A4 \| ...` | Rifles | `M4A4 \| Howl (Factory New)` |

Build a static `WEAPON_TO_CATEGORY` dict mapping ~30 weapon names to categories (Rifles, Pistols, SMGs, Heavy, Knives, Gloves). Stickers/Cases/Agents detected by prefix/suffix. This is more reliable than regex because CS2 weapon names are a closed set.

### Wear condition parsing

Extract from parentheses at end of name:
- `(Factory New)` -> FN
- `(Minimal Wear)` -> MW
- `(Field-Tested)` -> FT
- `(Well-Worn)` -> WW
- `(Battle-Scarred)` -> BS
- No parentheses -> N/A (stickers, cases, agents)

## File Structure (v2.0 target)

```
tools/steam-sniper/
  main.py              # Telegram bot (existing, unchanged)
  server.py            # FastAPI app (extend with catalog + lists endpoints)
  db.py                # SQLite (add user_lists table + helpers)
  dashboard.html       # Single-file dashboard (extend with catalog tab)
  static/
    manifest.json      # PWA manifest
    sw.js              # Service worker
    icon-192.png       # PWA icon
    icon-512.png       # PWA splash icon
    apple-touch-icon.png  # iOS icon (180x180)
  extension/
    manifest.json      # Chrome extension Manifest V3
    content.js         # Content script for lis-skins.com
    icon-48.png        # Extension icon
    icon-128.png       # Extension icon
  data/
    sniper.db          # SQLite database
  pyproject.toml       # No new deps needed
```

## What NOT to Add

| Temptation | Why Resist |
|------------|------------|
| Elasticsearch / MeiliSearch | 24k items, substring search. `Array.filter()` or Python list comp handles this in <10ms. A search engine is insane overkill. |
| SQLite FTS5 | Data lives in memory (_prices dict), refreshes every 5 min. FTS5 would index stale data and add sync complexity. |
| fastapi-pagination | `items[offset:offset+limit]` is not a library-worthy problem. |
| Workbox (Google's SW toolkit) | Our service worker is 40 lines. Workbox is 50KB+ of abstractions for complex caching strategies we don't need. |
| Any PWA framework (Vite PWA plugin, etc.) | No build tooling. Two static files. |
| React/Vue for Chrome extension | Content script injects one button. Vanilla JS. |
| HTTPS certificate (for PWA) | **Actually, this IS needed.** Service workers require HTTPS on iOS. Add nginx + Let's Encrypt. But that's infra, not stack. |
| WebSocket for extension->server | Extension makes one POST request per user action. HTTP fetch is perfect. |
| User auth system | 2 users, private VPS. `?user=lesha` query param is sufficient. |
| IndexedDB for client-side caching | 24k items = ~2.4MB. Just re-fetch on page load. Not worth the complexity of managing a client-side cache that goes stale every 5 minutes. |

## HTTPS Requirement (Infra Note)

PWA service workers require a secure context (HTTPS or localhost). The VPS currently serves HTTP on :8100.

**For PWA to work on iPhone:**
```
nginx (port 443, HTTPS) -> proxy_pass http://127.0.0.1:8100
```

Use certbot + Let's Encrypt for free HTTPS cert. Needs a domain (even a free one like `sniper.example.com`) or use a Cloudflare tunnel.

**Alternative:** Skip service worker on iPhone, just use manifest for "Add to Home Screen" icon. The app works fine without offline caching -- it needs live price data anyway. BUT: iOS Safari still requires HTTPS for `manifest.json` to trigger the install prompt in modern versions.

**Pragmatic choice:** Set up nginx + Let's Encrypt. It's a one-time 10-minute task and unblocks PWA properly.

## Version Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| FastAPI | >=0.115 (existing) | StaticFiles available since early versions. No upgrade needed. |
| Python | >=3.12 (existing) | All features used are standard library. |
| SQLite | >=3.37 (system) | `STRICT` tables available but not required. WAL mode works on all modern versions. |
| Chrome | Manifest V3 | Supported since Chrome 88 (2021). Current stable is 130+. |
| iOS Safari | 16.4+ | PWA install prompt + push notifications. iPhone must be on iOS 16.4+ (March 2023). |

## Sources

- [MDN PWA Installable Guide](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable) -- HIGH confidence
- [Chrome Manifest V3 Content Scripts](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts) -- HIGH confidence
- [FastAPI Static Files](https://fastapi.tiangolo.com/tutorial/static-files/) -- HIGH confidence
- [SQLite FTS5 docs](https://www.sqlite.org/fts5.html) -- HIGH confidence (referenced to justify NOT using it)
- [PWA iOS Limitations 2026](https://www.magicbell.com/blog/pwa-ios-limitations-safari-support-complete-guide) -- MEDIUM confidence
- [PWA Icon Requirements 2025](https://dev.to/albert_nahas_cdc8469a6ae8/pwa-icon-requirements-the-complete-2025-checklist-i3g) -- MEDIUM confidence
- [Virtual Scrolling in Vanilla JS](https://sergimansilla.com/blog/virtual-scrolling/) -- MEDIUM confidence

---
*Stack research for: Steam Sniper v2.0 milestone*
*Researched: 2026-04-13*
