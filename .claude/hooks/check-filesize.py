"""PostToolUse hook: предупреждает если файл превышает лимит строк."""
import json
import os
import sys

data = json.load(sys.stdin)
inp = data.get("tool_input", {})
file_path = inp.get("file_path", "")

if not file_path or not os.path.exists(file_path):
    sys.exit(0)

ext = os.path.splitext(file_path)[1].lower()
if ext not in (".py", ".js", ".ts", ".tsx", ".jsx", ".vue", ".svelte", ".html", ".css"):
    sys.exit(0)

try:
    with open(file_path, encoding="utf-8", errors="ignore") as f:
        line_count = sum(1 for _ in f)
except (OSError, UnicodeDecodeError):
    sys.exit(0)

if line_count > 700:
    result = {
        "additionalContext": (
            f"WARNING: {os.path.basename(file_path)} = {line_count} строк "
            f"(лимит 700). Разбей файл на модули."
        )
    }
    json.dump(result, sys.stdout)
elif line_count > 500:
    result = {
        "additionalContext": (
            f"NOTE: {os.path.basename(file_path)} = {line_count} строк "
            f"(лимит 700). Следи за размером."
        )
    }
    json.dump(result, sys.stdout)
