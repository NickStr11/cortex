"""PreToolUse hook: предупреждает о дорогих вызовах (browser automation и т.д.)."""
import json
import sys

data = json.load(sys.stdin)
tool = data.get("tool_name", "")

EXPENSIVE_TOOLS = [
    "mcp__playwright__browser_run_code",
    "mcp__playwright__browser_navigate",
    "mcp__playwright__browser_take_screenshot",
    "mcp__playwright__browser_snapshot",
    "mcp__playwright__browser_click",
    "mcp__playwright__browser_type",
    "mcp__playwright__browser_evaluate",
]

WARN_ONLY = [
    "mcp__playwright__browser_close",
    "mcp__playwright__browser_console_messages",
    "mcp__playwright__browser_network_requests",
    "mcp__playwright__browser_tabs",
]

if tool in EXPENSIVE_TOOLS:
    print(f"COST WARNING: {tool} — browser automation is expensive", file=sys.stderr)

if tool in WARN_ONLY:
    print(f"NOTE: browser tool {tool}", file=sys.stderr)
