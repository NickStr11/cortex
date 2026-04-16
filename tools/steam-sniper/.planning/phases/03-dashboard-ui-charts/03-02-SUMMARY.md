---
phase: 03-dashboard-ui-charts
plan: 02
subsystem: ui
tags: [tradingview, lightweight-charts, charting, price-history]

requires:
  - phase: 03-01
    provides: "dashboard.html with API wiring, data-item-name on rows, usdRub variable"
  - phase: 02-01
    provides: "/api/history/{name}?tf= endpoint returning price_usd + ts"
provides:
  - "TradingView Lightweight Charts v5 integration in dashboard"
  - "Interactive price history chart with 24h/7d/30d/all timeframes"
  - "Chart stats bar (min/max/avg/count)"
  - "Row click -> chart open, close button hides"
affects: [04-deploy-bot]

tech-stack:
  added: [lightweight-charts v5 (CDN)]
  patterns: [event delegation for dynamic rows, CSS.escape for attribute selectors]

key-files:
  created: []
  modified: [dashboard.html]

key-decisions:
  - "CSS.escape for safe attribute selector matching on item names with special chars"
  - "Chart count shows number of price history points (not watchlist qty)"
  - "Single chart instance reused across items (create once, setData on switch)"

patterns-established:
  - "Chart initialization: lazy-create on first showChart(), reuse thereafter"
  - "Event delegation in init() for row clicks (not re-added on each loadWatchlist)"

requirements-completed: [CHART-01, CHART-02, CHART-03]

duration: 2min
completed: 2026-04-12
---

# Phase 03 Plan 02: Chart Panel Summary

**TradingView Lightweight Charts v5 with 4 timeframes, dark theme, and min/max/avg stats bar**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-12T18:58:39Z
- **Completed:** 2026-04-12T19:00:41Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- TradingView Lightweight Charts v5 integrated via CDN
- Chart panel with 24h/7d/30d/all timeframe switching
- Stats bar showing min/max/avg prices and data point count
- Row click opens chart, close button hides panel
- Dark theme matching dashboard (bg #111b2e, accent line #ff906a)
- Prices converted USD -> RUB using usdRub rate from watchlist API

## Task Commits

Each task was committed atomically:

1. **Task 1: Add TradingView Lightweight Charts and chart panel** - `c015f9f` (feat)

## Files Created/Modified
- `dashboard.html` - Added CDN script, chart panel HTML, chart CSS, showChart/loadChart/hideChart JS functions, event handlers

## Decisions Made
- Used CSS.escape() for safe attribute selector matching (item names contain special characters like pipes and parentheses)
- Chart count stat shows number of history data points rather than watchlist qty (more meaningful for chart context)
- Single chart instance created lazily on first showChart() and reused for all items (avoids memory leaks from multiple chart instances)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 03 complete (both plans done)
- Dashboard has full watchlist management + price charts
- Ready for Phase 04: deployment and bot integration

---
*Phase: 03-dashboard-ui-charts*
*Completed: 2026-04-12*
