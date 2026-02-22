"""PreToolUse hook: проверяет staged файлы перед git commit."""
import json
import os
import subprocess
import sys

data = json.load(sys.stdin)
command = data.get("tool_input", {}).get("command", "")

if "git commit" not in command:
    sys.exit(0)

result = subprocess.run(
    ["git", "diff", "--cached", "--name-only"],
    capture_output=True, text=True
)
files = [f for f in result.stdout.strip().split("\n") if f]

issues = []
for filepath in files:
    if not os.path.exists(filepath):
        continue
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".py", ".js", ".ts", ".tsx", ".jsx"):
        continue

    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("//"):
                    continue
                if ext == ".py" and "print(" in line:
                    issues.append(f"  {filepath}:{i} — print()")
                if ext in (".js", ".ts", ".tsx", ".jsx") and "console.log" in line:
                    issues.append(f"  {filepath}:{i} — console.log")
    except (OSError, UnicodeDecodeError):
        continue

if issues:
    warning = "DEBUG STATEMENTS в staged файлах:\n" + "\n".join(issues[:10])
    ctx = {"additionalContext": f"WARNING: {warning}\nУдали перед коммитом (правило CLAUDE.md)."}
    json.dump(ctx, sys.stdout)
