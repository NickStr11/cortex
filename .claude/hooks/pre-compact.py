#!/usr/bin/env python3
"""PreCompact hook: auto-save diary entry before context compression.

Reads the conversation transcript from stdin (hook input),
extracts key actions, and writes a diary entry to memory/diary/.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

MEMORY_DIR = Path(os.environ.get(
    "CLAUDE_PROJECT_DIR",
    r"D:\code\2026\2\cortex"
)).parent.parent / ".claude" / "projects" / "D--code-2026-2-cortex" / "memory" / "diary"

# Fallback: try project-local memory
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", r"D:\code\2026\2\cortex"))
DIARY_DIR = Path(r"C:\Users\User\.claude\projects\D--code-2026-2-cortex\memory\diary")


def get_next_number() -> int:
    """Find next diary entry number."""
    DIARY_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(DIARY_DIR.glob("*_*.md"))
    if not existing:
        return 1
    numbers = []
    for f in existing:
        try:
            numbers.append(int(f.name.split("_")[0]))
        except (ValueError, IndexError):
            pass
    return max(numbers, default=0) + 1


def extract_summary(transcript: str) -> str:
    """Extract a basic summary from hook input."""
    # Hook input is JSON with conversation_id and transcript
    lines = []
    try:
        data = json.loads(transcript)
        raw = data.get("transcript", transcript)
    except (json.JSONDecodeError, TypeError):
        raw = transcript

    # Grab tool usage patterns as indicators of what was done
    tool_actions = []
    if "Edit(" in str(raw) or "Write(" in str(raw):
        tool_actions.append("файлы редактировались")
    if "Bash(" in str(raw):
        tool_actions.append("команды выполнялись")
    if "WebFetch" in str(raw) or "WebSearch" in str(raw):
        tool_actions.append("веб-ресёрч")
    if "Agent(" in str(raw):
        tool_actions.append("субагенты использовались")

    return ", ".join(tool_actions) if tool_actions else "сессия без явных действий"


def write_diary(num: int, summary: str) -> Path:
    """Write a minimal diary entry."""
    now = datetime.now(timezone(timedelta(hours=3)))  # MSK
    date_str = now.strftime("%Y-%m-%d")
    filename = f"{num:03d}_{date_str}.md"
    filepath = DIARY_DIR / filename

    content = f"""# Сессия {num:03d} — {date_str} — Auto-saved (PreCompact)

## Что сделано
- Контекст сжат автоматически
- Активности: {summary}

## Остановились на
- Сессия прервана сжатием контекста — проверь CURRENT_CONTEXT.md
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


def main() -> None:
    # Read stdin if available (hook transcript)
    transcript = ""
    if not sys.stdin.isatty():
        try:
            transcript = sys.stdin.read()
        except Exception:
            pass

    summary = extract_summary(transcript)
    num = get_next_number()
    path = write_diary(num, summary)

    # Print message for Claude to see
    print(f"[PreCompact] Diary #{num:03d} auto-saved to {path.name}")
    print("Контекст сжимается. Diary записан автоматически.")
    sys.exit(0)


if __name__ == "__main__":
    main()
