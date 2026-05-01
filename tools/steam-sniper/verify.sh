#!/usr/bin/env bash
# Domain-specific verification для Steam Sniper.
# Запускать после deploy или при подозрении что что-то сломалось.
# Generic тесты (pytest, ruff) ловят далеко не всё. Это про реальный продакшен.
#
# Usage:
#   bash tools/steam-sniper/verify.sh           # full check
#   bash tools/steam-sniper/verify.sh --quick   # только HTTP, без VM
set -u

VPS="72.56.37.150"
VPS_KEY="${HOME}/.ssh/id_ed25519_steamsniper"
[[ -f "$VPS_KEY" ]] || VPS_KEY="${HOME}/.ssh/vps_key"
VM="cortex-vm"
VM_ZONE="europe-west3-b"

QUICK=false
[[ "${1:-}" == "--quick" ]] && QUICK=true

PASS=0
FAIL=0

check() {
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then
        echo "  ✅ $name"
        PASS=$((PASS+1))
    else
        echo "  ❌ $name"
        FAIL=$((FAIL+1))
    fi
}

check_with_output() {
    local name="$1"; shift
    local out
    out=$("$@" 2>&1)
    local rc=$?
    if [[ $rc -eq 0 ]]; then
        echo "  ✅ $name — $out"
        PASS=$((PASS+1))
    else
        echo "  ❌ $name — $out"
        FAIL=$((FAIL+1))
    fi
}

echo "=== Steam Sniper verification ==="
echo

echo "[1] HTTP endpoints на проде (http://${VPS}/)"

# Health: dashboard.html отдаётся
check "dashboard renders" \
    bash -c "curl -fsS http://${VPS}/ | grep -q '<html'"

# /api/lists возвращает JSON, не HTML
check "GET /api/lists returns JSON" \
    bash -c "curl -fsS 'http://${VPS}/api/lists?user=lesha&type=favorite' | head -c 1 | grep -q '\['"

# /api/catalog возвращает items
check "GET /api/catalog returns items" \
    bash -c "curl -fsS 'http://${VPS}/api/catalog?limit=1' | grep -q 'items'"

# /api/debug — snapshot freshness
check "snapshot built_at < 24h ago" \
    bash -c "
        built=\$(curl -fsS http://${VPS}/api/debug | python -c 'import sys,json,datetime; d=json.load(sys.stdin); print(d.get(\"snapshot_built_at\",\"\"))' 2>/dev/null)
        [[ -n \"\$built\" ]] || exit 1
        ts=\$(date -d \"\$built\" +%s 2>/dev/null) || exit 1
        now=\$(date +%s)
        (( now - ts < 86400 ))
    "

# Cache-Control: no-cache, must-revalidate
check "Cache-Control on /static is no-cache" \
    bash -c "curl -fsSI 'http://${VPS}/static/dashboard.js' | grep -qi 'cache-control:.*no-cache'"

# CSS / JS реально обновлённые (cache-busting через ?v=)
echo "[1.5] Static assets с cache-busting"
check "dashboard.html ссылается на ?v= в JS" \
    bash -c "curl -fsS http://${VPS}/ | grep -q 'js?v='"

if $QUICK; then
    echo
    echo "[skipped VM checks because --quick]"
else
    echo
    echo "[2] Snapshot pipeline на cortex-vm"
    if command -v gcloud >/dev/null 2>&1; then
        check "VM SSH alive" \
            gcloud compute ssh "$VM" --zone="$VM_ZONE" --command="echo ok" --quiet
        check "cron entry exists" \
            gcloud compute ssh "$VM" --zone="$VM_ZONE" --command="crontab -l | grep -q sync_steam_sniper" --quiet
        check "last cron run within 5h" \
            gcloud compute ssh "$VM" --zone="$VM_ZONE" --command="
                test -f ~/sync_steam_sniper_snapshot.log &&
                [[ \$(find ~/sync_steam_sniper_snapshot.log -mmin -300 -print) ]]
            " --quiet
    else
        echo "  ⚠️  gcloud CLI не найден — VM checks пропущены"
    fi

    echo
    echo "[3] systemd на VPS"
    if [[ -f "$VPS_KEY" ]]; then
        check "steam-sniper-dashboard active" \
            ssh -i "$VPS_KEY" -o StrictHostKeyChecking=no "root@${VPS}" \
                "systemctl is-active --quiet steam-sniper-dashboard"
        check "no exceptions in last 100 log lines" \
            ssh -i "$VPS_KEY" -o StrictHostKeyChecking=no "root@${VPS}" \
                "! journalctl -u steam-sniper-dashboard -n 100 --no-pager | grep -qE 'Traceback|ERROR'"
        check ".env has TELEGRAM_BOT_TOKEN" \
            ssh -i "$VPS_KEY" -o StrictHostKeyChecking=no "root@${VPS}" \
                "grep -q '^TELEGRAM_BOT_TOKEN=' /opt/steam-sniper/.env"
        check ".env has LESHA_TG_CHAT_ID" \
            ssh -i "$VPS_KEY" -o StrictHostKeyChecking=no "root@${VPS}" \
                "grep -q '^LESHA_TG_CHAT_ID=' /opt/steam-sniper/.env"
    else
        echo "  ⚠️  $VPS_KEY не найден — VPS systemd checks пропущены"
    fi
fi

echo
echo "[4] Generic checks (на всякий случай)"
check "pyproject.toml имеет pytest в основных deps" \
    bash -c "grep -A 30 '^dependencies' tools/steam-sniper/pyproject.toml | grep -q 'pytest'"

check "manifest.json extension version >= 1.2" \
    bash -c "
        ver=\$(python -c 'import json; print(json.load(open(\"tools/steam-sniper/extension/manifest.json\"))[\"version\"])' 2>/dev/null)
        python -c \"import sys; sys.exit(0 if tuple(map(int, '\$ver'.split('.'))) >= (1,2) else 1)\"
    "

echo
echo "=== Result: $PASS passed, $FAIL failed ==="
exit $FAIL
