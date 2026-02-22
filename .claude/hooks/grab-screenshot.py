"""UserPromptSubmit hook: если в сообщении упоминается скриншот/скрин/экран,
автоматически сохраняет изображение из буфера обмена."""
import json
import os
import re
import subprocess
import sys

data = json.load(sys.stdin)
prompt = data.get("prompt", "").lower()

TRIGGERS = r"скрин|screen|экран|снимок|скриншот|screenshot|вот что вижу|посмотри|глянь"

if not re.search(TRIGGERS, prompt):
    sys.exit(0)

script = os.path.join(
    os.environ.get("CLAUDE_PROJECT_DIR", "."),
    "tools", "grab-clipboard.ps1"
)

result = subprocess.run(
    ["powershell", "-ExecutionPolicy", "Bypass", "-File", script],
    capture_output=True, text=True, timeout=10
)

if result.returncode == 0 and result.stdout.strip():
    path = result.stdout.strip()
    output = {
        "additionalContext": f"Скриншот сохранён: {path}\nПрочитай его через Read tool и ответь на вопрос пользователя."
    }
    json.dump(output, sys.stdout)
