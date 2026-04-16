---
phase: 05-dashboard-split
plan: 01
subsystem: ui
tags: [es-modules, javascript, css, fastapi, static-files]

requires:
  - phase: 01-04 (v1.0)
    provides: monolithic dashboard.html with all CSS/JS inline

provides:
  - ES module architecture with 10 JS files + 1 CSS file
  - Event bus for cross-module communication (watchlist:changed, chart:hide)
  - StaticFiles mount on FastAPI for /static/
  - Shared state object replacing global variables

affects: [05-02-verify, 06-catalog, 07-lists, 08-cases]

tech-stack:
  added: [ES modules, FastAPI StaticFiles]
  patterns: [event-bus cross-module communication, shared state object, thin HTML shell]

key-files:
  created:
    - static/css/styles.css
    - static/js/state.js
    - static/js/events.js
    - static/js/utils.js
    - static/js/watchlist.js
    - static/js/search.js
    - static/js/chart.js
    - static/js/stats.js
    - static/js/modal.js
    - static/js/alerts.js
    - static/js/main.js
  modified:
    - server.py
    - dashboard.html

key-decisions:
  - "Event bus pattern for cross-module communication instead of direct function calls"
  - "Static top-level imports for fmtRub in search.js instead of dynamic import"
  - "Fixed chart.js selector bug: .wl-card instead of tr (original had wrong selector for card-based UI)"

patterns-established:
  - "ES module pattern: each domain concern in separate file with explicit imports/exports"
  - "Shared state via state.js: single mutable object imported by all modules that need it"
  - "Event bus via events.js: emit/on pattern for loose coupling between modules"

requirements-completed: [REF-01]

duration: 6min
completed: 2026-04-13
---

# Phase 05 Plan 01: Dashboard Split Summary

**Split 1373-line dashboard.html monolith into 10 ES modules + CSS file with event bus cross-module communication**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-13T10:00:15Z
- **Completed:** 2026-04-13T10:06:06Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- Extracted all CSS (757 lines) into static/css/styles.css
- Created shared infrastructure: state.js (mutable state), events.js (event bus), utils.js (formatters)
- Extracted 6 domain modules: watchlist, search, chart, stats, modal, alerts
- Created main.js entry point with cross-module event wiring
- Reduced dashboard.html from 1373 lines to 141 lines (thin HTML shell)
- Fixed existing bug in chart.js: selector used `tr[data-item-name]` but UI uses `div.wl-card`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create static infrastructure + shared modules + CSS extraction** - `0c7788c` (feat)
2. **Task 2: Extract domain JS modules + create main.js + update dashboard.html shell** - `155bd6b` (feat)

## Files Created/Modified
- `static/css/styles.css` - All CSS extracted from inline style tag (757 lines)
- `static/js/state.js` - Shared mutable state object (usdRub, pendingItem, chart, etc.)
- `static/js/events.js` - Lightweight event bus (on/off/emit)
- `static/js/utils.js` - Formatter functions (fmtRub, fmtUsd, fmtDelta, timeAgo)
- `static/js/watchlist.js` - Watchlist loading, rendering, delete handling
- `static/js/search.js` - Search input handling, result rendering, result click
- `static/js/chart.js` - TradingView chart creation, timeframe switching, stats
- `static/js/stats.js` - Hero stats block loading
- `static/js/modal.js` - Add-to-watchlist modal open/close/submit
- `static/js/alerts.js` - Activity feed loading
- `static/js/main.js` - Entry point, module init, event wiring, auto-refresh
- `server.py` - Added StaticFiles import and mount for /static/
- `dashboard.html` - Thin HTML shell, no inline JS or CSS

## Decisions Made
- Used event bus pattern (events.js) for cross-module communication instead of direct function calls -- enables adding new modules without modifying existing ones
- Fixed chart.js selector from `tr[data-item-name]` to `.wl-card[data-item-name]` -- original code had a bug (UI uses card divs, not table rows)
- Used static import for fmtRub in search.js instead of dynamic import -- simpler, no performance difference for modules

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed chart.js selector for highlighting selected item**
- **Found during:** Task 2 (chart.js extraction)
- **Issue:** Original code used `tr[data-item-name="..."]` selector but UI renders `div.wl-card` cards, not table rows
- **Fix:** Changed selector to `.wl-card[data-item-name="..."]` in showChart function
- **Files modified:** static/js/chart.js
- **Verification:** Selector matches actual DOM structure
- **Committed in:** 155bd6b (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Bug fix was identified in the plan itself. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Modular architecture ready for adding catalog, lists, and cases tabs (phases 6-10)
- Each new feature can be added as a new JS module with its own file
- Event bus enables loose coupling between existing and new modules
- Plan 05-02 should verify the split works correctly end-to-end

---
*Phase: 05-dashboard-split*
*Completed: 2026-04-13*
