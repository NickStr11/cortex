from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
from beartype import beartype

CLAUDE_CWD = Path(__file__).resolve().parents[2]  # cortex root
SCRIPT_DIR = Path(__file__).resolve().parent

# load .env from cortex root
_env_file = CLAUDE_CWD / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USERS: set[int] = {691773226}
SUBPROCESS_TIMEOUT = 120
TELEGRAM_MAX_LENGTH = 4096
HISTORY_FILE = SCRIPT_DIR / "history.json"
MAX_HISTORY = 20


@beartype
def load_history() -> list[dict[str, str]]:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text("utf-8"))
    return []


@beartype
def save_history(history: list[dict[str, str]]) -> None:
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), "utf-8")


@beartype
def build_prompt(history: list[dict[str, str]], message: str) -> str:
    if not history:
        return message
    lines = ["Previous conversation (for context):"]
    for entry in history:
        lines.append(f"User: {entry['user']}")
        lines.append(f"Assistant: {entry['assistant']}")
    lines.append(f"\nNow answer this:\n{message}")
    return "\n".join(lines)


@beartype
def api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"


@beartype
def send_message(client: httpx.Client, chat_id: int, text: str) -> None:
    if len(text) <= TELEGRAM_MAX_LENGTH:
        client.post(api_url("sendMessage"), json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        })
    else:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(text)
            tmp_path = f.name
        try:
            with open(tmp_path, "rb") as doc:
                client.post(api_url("sendDocument"), data={
                    "chat_id": str(chat_id),
                }, files={"document": ("response.md", doc, "text/markdown")})
        finally:
            os.unlink(tmp_path)


@beartype
def run_claude(prompt: str) -> str:
    try:
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            ["claude", "-p", "--output-format", "text", prompt],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
            cwd=str(CLAUDE_CWD),
            env=env,
            encoding="utf-8",
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr:
            output = output or result.stderr.strip()
        return output or "(empty response)"
    except subprocess.TimeoutExpired:
        return "(timeout)"
    except FileNotFoundError:
        return "(error: claude CLI not found in PATH)"


@beartype
def poll(client: httpx.Client, offset: int) -> int:
    resp = client.get(api_url("getUpdates"), params={
        "offset": offset,
        "timeout": 30,
    }, timeout=40)
    updates = resp.json().get("result", [])

    for update in updates:
        offset = update["update_id"] + 1
        msg = update.get("message")
        if not msg:
            continue

        user_id = msg.get("from", {}).get("id")
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if user_id not in ALLOWED_USERS:
            continue
        if not text or text.startswith("/start"):
            continue

        # /new — reset history
        if text.strip() == "/new":
            save_history([])
            send_message(client, chat_id, "History cleared.")
            continue

        try:
            print(f"<< {text[:80]}", flush=True)
            send_message(client, chat_id, "thinking...")

            history = load_history()
            prompt = build_prompt(history, text)
            answer = run_claude(prompt)

            # save to history (keep last N)
            history.append({"user": text, "assistant": answer})
            save_history(history[-MAX_HISTORY:])

            print(f">> {answer[:80]}", flush=True)
            send_message(client, chat_id, answer)
        except Exception as e:
            print(f"error processing message: {e}", flush=True)

    return offset


def main() -> None:
    if not BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN not set. Add it to .env or export it.")
        sys.exit(1)

    print(f"tg-bridge started | cwd={CLAUDE_CWD} | history={MAX_HISTORY} msgs", flush=True)
    offset = 0

    with httpx.Client() as client:
        # flush old updates
        resp = client.get(api_url("getUpdates"), params={"offset": -1}, timeout=10)
        updates = resp.json().get("result", [])
        if updates:
            offset = updates[-1]["update_id"] + 1

        while True:
            try:
                offset = poll(client, offset)
            except httpx.ReadTimeout:
                continue
            except KeyboardInterrupt:
                print("\nstopped")
                break
            except Exception as e:
                print(f"error: {e}")


if __name__ == "__main__":
    main()
