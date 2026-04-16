---
phase: 04-vps-deployment
plan: 01
subsystem: infra
tags: [paramiko, systemd, vps, deployment, ssh]

requires:
  - phase: 03-dashboard-ui
    provides: Complete dashboard (server.py + dashboard.html) and bot (main.py) ready for production
provides:
  - deploy.py paramiko-based deploy script for one-command VPS deployment
  - systemd unit templates for dashboard (port 8100) and telegram bot
  - Auto-restart and reboot survival configuration
affects: []

tech-stack:
  added: [paramiko]
  patterns: [paramiko SSH deploy, systemd service units, uv-based remote dependency install]

key-files:
  created: [deploy.py, deploy/steam-sniper-dashboard.service, deploy/steam-sniper-bot.service]
  modified: [pyproject.toml]

key-decisions:
  - "paramiko added to main dependencies (not optional) for simple `uv run python deploy.py` invocation"
  - "SSH key auto-discovery with interactive passphrase fallback for flexibility"
  - "EnvironmentFile in systemd units (not dotenv in Python) for production env vars"

patterns-established:
  - "VPS deploy pattern: paramiko SSH + SFTP upload + systemd enable"
  - "Service naming: steam-sniper-{component}.service"

requirements-completed: [DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04]

duration: 3min
completed: 2026-04-12
---

# Phase 4 Plan 1: VPS Deployment Summary

**Paramiko deploy script + systemd units for dashboard (port 8100) and bot on VPS 194.87.140.204**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-12T19:07:44Z
- **Completed:** 2026-04-12T19:10:24Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Two systemd unit files with auto-restart, reboot survival, shared WorkingDirectory
- Complete paramiko deploy script with 9-step deployment flow
- SSH key auto-discovery (ed25519/rsa) with interactive credential fallback

## Task Commits

Each task was committed atomically:

1. **Task 1: Create systemd unit templates** - `7485003` (feat)
2. **Task 2: Create paramiko deploy script** - `34519a2` (feat)

## Files Created/Modified
- `deploy/steam-sniper-dashboard.service` - systemd unit for FastAPI dashboard on port 8100
- `deploy/steam-sniper-bot.service` - systemd unit for Telegram bot polling
- `deploy.py` - Paramiko-based deploy script (215 lines, 9-step flow)
- `pyproject.toml` - Added paramiko>=3.4 dependency

## Decisions Made
- paramiko in main deps (not optional group) so `uv run python deploy.py` works without flags
- SSH key auto-discovery tries ed25519 then rsa, falls back to interactive input
- EnvironmentFile directive in systemd units instead of relying on python-dotenv for production

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All v1 requirements complete (30/30)
- Run `uv run python deploy.py` from tools/steam-sniper/ to deploy to VPS
- Dashboard will be at http://194.87.140.204:8100 after deploy

---
*Phase: 04-vps-deployment*
*Completed: 2026-04-12*
