#!/usr/bin/env bash
# Domain-specific verification для max-transcribe.
# Проверяет что Chrome CDP, whisper-cli и Playwright доступны.
set -u

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

echo "=== max-transcribe verification ==="

echo "[1] Dependencies"
check "uv project ok" \
    bash -c "cd tools/max-transcribe && uv sync --quiet"
check "playwright module importable" \
    bash -c "cd tools/max-transcribe && uv run python -c 'import playwright' 2>/dev/null"

echo
echo "[2] Chrome CDP availability"
# Chrome with CDP должен быть на :9222 если запущен
check "Chrome CDP :9222 listening" \
    bash -c "curl -fsS http://localhost:9222/json/version | grep -q 'webSocketDebuggerUrl'"

echo
echo "[3] whisper-cli (для транскрипции)"
WHISPER_PATHS=(
    "$HOME/whisper.cpp/main"
    "$HOME/whisper.cpp/build/bin/whisper-cli"
    "/c/whisper.cpp/main.exe"
)
WHISPER_FOUND=false
for p in "${WHISPER_PATHS[@]}"; do
    if [[ -x "$p" ]]; then
        echo "  ✅ whisper-cli found at $p"
        PASS=$((PASS+1))
        WHISPER_FOUND=true
        break
    fi
done
if ! $WHISPER_FOUND; then
    echo "  ❌ whisper-cli not found in standard paths"
    FAIL=$((FAIL+1))
fi

echo
echo "[4] WhisperX optional (--diarize)"
check "whisperx module importable (opt-in)" \
    bash -c "cd tools/max-transcribe && uv run python -c 'import whisperx' 2>/dev/null" || true
echo "  (whisperx опционален — для diarize. Без него нормально.)"

echo
echo "=== Result: $PASS passed, $FAIL failed ==="
exit $FAIL
