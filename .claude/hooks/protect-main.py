"""PreToolUse hook: блокирует git commit в ветке main/master."""
import json
import subprocess
import sys

data = json.load(sys.stdin)
command = data.get("tool_input", {}).get("command", "")

if "git commit" not in command:
    sys.exit(0)

result = subprocess.run(
    ["git", "branch", "--show-current"],
    capture_output=True, text=True
)
branch = result.stdout.strip()

if branch in ("main", "master"):
    print(
        f"BLOCKED: коммит в ветку '{branch}' запрещён. "
        "Создай feature-ветку: git checkout -b feat/...",
        file=sys.stderr
    )
    sys.exit(2)
