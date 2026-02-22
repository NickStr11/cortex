"""PreToolUse hook: блокирует запись файлов с секретами."""
import json
import re
import sys

data = json.load(sys.stdin)
tool = data.get("tool_name", "")
inp = data.get("tool_input", {})

content = ""
if tool == "Write":
    content = inp.get("content", "")
elif tool == "Edit":
    content = inp.get("new_string", "")

if not content:
    sys.exit(0)

PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', "API key (sk-...)"),
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key"),
    (r'''(?:api_key|apikey|secret_key|api_secret)\s*[=:]\s*['"][^'"]{8,}['"]''', "hardcoded API key"),
    (r'''password\s*[=:]\s*['"][^'"]{8,}['"]''', "hardcoded password"),
]

for pattern, label in PATTERNS:
    if re.search(pattern, content, re.IGNORECASE):
        print(f"BLOCKED: {label} найден в коде. Используй .env", file=sys.stderr)
        sys.exit(2)
