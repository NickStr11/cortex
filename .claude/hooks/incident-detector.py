"""PostToolUse hook: detect repeated Bash failures and suggest incident logging."""
import json
import os
import sys
from pathlib import Path

COUNTER_DIR = Path(os.environ.get("TMPDIR", os.environ.get("TEMP", "/tmp")))
FAIL_COUNTER_FILE = COUNTER_DIR / "claude_fail_counter.json"
DEBUG_LOG = COUNTER_DIR / "claude_incident_debug.log"
THRESHOLD = 2


def debug(msg):
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def load_counter():
    if FAIL_COUNTER_FILE.exists():
        try:
            return json.loads(FAIL_COUNTER_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"consecutive_fails": 0}


def save_counter(data):
    try:
        FAIL_COUNTER_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception as e:
        debug(f"save error: {e}")


try:
    raw = sys.stdin.read()
    data = json.loads(raw)
    debug(f"keys: {list(data.keys())}")

    # Try multiple ways to detect failure
    tool_result = data.get("tool_result", {})
    exit_code = None
    if isinstance(tool_result, dict):
        exit_code = tool_result.get("exit_code")
        stderr = tool_result.get("stderr", "")
    elif isinstance(tool_result, str):
        stderr = tool_result
    else:
        stderr = str(tool_result)

    is_failure = (exit_code is not None and exit_code != 0) or ("Exit code" in stderr and "Exit code 0" not in stderr)
    debug(f"exit_code={exit_code}, is_failure={is_failure}, stderr_preview={stderr[:100] if stderr else 'empty'}")

    counter = load_counter()

    if is_failure:
        counter["consecutive_fails"] += 1
        save_counter(counter)
        debug(f"fails={counter['consecutive_fails']}")

        if counter["consecutive_fails"] >= THRESHOLD:
            print(
                f"⚠ {counter['consecutive_fails']} consecutive Bash failures. "
                "Consider: 1) /systematic-debugging  2) Log incident in docs/incidents.md"
            )
    else:
        if counter.get("consecutive_fails", 0) > 0:
            counter["consecutive_fails"] = 0
            save_counter(counter)
            debug("reset counter")

except Exception as e:
    debug(f"hook error: {e}")
