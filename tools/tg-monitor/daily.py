"""Daily Digest Runner — combines heartbeat + tg-monitor into one run.

Usage:
    uv run python tools/tg-monitor/daily.py                    # full run
    uv run python tools/tg-monitor/daily.py --dry-run          # no telegram
    uv run python tools/tg-monitor/daily.py --skip-heartbeat   # tg-monitor only
    uv run python tools/tg-monitor/daily.py --skip-tg          # heartbeat only

Requires env:
    TG_API_ID, TG_API_HASH          — for Telethon userbot
    GOOGLE_API_KEY                  — for Gemini digest
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID — for sending
"""
from __future__ import annotations

import asyncio
import io
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx
from beartype import beartype

ROOT = Path(__file__).parent.parent.parent
HEARTBEAT_DIR = ROOT / "tools" / "heartbeat"
TG_MONITOR_DIR = Path(__file__).parent


@beartype
def send_file_to_telegram(filepath: Path, caption: str, token: str, chat_id: str) -> int:
    """Send file to Telegram. Returns message_id."""
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with open(filepath, "rb") as f:
        response = httpx.post(
            url,
            data={"chat_id": chat_id, "caption": caption},
            files={"document": (filepath.name, f)},
            timeout=30,
        )
    response.raise_for_status()
    result: dict[str, object] = response.json()
    message = result["result"]  # type: ignore[index]
    return int(message["message_id"])  # type: ignore[index]


@beartype
def run_heartbeat() -> str | None:
    """Run heartbeat fetch and return raw markdown."""
    print("\n[1/3] Running Heartbeat...")
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "--mode", "fetch"],
            cwd=str(HEARTBEAT_DIR),
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
        )
        if result.returncode != 0:
            print(f"  Heartbeat failed: {result.stderr[:200]}")
            return None
        output = result.stdout.strip()
        print(f"  Heartbeat: {len(output)} chars")
        return output
    except Exception as e:
        print(f"  Heartbeat error: {e}")
        return None


@beartype
def run_tg_fetch() -> bool:
    """Fetch new messages from TG groups."""
    print("\n[2/3] Fetching TG groups...")
    try:
        # Import and run directly to reuse the same event loop
        sys.path.insert(0, str(TG_MONITOR_DIR))
        from monitor import run as monitor_run

        asyncio.run(monitor_run(limit=200, group_filter=None))
        return True
    except Exception as e:
        print(f"  TG fetch error: {e}")
        return False


@beartype
def run_tg_digest(dry_run: bool, hours: int) -> str | None:
    """Generate TG group digest via MapReduce pipeline."""
    print("\n[3/3] Generating TG digest (MapReduce)...")
    try:
        sys.path.insert(0, str(TG_MONITOR_DIR))
        from digest import (
            load_recent_messages,
            enrich_messages,
            filter_top_messages,
            pipeline_map,
            pipeline_reduce,
            pipeline_verify,
            CHUNK_SIZE,
        )
        import math

        groups_messages = load_recent_messages(hours)
        if not groups_messages:
            print("  No recent TG messages")
            return None

        parts: list[str] = []
        for group_name, messages in groups_messages.items():
            print(f"  {group_name}: {len(messages)} messages")
            # Enrich
            enriched = enrich_messages(messages)
            # Filter
            top = filter_top_messages(enriched)
            if len(top) < 5:
                top = sorted(enriched, key=lambda m: str(m.get("date", "")))
            print(f"    filtered: {len(top)} messages")
            # MAP
            n_chunks = max(1, math.ceil(len(top) / CHUNK_SIZE))
            chunks = [top[i * CHUNK_SIZE:(i + 1) * CHUNK_SIZE] for i in range(n_chunks)]
            topics = pipeline_map(chunks)
            # REDUCE
            digest = pipeline_reduce(group_name, topics)
            # VERIFY
            verify_result = pipeline_verify(digest, top)
            if "HALLUCINATION" in verify_result.upper():
                print(f"    WARNING: hallucinations detected in {group_name}")
            parts.append(digest)
            print(f"    digest: {len(digest)} chars")

        return "\n\n---\n\n".join(parts)
    except Exception as e:
        print(f"  TG digest error: {e}")
        return None


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Daily Digest Runner")
    parser.add_argument("--dry-run", action="store_true", help="Don't send to Telegram")
    parser.add_argument("--skip-heartbeat", action="store_true", help="Skip heartbeat")
    parser.add_argument("--skip-tg", action="store_true", help="Skip TG monitor")
    parser.add_argument("--hours", type=int, default=24, help="Time window for TG digest")
    args = parser.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not args.dry_run and (not token or not chat_id):
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"Daily Digest — {now}")

    parts: list[str] = []

    # Heartbeat
    if not args.skip_heartbeat:
        hb = run_heartbeat()
        if hb:
            # Trim heartbeat to key findings (first 1500 chars)
            summary = hb[:1500]
            if len(hb) > 1500:
                summary += "\n..."
            parts.append(f"*Heartbeat — {now[:10]}*\n\n{summary}")

    # TG Monitor
    if not args.skip_tg:
        run_tg_fetch()
        digest = run_tg_digest(args.dry_run, args.hours)
        if digest:
            parts.append(digest)

    if not parts:
        print("\nNothing to report today.")
        return

    full_digest = "\n\n---\n\n".join(parts)
    print(f"\n{'='*50}\n{full_digest}\n{'='*50}")
    print(f"Total length: {len(full_digest)} chars")

    if args.dry_run:
        print("\nDry run — not sending")
        return

    # Save as .md and send as file
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    md_path = Path(f"/tmp/daily_digest_{date_str}.md")
    md_path.write_text(full_digest, encoding="utf-8")
    print(f"\nSaved: {md_path}")

    caption = f"Daily Digest — {date_str}"
    msg_id = send_file_to_telegram(md_path, caption, token, chat_id)
    print(f"Sent to Telegram: message_id={msg_id}")


if __name__ == "__main__":
    main()
