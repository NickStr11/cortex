# Feature Research

**Domain:** CS2 skin price tracking dashboard -- v2.0 lis-skins mirror (catalog, lists, cases, PWA, extension)
**Researched:** 2026-04-13
**Confidence:** HIGH

## Context: What Already Exists (v1.0)

Built and deployed on VPS (194.87.140.204:8100):
- Watchlist table with buy/sell split, live prices, deltas, targets
- Search across 24K lis-skins items (English + Russian via Steam Market API)
- Add/delete items with type, target price, quantity
- TradingView price history charts (24h/7d/30d/all)
- Hero stats (portfolio value, delta)
- Activity feed (alerts)
- Dark gaming theme, auto-refresh every 5 min
- Telegram bot alerts (shared SQLite)
- Rarity color coding from Steam categories

This research focuses ONLY on the v2.0 features: catalog browsing, category navigation, dual lists, case tracking, PWA, Chrome extension.

---

## Feature Landscape

### Table Stakes (Users Expect These)

These are the features that make v2 feel like a real "mirror" of lis-skins rather than a watchlist with search. Without them, the "catalog" claim is hollow.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Full catalog browsing (paginated)** | Core promise of v2 -- "весь каталог lis-skins как свой." Lis-skins itself, CSGOStash, CSGOSKINS.GG all present full item catalogs with browsing. Without this, it's still just a watchlist. | MEDIUM | 24K items in memory (`_prices` dict). Need paginated API endpoint (e.g., 50/page), client-side virtual scroll or pagination controls. No new data source needed. |
| **Category navigation (weapon types)** | Every skin marketplace has category filters. Lis-skins has weapon type, wear, price filters. CSGOSKINS.GG organizes by Pistols/Rifles/SMGs/Heavy/Knives/Gloves. Without categories, browsing 24K items is useless. | MEDIUM | Parse category from item name. Lis-skins JSON has only `name`, `price`, `url`, `count` -- no category field. Must extract from name patterns (see parsing section below). |
| **Wear condition filter** | All CS2 marketplaces filter by Factory New/Minimal Wear/Field-Tested/Well-Worn/Battle-Scarred. Users think in wear tiers. | LOW | Already parseable from item name suffix `(Factory New)` etc. Regex extraction at collection time. |
| **Price range filter** | Lis-skins, CSGOSKINS.GG, PriceEmpire all have min/max price filters. Essential for browsing a 24K catalog. | LOW | Client-side filter or API query param. Data already in `_prices`. |
| **Sort by price/name** | Every catalog has sort controls. At minimum: price low-to-high, price high-to-low, name A-Z. | LOW | Trivial on API or client side. |
| **Favorites list (items I own / love)** | Steam Inventory Helper has favorites. Every e-commerce site has wishlists. Lyosha specifically asked for "избранное" -- items he already owns or likes. | LOW | New SQLite table `favorites` with user_id, item_name, added_at. Simple heart toggle on cards. |
| **Wishlist (items I want to buy)** | Distinct from favorites. Standard e-commerce pattern. Lyosha wants separate "хотелки" -- items he wants to buy but hasn't yet. | LOW | New SQLite table `wishlist` or extend existing watchlist with a `list_type` column. Distinct icon (bookmark/star vs heart). |
| **Quick-add buttons on catalog cards** | If you browse a catalog but can't add items to lists without leaving the card, the UX is broken. Lis-skins has "Add to cart" on every card. Our analog: add-to-favorites and add-to-wishlist buttons. | LOW | Two icon buttons per card. POST to API, toggle state. |

### Differentiators (Competitive Advantage)

Features that make this mirror better than just visiting lis-skins.com directly.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Case/container tracking tab** | No major tracker isolates cases as a separate view. Cases are a specific investment category (~30-50 active cases in lis-skins). Lyosha tracks case prices separately. Dedicated tab with case-specific data (contents preview, price trends). | MEDIUM | Filter `_prices` for items matching case patterns (names ending in "Case"). ~3000 items per PROJECT.md claim, though likely fewer unique cases (~50 unique types x wear variations). Separate tab/view. |
| **Dual list status indicators in catalog** | When browsing catalog, instantly see which items are in favorites vs wishlist. No competitor shows personal list membership inline in catalog browse. Like Spotify showing which songs are in your library. | LOW | Query favorites + wishlist tables, overlay icons on catalog cards. Two-state visual: heart filled = in favorites, star filled = in wishlist. |
| **PWA install (iPhone home screen)** | No CS2 tracker offers PWA. Skinmanity is a native app. Having a home screen icon that opens in standalone mode without Safari chrome is a significant UX win for mobile checking. | LOW | manifest.json + meta tags + icons. No service worker needed for v2 (no offline). Just installability. |
| **Chrome extension for lis-skins.com** | SIH and CS2 Trader inject into Steam. Nobody injects into lis-skins specifically. One-click "add to my dashboard" while browsing lis-skins.com = zero friction for discovery. | HIGH | Chrome Extension MV3. Content script injecting buttons on lis-skins item pages. Background script calling dashboard API. Needs lis-skins page structure analysis (DOM selectors). |
| **Cross-reference owned vs available** | Browse catalog and see "you own 3 of these" or "this is on your wishlist at target 4000 RUB, current price 3800 -- BUY NOW." No competitor connects personal lists to catalog browse with actionable signals. | MEDIUM | Join catalog data with favorites/wishlist. Highlight cards where current price <= target. |
| **Category-level price trends** | See "Knives avg price up 5% this week" or "Cases are dropping." CSGOStocks has indexes, EsportFire has category indexes, but nobody does this for a single marketplace. | MEDIUM | Aggregate price history by parsed category. Requires enough history data. Defer to later if insufficient data. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Full offline PWA with service worker caching** | "Works without internet" sounds great | 50MB iOS cache limit, stale data = wrong prices, service worker complexity for a price tracker that's useless offline. CS2 prices change every 5 min. | PWA manifest for installability only. No offline cache. Show "no connection" state gracefully. |
| **Case opening simulator/tracker** | SteamLedger has it, people ask for it | Entertainment feature, not trader tool. Requires case contents database, drop rate simulation. Scope creep. | Link to csgocasetracker.com or case.oki.gg for that. |
| **Steam inventory auto-import** | SIH, PriceEmpire do this | Requires Steam OAuth, API key management, rate limiting, security concerns. 2 users can add items manually. | Manual add via search, Telegram bot `/buy` command, or Chrome extension. |
| **Multi-marketplace price comparison** | SIH compares 28+ marketplaces | Different APIs, data formats, rate limits. Out of scope per PROJECT.md. Would require maintaining price feeds from multiple sources. | Single marketplace (lis-skins), add Steam price comparison later when Lyosha provides account. |
| **Push notifications from PWA** | iOS 16.4+ supports them | Unreliable on iOS (service worker push events don't trigger consistently per Apple docs). Already have Telegram bot for alerts which works perfectly. | Keep Telegram as notification channel. PWA is view-only. |
| **Complex Chrome extension with popup UI** | Full-featured extensions like CS2 Trader have settings, dashboards | Maintenance burden, Chrome Web Store review process, security concerns. Just need "add to dashboard" buttons. | Minimal content script only. Inject 1-2 buttons on lis-skins item pages. No popup, no options page. |
| **User authentication** | "Each user sees their own lists" | 2 users on private VPS. Auth adds session management, password reset, security surface. Zero benefit. | Simple user_id parameter (?user=nikita or ?user=lesha). No login. |

## Item Name Parsing for Categories

The lis-skins JSON provides only `name`, `price`, `url`, `count`. Categories must be parsed from names. Confidence: HIGH (name patterns are standardized by Valve).

### CS2 Item Name Patterns

```
Weapon skins:    "AK-47 | Redline (Field-Tested)"
                 "StatTrak™ M4A4 | Howl (Factory New)"
Knives:          "★ Karambit | Fade (Factory New)"
                 "★ StatTrak™ Butterfly Knife | Doppler (Factory New)"
Gloves:          "★ Sport Gloves | Vice (Minimal Wear)"
                 "★ Driver Gloves | King Snake (Field-Tested)"
Cases:           "Kilowatt Case"
                 "Revolution Case"
Stickers:        "Sticker | NaVi (Holo) | Copenhagen 2024"
Agents:          "Vypa | Agent"
Patches:         "Patch | Metal..."
Graffiti:        "Sealed Graffiti | ..."
Keys:            "Kilowatt Case Key"
Music kits:      "Music Kit | ..."
Pins/Collectibles: "Genuine Pin | ..."
```

### Parsing Strategy

```python
WEAPON_TYPES = {
    # Pistols
    "Glock-18", "USP-S", "P2000", "P250", "Five-SeveN",
    "Tec-9", "CZ75-Auto", "Desert Eagle", "R8 Revolver", "Dual Berettas",
    # Rifles
    "AK-47", "M4A4", "M4A1-S", "FAMAS", "Galil AR",
    "AUG", "SG 553", "SSG 08", "AWP", "SCAR-20", "G3SG1",
    # SMGs
    "MAC-10", "MP9", "MP7", "MP5-SD", "UMP-45", "P90", "PP-Bizon",
    # Heavy
    "Nova", "XM1014", "MAG-7", "Sawed-Off", "M249", "Negev",
    # Knives (after ★ prefix)
    "Bayonet", "Bowie Knife", "Butterfly Knife", "Classic Knife",
    "Falchion Knife", "Flip Knife", "Gut Knife", "Huntsman Knife",
    "Karambit", "Kukri Knife", "M9 Bayonet", "Navaja Knife",
    "Nomad Knife", "Paracord Knife", "Shadow Daggers",
    "Skeleton Knife", "Stiletto Knife", "Survival Knife",
    "Talon Knife", "Ursus Knife",
    # Gloves
    "Bloodhound Gloves", "Broken Fang Gloves", "Driver Gloves",
    "Hand Wraps", "Hydra Gloves", "Moto Gloves",
    "Specialist Gloves", "Sport Gloves",
}

# Category extraction logic:
# 1. Starts with "★" → knife or glove (check WEAPON_TYPES for which)
# 2. Contains " | " → split on first "|", left side = weapon
# 3. Ends with "Case" → case/container
# 4. Starts with "Sticker" → sticker
# 5. Starts with "Music Kit" → music kit
# 6. etc.
```

### Category Hierarchy for Navigation

```
All Items (24K)
├── Rifles (~8K)
│   ├── AK-47, M4A4, M4A1-S, AWP, ...
├── Pistols (~4K)
│   ├── Glock-18, USP-S, Desert Eagle, ...
├── SMGs (~3K)
│   ├── MAC-10, MP9, P90, ...
├── Heavy (~2K)
│   ├── Nova, XM1014, MAG-7, ...
├── Knives (~2K) ★
│   ├── Karambit, Butterfly Knife, M9 Bayonet, ...
├── Gloves (~800) ★
│   ├── Sport Gloves, Driver Gloves, ...
├── Cases (~50 unique types)
├── Stickers (~3K)
├── Agents (~100)
├── Other (patches, graffiti, music kits, keys, pins)
```

## Feature Dependencies

```
Category Parser (name → category mapping)
    └──required by──> Category Navigation
    └──required by──> Case Tracking Tab
    └──required by──> Category-level Trends

Catalog Browsing (paginated API)
    └──required by──> Category Navigation (filter param)
    └──required by──> Quick-add Buttons
    └──required by──> Dual List Status Indicators

Favorites Table (SQLite)
    └──required by──> Favorites List View
    └──required by──> Quick-add Buttons (heart toggle)
    └──required by──> Dual List Status in Catalog

Wishlist Table (SQLite)
    └──required by──> Wishlist List View
    └──required by──> Quick-add Buttons (star toggle)
    └──required by──> Dual List Status in Catalog
    └──required by──> Cross-reference Owned vs Available

PWA Manifest
    └──independent──> No dependencies on other features

Chrome Extension
    └──requires──> Dashboard API (already exists)
    └──requires──> Lis-skins page structure knowledge
    └──independent of──> Catalog browsing (works with existing /api/watchlist POST)
```

### Dependency Notes

- **Category Parser is foundational:** Both category navigation and case tracking require knowing what category each item belongs to. Build this first as a server-side enrichment step during collection.
- **Favorites/Wishlist tables are parallel:** Both are simple SQLite tables with similar schema. Can be built together. The existing `watchlist` table (buy/sell) remains separate -- it has target prices and alerts. Favorites/wishlist are simpler (just a list of items).
- **Chrome extension is decoupled:** It only needs the existing POST /api/watchlist endpoint. Can be built independently at any point.
- **PWA manifest is trivial and independent:** Just static files. No dependencies.

## MVP Definition

### Launch With (v2.0 core)

- [ ] **Category parser** -- enrich `_prices` dict with parsed category at collection time
- [ ] **Catalog browsing** -- new `/api/catalog` endpoint with pagination, category filter, price filter, sort
- [ ] **Category sidebar/tabs** -- UI navigation: All / Rifles / Pistols / SMGs / Heavy / Knives / Gloves / Cases / Stickers / Other
- [ ] **Favorites list** -- new SQLite table, heart button on cards, dedicated view
- [ ] **Wishlist** -- new SQLite table, star/bookmark button on cards, dedicated view
- [ ] **Quick-add buttons** -- two icons per catalog card (heart + star)
- [ ] **PWA manifest** -- manifest.json, apple-touch-icon, meta tags for standalone mode

### Add After Validation (v2.x)

- [ ] **Case tracking tab** -- dedicated view filtering cases only, with price trends and contents info
- [ ] **Chrome extension** -- content script for lis-skins.com, "Add to Dashboard" button injection
- [ ] **Dual list status indicators in catalog** -- show filled heart/star for items already in lists
- [ ] **Cross-reference signals** -- highlight catalog items where price <= wishlist target

### Future Consideration (v3+)

- [ ] **Category-level price trends** -- requires substantial price history (weeks of data)
- [ ] **Steam price comparison** -- blocked by needing Lyosha's Steam account
- [ ] **Case contents preview** -- requires external data source (ByMykel/CSGO-API or manual mapping)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Category parser | HIGH | LOW | P1 |
| Catalog browsing (paginated) | HIGH | MEDIUM | P1 |
| Category navigation | HIGH | MEDIUM | P1 |
| Favorites list | HIGH | LOW | P1 |
| Wishlist | HIGH | LOW | P1 |
| Quick-add buttons | HIGH | LOW | P1 |
| Wear condition filter | MEDIUM | LOW | P1 |
| Price range filter | MEDIUM | LOW | P1 |
| Sort controls | MEDIUM | LOW | P1 |
| PWA manifest | MEDIUM | LOW | P1 |
| Case tracking tab | MEDIUM | MEDIUM | P2 |
| Dual list status in catalog | MEDIUM | LOW | P2 |
| Chrome extension | MEDIUM | HIGH | P2 |
| Cross-reference signals | LOW | MEDIUM | P3 |
| Category-level trends | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for v2.0 launch
- P2: Should have, add in v2.x
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Lis-skins.com | CSGOStash/CSGOSKINS.GG | SIH Extension | Our Approach |
|---------|---------------|------------------------|---------------|-------------|
| Category navigation | Weapon type, wear, price sidebar filters | Full taxonomy: weapons, knives, gloves, cases, stickers, agents | N/A (extension, not catalog) | Parsed from item names. Top-level tabs + wear/price filters |
| Favorites/wishlist | No | No (browsing only) | Favorites in extension popup | Two separate lists: favorites (own/love) + wishlist (want to buy). SQLite backed |
| Case tracking | Mixed in with all items | Dedicated "Containers" section with case contents | N/A | Dedicated tab, parsed from "* Case" name pattern |
| Mobile access | Responsive website | Responsive website | N/A | PWA manifest for home screen icon, standalone mode |
| Browser extension | N/A (is the website) | N/A | Injects into Steam pages | Content script on lis-skins pages, "Add to Dashboard" button |
| Price history | None (marketplace, not tracker) | Price trends charts | No | Already built (TradingView charts from SQLite snapshots) |
| Personal lists on catalog | Cart only | None | Favorites list | Heart/star overlay on every catalog card |

## PWA Technical Requirements

Minimal PWA for installability (no offline, no push):

```json
{
  "name": "Steam Sniper",
  "short_name": "Sniper",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#060a12",
  "theme_color": "#ff906a",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

Plus HTML meta tags:
```html
<link rel="manifest" href="/manifest.json">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="apple-touch-icon" href="/icon-192.png">
```

**iOS limitations (2026):** No push notifications (use Telegram). 50MB cache limit (irrelevant -- no offline caching). EU may lose standalone mode (iOS 17.4+ DMA). Manual install only (Share > Add to Home Screen).

## Chrome Extension Technical Requirements

MV3 Chrome Extension. Minimal scope:

```
manifest.json (MV3)
content.js (injected into lis-skins.com/market/*)
styles.css (button styling)
```

Content script responsibilities:
1. Detect item cards on lis-skins market pages
2. Extract item name from card DOM
3. Inject "Add to Sniper" button on each card
4. On click: POST to `http://194.87.140.204:8100/api/watchlist` with item data
5. Show success/error toast

**Key risks:**
- Lis-skins DOM structure is not documented and may change without notice
- Extension communicates with VPS directly (not localhost) -- CORS already set to `*`
- No Chrome Web Store publishing needed (2 users, load unpacked)
- MV3 requires service worker instead of background page

## Sources

- [CS2 Trader Extension (open source)](https://github.com/gergelyszabo94/csgo-trader-extension) -- reference for Chrome extension structure, content script injection patterns
- [SIH (Steam Inventory Helper)](https://sih.app/) -- price comparison across 28+ marketplaces including lis-skins, favorites feature
- [CSFloat Market Checker](https://chromewebstore.google.com/detail/csfloat-market-checker/jjicbefpemnphinccgikpdaagjebbnhg) -- float value injection on Steam Market pages
- [SkinScanner](https://chrome-stats.com/d/igfbjdbkogljnmakhfckgffbkheekicp) -- multi-market price comparison extension
- [CSGOStash / Stash.clash.gg](https://stash.clash.gg/) -- category taxonomy reference (weapons, knives, gloves, cases, agents)
- [CSGO Database](https://www.csgodatabase.com/weapons/) -- 54 weapons, 20 knife types, 8 glove types
- [ByMykel/CSGO-API](https://github.com/ByMykel/CSGO-API) -- unofficial JSON API with case contents, item metadata
- [PWA on iOS 2026](https://brainhub.eu/library/pwa-on-ios) -- iOS PWA limitations and capabilities
- [MDN PWA Installation](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable) -- manifest.json specification
- [Chrome MV3 Content Scripts](https://developer.chrome.com/docs/extensions/mv3/content_scripts) -- content script injection API
- [CS2 Case Tracker](https://csgocasetracker.com/) -- case-specific tracking reference
- [Lis-skins market](https://lis-skins.com/market/cs2/) -- weapon type, wear, price filters on source marketplace

---
*Feature research for: Steam Sniper v2.0 -- lis-skins mirror*
*Researched: 2026-04-13*
