#!/bin/bash
# Setup script for cortex-vm (34.159.55.61)
# Run: bash tools/tg-monitor/deploy/setup-vm.sh

set -euo pipefail

CORTEX_DIR="/opt/cortex"
VENV_DIR="$CORTEX_DIR/.venv"

echo "=== Cortex TG Monitor — VM Setup ==="

# 1. Update repo
echo "[1/5] Updating cortex repo..."
cd "$CORTEX_DIR"
git pull origin main

# 2. Setup venv + deps
echo "[2/5] Setting up Python venv..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install telethon google-genai beartype httpx

# 3. Check .env
echo "[3/5] Checking .env..."
required_vars=("TG_API_ID" "TG_API_HASH" "GOOGLE_API_KEY" "TELEGRAM_BOT_TOKEN" "TELEGRAM_CHAT_ID")
if [ ! -f "$CORTEX_DIR/.env" ]; then
    echo "ERROR: $CORTEX_DIR/.env not found!"
    echo "Create it with:"
    for var in "${required_vars[@]}"; do
        echo "  $var=..."
    done
    exit 1
fi
for var in "${required_vars[@]}"; do
    if ! grep -q "^$var=" "$CORTEX_DIR/.env"; then
        echo "WARNING: $var not found in .env"
    fi
done
echo "  .env OK"

# 4. Telethon auth (interactive — needs phone + code)
echo "[4/5] Telethon auth check..."
echo "  If first run, you'll need to enter phone + code."
echo "  Run manually: cd $CORTEX_DIR && $VENV_DIR/bin/python tools/tg-monitor/monitor.py --limit 5"

# 5. Install systemd timer
echo "[5/5] Installing systemd timer..."
cp tools/tg-monitor/deploy/cortex-daily.service /etc/systemd/system/
cp tools/tg-monitor/deploy/cortex-daily.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable cortex-daily.timer
systemctl start cortex-daily.timer

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Add TG_API_ID and TG_API_HASH to .env"
echo "  2. Run monitor.py manually to auth Telethon:"
echo "     cd $CORTEX_DIR && source .env && $VENV_DIR/bin/python tools/tg-monitor/monitor.py --limit 5"
echo "  3. Check timer: systemctl list-timers | grep cortex"
echo "  4. Manual test: systemctl start cortex-daily"
echo "  5. Logs: journalctl -u cortex-daily -f"
