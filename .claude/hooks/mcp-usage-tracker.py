"""PreToolUse hook: логирует все вызовы инструментов для аудита."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

data = json.load(sys.stdin)
tool = data.get("tool_name", "unknown")
tool_input = data.get("tool_input", {})

log_dir = Path.home() / ".claude" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "tool-usage.jsonl"

entry = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "tool": tool,
    "input_keys": list(tool_input.keys()) if isinstance(tool_input, dict) else [],
}

if tool.startswith("mcp__"):
    entry["mcp"] = True

with open(log_file, "a", encoding="utf-8") as f:
    f.write(json.dumps(entry) + "\n")
