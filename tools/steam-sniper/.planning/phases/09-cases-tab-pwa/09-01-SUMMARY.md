---
phase: 09-cases-tab-pwa
plan: 01
subsystem: ui
tags: [javascript, es-modules, cases, trend-badges, pagination]

# Dependency graph
requires:
  - phase: 08-dashboard-tabs-catalog-lists-ui
    provides: catalog.js pattern, lists.js integration, cat-card CSS, pagination
provides:
  - Cases tab module (cases.js) with filtered catalog view
  - Trend data in /api/catalog for case items
  - Cases tab HTML structure with controls
affects: [09-02 PWA, 10-chrome-extension]

# Tech tracking
tech-stack:
  added: []
  patterns: [filtered-catalog-view, trend-badge-rendering]

key-files:
  created: [static/js/cases.js]
  modified: [server.py, dashboard.html, static/js/main.js, static/css/styles.css]

key-decisions:
  - "Trend data only for case items in /api/catalog (not all 24k -- DB query per item too expensive)"
  - "Copied _buildPageRange locally in cases.js to keep modules independent (no shared util for 20 lines)"
  - "No sidebar for cases tab -- ~50 items don't need category filtering"

patterns-established:
  - "Filtered catalog view pattern: hardcode category param, reuse cat-card CSS, add domain-specific badges"
  - "Trend badge: .trend .trend-{direction} spans with arrow + percentage text"

requirements-completed: [CASE-01, CASE-02]

# Metrics
duration: 2min
completed: 2026-04-13
---

# Phase 9 Plan 01: Cases Tab Summary

**Dedicated cases tab with trend badges showing price direction/percentage, reusing catalog card grid and pagination patterns**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-13T10:48:13Z
- **Completed:** 2026-04-13T10:50:27Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Cases tab renders case items from /api/catalog?category=case with trend badges
- Each card shows image, name, price (RUB), availability count, and trend indicator (up/down/flat with %)
- Pagination, sort dropdown, and debounced search work within cases tab
- List toggle buttons (heart/star) work on case cards via existing lists.js event delegation

## Task Commits

Each task was committed atomically:

1. **Task 1: Add trend to catalog API + create cases.js module** - `1461d64` (feat)
2. **Task 2: Wire cases.js into dashboard HTML and main.js** - `bcf31d6` (feat)

## Files Created/Modified
- `static/js/cases.js` - Cases tab module: fetch, render grid with trends, pagination, sort, search
- `server.py` - Added trend field ({direction, pct}) for case items in /api/catalog response
- `dashboard.html` - Replaced cases tab stub with casesGrid, controls, pagination containers
- `static/js/main.js` - Import initCases, call in init(), wire cases:loaded event
- `static/css/styles.css` - cases-layout, cases-controls, cat-card-trend styles

## Decisions Made
- Trend data only computed for case items in catalog API (avoid expensive DB queries on 24k items)
- _buildPageRange copied locally in cases.js (keep modules independent, function is ~20 lines)
- No sidebar needed for cases tab (~50 items, single category)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Cases tab complete, ready for Phase 9 Plan 02 (PWA manifest + service worker + HTTPS)
- Note: server.py already has /sw.js route added (by concurrent process), ready for service worker

---
*Phase: 09-cases-tab-pwa*
*Completed: 2026-04-13*
