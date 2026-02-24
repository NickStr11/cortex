"""PostToolUse hook: маскирует секреты в выводе инструментов."""
import json
import re
import sys

data = json.load(sys.stdin)
output = data.get("tool_output", "")

if not output or not isinstance(output, str):
    sys.exit(0)

MASKS = [
    (r'(sk-[a-zA-Z0-9]{4})[a-zA-Z0-9]{16,}', r'\1****'),
    (r'(AKIA[0-9A-Z]{4})[0-9A-Z]{12,}', r'\1****'),
    (r'(ghp_[a-zA-Z0-9]{4})[a-zA-Z0-9]{32,}', r'\1****'),
    (r'(gho_[a-zA-Z0-9]{4})[a-zA-Z0-9]{32,}', r'\1****'),
    (r'(xoxb-[0-9]{4})[0-9a-zA-Z-]{20,}', r'\1****'),
    (r'(-----BEGIN (?:RSA |EC )?PRIVATE KEY-----).+?(-----END)', r'\1 [MASKED] \2'),
    (r'(Bearer\s+)[a-zA-Z0-9._\-]{20,}', r'\1****'),
]

masked = output
found = False
for pattern, replacement in MASKS:
    result = re.sub(pattern, replacement, masked, flags=re.DOTALL)
    if result != masked:
        found = True
        masked = result

if found:
    print("WARNING: секреты в выводе замаскированы", file=sys.stderr)
