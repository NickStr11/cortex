# Pitfalls Research

**Domain:** CS2 skin tracker v2.0 -- catalog browsing, dual lists, PWA, Chrome extension on existing FastAPI + vanilla JS + SQLite
**Researched:** 2026-04-13
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Rendering 24k catalog items kills the browser

**What goes wrong:**
The current dashboard renders watchlist items (maybe 20-50 cards) by building an HTML string and setting `innerHTML`. Applying the same approach to the full lis-skins catalog (24,000 items) creates 24k DOM nodes. The browser freezes for 5-10 seconds, mobile Safari crashes entirely. Even filtering to a category still leaves 3,000-5,000 items. The dashboard.html is already 1,373 lines -- adding catalog rendering logic bloats it further.

**Why it happens:**
Developers test with a filtered view (100 items), it works great. Then someone opens "All Weapons" and the tab dies. DOM nodes are heavyweight objects -- each card with 10+ child elements means 240k+ DOM nodes.

**How to avoid:**
1. Server-side pagination: `/api/catalog?category=rifle&page=1&limit=50`. Never send more than 50-100 items per request
2. Infinite scroll with lazy loading: render next batch on scroll threshold, not all at once
3. If you need fast scroll through thousands: virtual scrolling (only render visible viewport + buffer). Libraries: `hyperlist` (12KB, no deps) or hand-roll in ~150 lines of vanilla JS
4. API must support `offset`/`limit` from day one -- retrofitting pagination into a "return everything" API is painful
5. Keep the in-memory `_prices` dict on the server (already there), but never dump it wholesale to the client

**Warning signs:**
- Browser DevTools shows >5000 DOM nodes in Elements panel
- `Time to Interactive` exceeds 3 seconds on page load
- Mobile users reporting white screen after opening catalog

**Phase to address:**
Phase 1 (Catalog API + browsing). Pagination is an API design decision that must be made before any frontend code.

---

### Pitfall 2: Category classification regex breaks on CS2 naming edge cases

**What goes wrong:**
CS2 item names follow patterns but with numerous exceptions that break naive parsing:

| Pattern | Example | Edge case |
|---------|---------|-----------|
| `Weapon | Skin (Wear)` | `AK-47 \| Redline (Field-Tested)` | Standard |
| StatTrak prefix | `StatTrak\u2122 AK-47 \| Redline (Field-Tested)` | `\u2122` is a special char |
| Souvenir prefix | `Souvenir M4A1-S \| Hyper Beast (Minimal Wear)` | Mutually exclusive with StatTrak |
| Star knives | `\u2605 Karambit \| Doppler (Factory New)` | `\u2605` star symbol |
| Star + StatTrak | `\u2605 StatTrak\u2122 Butterfly Knife \| Fade (Factory New)` | Both prefixes |
| Vanilla knives | `\u2605 Karambit` | NO skin name, NO wear |
| Gloves | `\u2605 Sport Gloves \| Superconductor (Field-Tested)` | Star prefix, "Gloves" not "Knife" |
| Agents | `Cmdr. Frank "Wet Sox" Baroud \| SEAL Frogman` | Quotes, no wear |
| Stickers | `Sticker \| NaVi (Holo) \| Katowice 2014` | Multiple pipes, parentheses are NOT wear |
| Cases | `Kilowatt Case` | No pipe, no wear, no parentheses |
| Graffiti | `Sealed Graffiti \| Crown (Tiger Orange)` | Parentheses = color, not wear |
| Music kits | `StatTrak\u2122 Music Kit \| Austin Wintory, Desert Walk` | Comma in name |
| Patches | `Patch \| Trident` | Simple format but distinct category |
| Keys | `Kilowatt Case Key` | Must NOT be classified as a case |

A regex like `^(StatTrak.*)?\s*(.*?)\s*\|\s*(.*?)\s*\((.*?)\)$` fails on at least 6 of these patterns.

**Why it happens:**
CS2's naming is organic, accumulated over 12 years. No single regex covers all patterns. Developers test with the 10 most common items (rifles, pistols, knives), deploy, and then stickers/agents/music kits all miscategorize.

**How to avoid:**
1. Don't classify by regex alone. Use a category lookup table (weapon type -> items that match) rather than parsing the name
2. Start simple: a `CATEGORY_PREFIXES` dict that catches 90% of items:
   ```python
   CATEGORIES = {
       "Rifle": ["AK-47", "M4A1-S", "M4A4", "AWP", "FAMAS", ...],
       "Pistol": ["Glock-18", "USP-S", "Desert Eagle", ...],
       "Knife": ["Karambit", "Butterfly Knife", "Bayonet", ...],
       "Gloves": ["Sport Gloves", "Specialist Gloves", ...],
       "Case": items ending with "Case" but NOT "Case Key",
       "Key": items ending with "Case Key",
       "Sticker": items starting with "Sticker |",
       "Agent": known agent names (finite list),
   }
   ```
3. Handle the `\u2605` (star) and `StatTrak\u2122` prefixes by stripping them BEFORE category matching
4. Wear parsing: ONLY apply to items with `|` separator. The 5 valid wears are: Factory New, Minimal Wear, Field-Tested, Well-Worn, Battle-Scarred. Anything in parentheses that isn't one of these 5 strings is NOT a wear level
5. Use the ByMykel/CSGO-API (https://bymykel.github.io/CSGO-API/) as a reference dataset for all item types -- it has category metadata already mapped

**Warning signs:**
- "Unknown" or "Other" category contains more than 5% of items
- Stickers appearing in "Weapon" category
- Cases classified as "Rifle" because they contain a weapon name
- Vanilla knives (no skin name) not appearing in "Knife" category

**Phase to address:**
Phase 1 (Catalog + categories). The classification function must exist before catalog browsing UI.

---

### Pitfall 3: Dual list migration breaks existing watchlist behavior

**What goes wrong:**
Current schema has `watchlist` table with `type IN ('buy', 'sell')` where `buy` = "alert when price drops below target" and `sell` = "alert when price rises above target". The v2.0 introduces two NEW lists: "favorites" (items I own) and "wishlist" (items I want to buy). These are NOT the same as buy/sell alerts -- they're organizational, not price-trigger-based.

If you try to repurpose `buy` -> `wishlist` and `sell` -> `favorites`, the semantics break: a "favorites" item still needs buy/sell alert capability. If you add new tables, the Telegram bot's alert logic needs updating. If you add a `list_type` column, existing queries break.

**Why it happens:**
The dual list concept conflates two orthogonal dimensions:
1. **Organization** -- which list does this belong to? (favorites vs wishlist)
2. **Alert type** -- what price direction triggers notification? (buy below vs sell above)

An item in "favorites" (I own it) could have a SELL alert. An item in "wishlist" (I want it) could have a BUY alert. But an item in wishlist could also have NO alert (just tracking).

**How to avoid:**
1. Keep the existing `watchlist` table for ALERT items (buy/sell with target prices)
2. Add a NEW `user_lists` table for organization:
   ```sql
   CREATE TABLE user_lists (
       id INTEGER PRIMARY KEY,
       name_lower TEXT NOT NULL,
       list_type TEXT NOT NULL CHECK(list_type IN ('favorite', 'wishlist')),
       user TEXT DEFAULT 'default',
       added_at TEXT NOT NULL,
       UNIQUE(name_lower, list_type, user)
   );
   ```
3. An item can be in user_lists WITHOUT being in watchlist (no alert)
4. An item can be in BOTH user_lists and watchlist (organizational + alert)
5. The dashboard shows items from user_lists, with alert indicators from watchlist
6. The Telegram bot continues to work with watchlist only -- zero changes needed
7. Add a `user` column from the start (even if only 'nikita' and 'lesha') -- you know there are 2 users

**Warning signs:**
- "Add to favorites" also creating an alert
- Items disappearing from watchlist after adding to favorites
- Telegram bot sending alerts for items that user just bookmarked without setting a target

**Phase to address:**
Phase 2 (Dual lists). Schema migration must be additive (new table), not destructive (altering existing).

---

### Pitfall 4: 1,373-line dashboard.html becomes unmaintainable with catalog + filters + tabs

**What goes wrong:**
The current `dashboard.html` is a single file with inline CSS (766 lines), HTML structure (130 lines), and JavaScript (480 lines). Adding catalog browsing, category filters, dual list tabs, case tracking tab, search refinements, and PWA registration could easily triple this to 4,000+ lines. At that size:
- Every change risks breaking unrelated features (no module boundaries)
- Two developers can't work on different features simultaneously
- Finding the bug in the filter logic requires scrolling past 2,000 lines of CSS
- No test coverage possible for any JS logic

**Why it happens:**
"I'll just add one more feature to the same file" -- works for v1.0, death by a thousand cuts in v2.0. The monolith HTML file pattern breaks around 1,500-2,000 lines.

**How to avoid:**
1. Split NOW, before adding any v2.0 features:
   - `static/style.css` -- all CSS
   - `static/app.js` -- main entry, init, routing between tabs
   - `static/catalog.js` -- catalog rendering, filtering, pagination
   - `static/lists.js` -- favorites + wishlist rendering
   - `static/chart.js` -- TradingView chart logic (already 90 lines, will grow)
   - `static/search.js` -- search with debounce, results rendering
   - `index.html` -- just structure, `<script type="module">` imports
2. Use ES modules (`import`/`export`) -- no build step needed, works in all modern browsers
3. Shared state (usdRub, current tab, etc.) in a simple `state.js` module
4. FastAPI already handles `StaticFiles` -- just add `app.mount("/static", StaticFiles(directory="static"))` to server.py
5. Don't reach for a framework. Vanilla JS with modules is fine for 2 users

**Warning signs:**
- Adding a feature requires reading through 500+ lines of unrelated code
- "I changed the CSS for catalog and now the watchlist cards look broken"
- Two features use the same variable name and silently conflict
- Ctrl+F for a function name returns 15+ results

**Phase to address:**
Phase 0 / prep work. Split the file BEFORE starting any v2.0 feature. This is a 1-2 hour task that saves dozens of hours.

---

### Pitfall 5: PWA service worker caching serves stale dashboard forever

**What goes wrong:**
You add a `manifest.json` and a `sw.js` that caches `index.html`, CSS, and JS files. The PWA installs beautifully on Lesha's iPhone. Then you deploy a bugfix. Lesha opens the app and still sees the old version. He force-closes and reopens -- still old. The service worker cached the old files and is serving them. The only fix is to clear Safari's website data manually, which non-technical users won't know how to do.

**Why it happens:**
Service workers are persistent. A new service worker won't activate until ALL tabs using the old one are closed. On iOS, PWAs opened from home screen are a single persistent tab that may never fully close. Cache invalidation is hard, and the default service worker patterns (cache-first) prioritize offline availability over freshness.

**How to avoid:**
1. Use a `network-first` strategy for HTML and API calls, `cache-first` only for static assets (fonts, icons)
2. Version your cache: `const CACHE_VERSION = 'v2.1'`. On activate, delete all caches that aren't the current version
3. In `sw.js`, call `self.skipWaiting()` in the install event -- this forces immediate activation
4. In `app.js`, listen for `controllerchange` event and reload:
   ```js
   navigator.serviceWorker.addEventListener('controllerchange', () => {
       window.location.reload();
   });
   ```
5. Add a version check: on every page load, fetch `/api/version` and compare to the cached version. If different, show "Update available" toast
6. Keep the service worker SIMPLE: only cache the manifest icon and offline fallback page. For a dashboard that always needs fresh data, aggressive caching is an anti-pattern
7. **iOS-specific**: Safari limits PWA cache to 50MB. Don't precache the TradingView Lightweight Charts library (400KB+) and all fonts -- be selective

**Warning signs:**
- After deploy, you see the new version but Lesha still sees the old one
- DevTools > Application > Service Workers shows "waiting to activate"
- Users report "it was working yesterday, now it shows old data"

**Phase to address:**
Phase 4 (PWA). But the service worker strategy must be decided before writing any caching code. Start with manifest-only PWA (home screen icon, no caching), add service worker caching later.

---

### Pitfall 6: Chrome extension CORS and protocol mismatch with self-hosted API

**What goes wrong:**
The Chrome extension on lis-skins.com needs to communicate with the dashboard API at `http://194.87.140.204:8100/api/`. Two problems:
1. Lis-skins uses HTTPS. The extension tries to fetch from HTTP. Mixed content blocks the request silently -- no error in the content script, just a failed fetch
2. Even if the API had HTTPS, the extension's content script runs in the page's origin (lis-skins.com). Fetches from content scripts are subject to CORS. The dashboard API has `allow_origins=["*"]` but this may not be enough for extensions in Manifest V3

**Why it happens:**
Manifest V3 changed how extensions handle cross-origin requests. Content scripts can no longer bypass CORS. API calls must be routed through the extension's background service worker, which has the `host_permissions` to bypass CORS.

**How to avoid:**
1. Extension architecture: content script extracts item data from lis-skins page -> sends message to background service worker -> background SW makes API call to dashboard -> returns result to content script
2. `manifest.json` must include:
   ```json
   {
       "host_permissions": ["http://194.87.140.204:8100/*"],
       "permissions": ["activeTab"]
   }
   ```
3. CRITICAL: the host permission must use `http://` (not `https://`) because the dashboard API doesn't have TLS. A missing trailing `/*` or wrong protocol silently fails
4. Consider adding TLS to the dashboard (Let's Encrypt + nginx reverse proxy on VPS) to avoid mixed content issues entirely. This also makes the PWA more reliable
5. For development: Chrome allows extensions to access `http://localhost` without host_permissions, but `http://194.87.140.204` is NOT localhost -- you need explicit permissions
6. The extension should store the API URL in `chrome.storage.sync` so it can be configured without rebuilding

**Warning signs:**
- Extension "add to dashboard" button does nothing (no error visible to user)
- Browser console shows "Mixed Content: The page was loaded over HTTPS, but requested an insecure resource"
- Extension works in development (localhost) but fails in production (VPS IP)

**Phase to address:**
Phase 5 (Chrome extension). But the decision about TLS on the dashboard API affects both PWA and extension -- decide in Phase 4.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Full catalog in `_prices` dict (in-memory, 24k items) | Fast lookups, simple code | ~50MB RAM, rebuilt every 5 min from scratch | Acceptable for 2 users on VPS with 1GB+ RAM |
| All CSS/JS in single HTML file | Zero build step, easy to deploy | Unmaintainable at 2000+ lines, blocks parallel work | Never for v2.0 -- split before starting |
| No user identification (no auth) | Simple, no login friction | Can't separate favorites/wishlists per user, can't do "my items" | Acceptable if using `user` column with hardcoded names in API calls |
| `allow_origins=["*"]` CORS | Works immediately | Any website can call your API, trivial to scrape your data | Acceptable for private VPS URL, but restrict to known origins if extension is added |
| Storing 24k items only in memory (no catalog table) | No DB writes for catalog, fast | Catalog not searchable when server restarts until first fetch completes | Acceptable -- first fetch happens on startup |
| Manual category classification (hardcoded dict) | Quick to implement, easy to debug | New CS2 items/categories require code changes | Acceptable for years -- CS2 weapon types rarely change, cases change monthly but pattern is trivial |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Lis-skins JSON + catalog DB | Storing all 24k items in SQLite every 5 min (288 full writes/day) | Keep catalog in memory only. SQLite for user data (lists, alerts, history). Catalog is ephemeral, refreshed from source |
| Telegram bot + dual lists | Bot tries to manage favorites/wishlist with existing `/add` command, confusing UX | Bot manages alerts only (watchlist). Dashboard manages organization (favorites/wishlist). Clean separation of concerns |
| Chrome extension + dashboard API | Extension sends item name as string, but name on lis-skins page is in Russian while catalog uses English names | Extension should send the lis-skins URL, dashboard API extracts item by URL match, not name match |
| PWA + service worker + live prices | Service worker caches API responses, user sees stale prices | Never cache `/api/*` routes in service worker. Cache only static assets. API calls always go to network |
| Steam Market search API + search | Making 3 sequential HTTP requests to Steam per search query (current impl), each with 8s timeout | Acceptable for rare searches, but catalog browsing should NOT use Steam API. Catalog search = search `_prices` dict (already in memory) |
| TradingView Charts + dual list items | Chart shows only items in old watchlist, not items from favorites/wishlist | Chart should work for ANY item (watchlist, favorites, wishlist, or raw catalog search). Price history exists for watchlist items; for others, show "no history yet" |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Rendering 3000+ case items without pagination | Page freeze, high CPU, mobile crash | Server-side pagination + infinite scroll | >500 DOM cards simultaneously |
| Linear search through 24k `_prices` dict for catalog filtering | 50-200ms per filter change, noticeable lag | Pre-index by category on server: `_catalog_by_category = defaultdict(list)` | >10k items with substring matching |
| Loading all favorites + wishlist + watchlist in one API call | Slow initial load as lists grow | Separate endpoints: `/api/favorites`, `/api/wishlist`, load active tab only | >200 items across all lists |
| Price history queries without LIMIT | Chart API returns 50k+ points for "all" timeframe | Always LIMIT server-side, downsample for long timeframes | >30 days of 5-min snapshots |
| Re-rendering entire card grid on any state change | Visible flicker, scroll position reset | Incremental DOM updates: only update changed cards, or use a simple diffing approach | >50 cards visible |
| Fetching Steam Market API during catalog browse | 24s timeout (3 pages x 8s each), blocks UI | Catalog browse uses in-memory `_prices` only. Steam API only for explicit Russian-language search | Any catalog pagination |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Dashboard API on HTTP without TLS | Anyone on the network can see/modify requests. VPS IP in extension manifest is public | Add nginx + Let's Encrypt for HTTPS. Minimal effort, high payoff for PWA and extension |
| `allow_origins=["*"]` with no auth | Anyone who discovers the VPS URL can add/remove items from watchlist, read all data | Restrict CORS to specific origins. Add a simple API key header (`X-Api-Key`) checked in middleware |
| Chrome extension hardcoding VPS IP | If IP changes, extension breaks. IP is visible in extension source code (reviewable by anyone) | Store API URL in `chrome.storage.sync`, set via extension options page |
| No rate limiting on API endpoints | A script could spam `/api/watchlist` POST, filling the DB | Add simple rate limiting: `slowapi` or manual counter (100 req/min per IP is plenty for 2 users) |
| SQLite DB file accessible via web | If someone guesses the path, they download the entire database | FastAPI serves only `/` and `/api/*` routes. Never mount `data/` as static files. Verify with `curl` |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Catalog and watchlist look identical (same card design) | User can't tell if they're browsing catalog or their list | Visual distinction: catalog cards are compact rows, list cards are detailed cards. Different background color for active tab |
| Adding to favorites requires opening a modal with target price fields | Friction for organizational action (not setting an alert) | "Heart" button on catalog card = instant add to favorites. Alert setup is separate, opt-in step |
| No indication which catalog items are already in a list | User adds the same item twice, or can't find their items in 24k catalog | Show heart/star icons on catalog cards that are already in favorites/wishlist. Filter: "Show only my items" |
| Category filter resets when navigating between tabs | User filters rifles, switches to wishlist tab, comes back, filter is gone | Persist filter state per tab in JS (or URL hash). Category filter is part of the tab state |
| Case tracking tab shows ALL 3000 cases/capsules/keys with no hierarchy | Overwhelming, no useful browsing | Group by: Active Drop Cases, Discontinued Cases, Sticker Capsules, Souvenir Packages. Default view: Active Drop Cases only |
| PWA icon opens to catalog instead of user's list | User wants to quickly check their items, not browse 24k catalog | Default PWA landing = last viewed tab (persist in localStorage). First-time: favorites tab if populated, else catalog |

## "Looks Done But Isn't" Checklist

- [ ] **Catalog pagination:** "Works on desktop" but not tested on iPhone Safari (viewport height calculation differs in PWA mode)
- [ ] **Category classification:** Tested with weapons/knives but not stickers/agents/music kits/patches/graffiti (these are ~30% of 24k items)
- [ ] **Dual lists:** Items can be added to lists but no way to MOVE between lists (favorites -> wishlist or vice versa)
- [ ] **Dual lists:** What happens when an item in favorites is also in watchlist with sell alert, and user removes from favorites? Alert should survive
- [ ] **PWA manifest:** Icons provided in multiple sizes (192x192 + 512x512 minimum). Missing sizes = generic icon on home screen
- [ ] **PWA on iOS:** `apple-touch-icon` meta tag set, `apple-mobile-web-app-capable` set, status bar style configured. Without these, iOS ignores the manifest
- [ ] **Chrome extension:** Tested on lis-skins.com item page AND search results page AND main catalog page -- DOM selectors differ between pages
- [ ] **Case tracking:** Cases and keys are separate items but visually linked. "Kilowatt Case" and "Kilowatt Case Key" should appear together, not in separate categories
- [ ] **Search:** Russian search still works (via Steam API) when catalog browse uses English names from lis-skins JSON
- [ ] **Mobile responsive:** Card grid works on 375px width (iPhone SE). Current grid might overflow with longer Russian display names
- [ ] **Rate conversion:** Items added to favorites store the price at time of addition (for "how much has it changed since I bookmarked it")

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Service worker caching stale version | LOW | Deploy new sw.js with incremented CACHE_VERSION. Users who can't update: instruct to clear Safari website data |
| Catalog rendering freezes browser | LOW | Add `?limit=50` to API endpoint, update frontend to paginate. No data migration needed |
| Wrong category classification | LOW | Fix classification dict/function, redeploy. Categories aren't stored permanently -- they're computed on the fly |
| Dual lists broke existing watchlist | MEDIUM | If additive (new table), rollback is just dropping the table. If destructive (altered existing table), need DB restore from backup |
| Chrome extension rejected from Chrome Web Store | LOW | Sideload as unpacked extension (only 2 users). No store needed for personal use |
| Dashboard.html too big to maintain | MEDIUM | Stop, split into modules. 2-4 hours of refactoring. Every hour delayed makes it harder |
| Price history table bloated (millions of rows) | MEDIUM | `DELETE FROM price_history WHERE ts < datetime('now', '-90 days')` then `VACUUM`. Add retention cron |
| No TLS breaks PWA + extension | HIGH | Set up nginx reverse proxy + certbot on VPS. Requires domain name (or self-signed cert, which has its own issues). Consider a free subdomain from duckdns.org |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 24k items rendering freeze | Phase 1 (Catalog API) | API returns max 50 items per page; curl test confirms pagination |
| Category classification edge cases | Phase 1 (Catalog API) | Run classifier on full 24k dataset, assert <5% in "Other" category |
| dashboard.html monolith unmaintainable | Phase 0 (Prep) | File split into modules, each <300 lines. `index.html` just imports |
| Dual lists breaking existing alerts | Phase 2 (Dual lists) | Existing Telegram bot alert test passes unchanged after migration |
| Service worker caching stale content | Phase 4 (PWA) | Deploy new version, verify Lesha's phone shows updated content within 1 reload |
| Chrome extension CORS / mixed content | Phase 5 (Extension) | Extension successfully calls `http://VPS:8100/api/` from lis-skins.com (HTTPS page) |
| Case tracking overwhelm (3000 items) | Phase 3 (Cases) | Default view shows only active drop cases (~15 items), with expandable groups |
| iOS PWA limitations | Phase 4 (PWA) | Test on actual iPhone Safari: home screen icon works, app opens standalone, push NOT expected |
| No TLS on dashboard | Phase 4 (PWA) | Decision logged: either add nginx+certbot, or accept HTTP-only with documented limitations |

## Sources

- [Virtual scrolling in vanilla JS](https://sergimansilla.com/blog/virtual-scrolling/) -- rendering performance for large lists
- [HyperList -- virtual scroll library](https://github.com/tbranyen/hyperlist) -- 12KB, no dependencies
- [Rich Harris: Things I wish I'd known about service workers](https://gist.github.com/Rich-Harris/fd6c3c73e6e707e312d7c5d7d0f3b2f9) -- caching pitfalls
- [PWA iOS limitations 2026](https://www.mobiloud.com/blog/progressive-web-apps-ios) -- 50MB cache limit, no background sync, EU restrictions
- [PWA iOS Safari support](https://www.magicbell.com/blog/pwa-ios-limitations-safari-support-complete-guide) -- apple-touch-icon requirements
- [Chrome Extension Manifest V3 CORS](https://groups.google.com/a/chromium.org/g/chromium-extensions/c/IY_g501CekI) -- content script CORS changes
- [Chrome Extension host_permissions](https://www.codestudy.net/blog/access-to-fetch-has-been-blocked-by-cors-policy-chrome-extension-error/) -- proper URL patterns with trailing /*
- [Chromium: content script fetch changes](https://www.chromium.org/Home/chromium-security/extension-content-script-fetches/) -- must route through background SW
- [SQLite WAL concurrent writes](https://oldmoe.blog/2024/07/08/the-write-stuff-concurrent-write-transactions-in-sqlite/) -- single writer pattern
- [SQLite busy_timeout and locked errors](https://tenthousandmeters.com/blog/sqlite-concurrent-writes-and-database-is-locked-errors/) -- connection contention
- [CS2 skin types guide](https://www.cs2deck.com/cs2-skins-types-normal-stattrak-souvenir-guide) -- StatTrak/Souvenir naming
- [ByMykel CSGO-API](https://bymykel.github.io/CSGO-API/) -- reference dataset for item classification
- [CS2 all items list](https://skinsbook.com/all-cs2-items) -- category breakdown
- [Modular frontend from monolith](https://medium.com/thron-tech/single-page-application-from-monolithic-to-modular-c1d413c10292) -- gradual migration strategy

---
*Pitfalls research for: Steam Sniper v2.0 -- catalog, dual lists, PWA, Chrome extension*
*Researched: 2026-04-13*
