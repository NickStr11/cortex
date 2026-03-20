#!/usr/bin/env bash
# Cortex — root operations (works in Git Bash on Windows)
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS_WITH_TESTS="tools/heartbeat tools/metrics"
TOOLS_ALL="tools/heartbeat tools/metrics tools/kwork-monitor tools/tg-monitor tools/tg-bridge tools/tg-pharma tools/pipeline tools/scaffold"

case "${1:-help}" in
  test)
    echo "Running tests..."
    for d in $TOOLS_WITH_TESTS; do
      echo "=== $d ==="
      (cd "$ROOT/$d" && uv sync --quiet 2>/dev/null && uv run pytest -q 2>&1) || true
    done
    ;;
  check)
    echo "Typecheck..."
    for d in $TOOLS_ALL; do
      echo "=== $d ==="
      (cd "$ROOT/$d" && uv run pyright . 2>&1 | tail -5) || true
    done
    ;;
  lint)
    echo "Lint..."
    for d in $TOOLS_ALL; do
      echo "=== $d ==="
      (cd "$ROOT/$d" && uv run ruff check . 2>&1 | tail -5) || true
    done
    ;;
  sync)
    echo "Sync deps..."
    for d in $TOOLS_ALL; do
      echo "=== $d ==="
      (cd "$ROOT/$d" && uv sync --quiet) || true
    done
    ;;
  secrets)
    echo "Checking for secrets in tracked files..."
    cd "$ROOT"
    git ls-files | xargs grep -lE '(sk-[a-zA-Z0-9]{20,}|AIzaSy[a-zA-Z0-9_-]{33}|ghp_[a-zA-Z0-9]{36})' 2>/dev/null \
      && echo "!! SECRETS FOUND !!" || echo "Clean."
    ;;
  clean)
    cd "$ROOT"
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
    find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null
    find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null
    echo "Cleaned."
    ;;
  help|*)
    echo "Usage: bash ops.sh <command>"
    echo ""
    echo "  test     Run tests (heartbeat, metrics)"
    echo "  check    Typecheck all tools (pyright)"
    echo "  lint     Lint all tools (ruff)"
    echo "  sync     Install/sync deps for all tools"
    echo "  secrets  Check for leaked secrets"
    echo "  clean    Remove __pycache__, .pytest_cache"
    ;;
esac
