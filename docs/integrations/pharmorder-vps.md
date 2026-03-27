<!-- L0: PharmOrder production — 194.87.140.204:8000, API, DB, деплой, TZ Moscow -->
# PharmOrder VPS

## Server
- **IP**: 194.87.140.204
- **SSH**: root, password-based (password in session, NEVER store in files)
- **SSH from Windows**: use `paramiko` library (sshpass/expect not available)

## CRITICAL
**`apteka-bot` is a production systemd service. DO NOT restart, stop, or modify it without explicit request.**

## File Layout
```
/opt/pharmorder/
  src/
    server.py          # Main API server
    static/
      index.html       # Web UI
  scan_items.json      # Shared scan items (polling every 3s)
  order_history.db     # ReeTov.DBF -> SQLite (85K records)
  sozvezdie.db         # Product matrices
  sklit_cache.db       # SCLIT product cache
  README.md            # Full architecture docs
```

## API
- **Port**: 8000
- **Auth**: query param `?key=` (required, else 401)
- Key endpoints:
  - `GET /api/sync` — delta sync status
  - `GET /api/sozvezdie?ean=...` — Sozvezdie matrix lookup
  - `POST /api/sozvezdie-batch` — batch EAN lookup
  - `GET /api/inventory` — current inventory

## Sync
- `sync_standalone.py` handles DBF -> SQLite sync
- First run = snapshot only, subsequent = delta (upserts + deletes)
- `--upload` flag for full re-upload
- sync.bat URL must include `?key=`, otherwise 401

## scan-relay
- `relay_server.py` on port 8080
- Receives scans from cash register, delivers to PharmOrder UI

## DBF Files
- **Encoding: cp1251** (NOT cp866 — cp866 produces garbage)
- `dbf` library auto-detects encoding; `dbfread` needs explicit `encoding='cp1251'`
- ReeTov.DBF: purchase history, retail prices (BL_ROSN_PR)
- pr_all.dbf: ~131K ZHVNLP registry records filtered by EXCLUDE_PREFIXES

## Sozvezdie
- Mandatory (O) and Recommended (R) matrices
- Pharmacy group: 5160, code: 00017402
- id_name fallback: if EAN not in matrix, resolves alternative EAN via sklit_cache.db

## Gotchas
- Mom's DBF copy has BL_ROSN_PR=0 — retail prices only on the work PC.
- `heredoc` breaks JSON private_key newlines — use SCP or base64 for file transfer.
- Windows CRLF: run `sed -i 's/\r$//' file` on VPS after transfer.
