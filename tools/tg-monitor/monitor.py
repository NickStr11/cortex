"""Telegram Group Monitor — read messages via Telethon userbot.

Usage:
    uv run python tools/tg-monitor/monitor.py                  # fetch all groups
    uv run python tools/tg-monitor/monitor.py --limit 50       # last 50 messages
    uv run python tools/tg-monitor/monitor.py --group aimindset_chat

Requires env:
    TG_API_ID, TG_API_HASH
    (first run will ask for phone number + code for auth)
"""
from __future__ import annotations

import asyncio
import io
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from beartype import beartype
from telethon import TelegramClient  # type: ignore[import-untyped]
from telethon.tl.types import Message  # type: ignore[import-untyped]

from config import DATA_DIR, GROUPS, TG_API_HASH, TG_API_ID, TG_SESSION_NAME, GroupConfig


@dataclass
class SavedMessage:
    """A message saved from a Telegram group."""

    group: str
    sender_id: int
    sender_name: str
    text: str
    date: str  # ISO format
    message_id: int
    reply_to: int | None = None
    has_media: bool = False


@beartype
def output_path(group_name: str) -> Path:
    """Get output JSON path for a group."""
    safe_name = group_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
    return DATA_DIR / f"{safe_name}.json"


@beartype
def load_existing(path: Path) -> list[dict[str, object]]:
    """Load existing messages from JSON file."""
    if not path.exists():
        return []
    data: list[dict[str, object]] = json.loads(path.read_text(encoding="utf-8"))
    return data


@beartype
def save_messages(path: Path, messages: list[dict[str, object]]) -> None:
    """Save messages to JSON, deduplicating by message_id."""
    seen: set[int] = set()
    unique: list[dict[str, object]] = []
    for msg in messages:
        mid = int(msg["message_id"])  # type: ignore[arg-type]
        if mid not in seen:
            seen.add(mid)
            unique.append(msg)
    # Sort by date descending
    unique.sort(key=lambda m: str(m.get("date", "")), reverse=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(unique, ensure_ascii=False, indent=2), encoding="utf-8")


@beartype
async def fetch_group(
    client: TelegramClient,  # type: ignore[type-arg]
    group: GroupConfig,
    limit: int,
) -> list[SavedMessage]:
    """Fetch last N messages from a group."""
    print(f"  Fetching {group.name} ({group.identifier})...")

    entity = await client.get_entity(group.identifier)  # type: ignore[arg-type]
    messages: list[SavedMessage] = []

    msg: Message
    async for msg in client.iter_messages(entity, limit=limit):  # type: ignore[union-attr]
        if not isinstance(msg, Message) or not msg.text:
            continue
        if len(msg.text) < group.min_length:
            continue

        sender_name = ""
        if msg.sender:
            sender_name = getattr(msg.sender, "first_name", "") or ""
            last = getattr(msg.sender, "last_name", "") or ""
            if last:
                sender_name = f"{sender_name} {last}"

        messages.append(
            SavedMessage(
                group=group.name,
                sender_id=msg.sender_id or 0,
                sender_name=sender_name,
                text=msg.text,
                date=msg.date.isoformat() if msg.date else "",
                message_id=msg.id,
                reply_to=msg.reply_to.reply_to_msg_id if msg.reply_to else None,
                has_media=msg.media is not None,
            )
        )

    print(f"    Got {len(messages)} messages (of {limit} checked)")
    return messages


@beartype
async def run(limit: int, group_filter: str | None) -> None:
    """Main async entry point."""
    if not TG_API_ID or not TG_API_HASH:
        print("Error: TG_API_ID and TG_API_HASH required", file=sys.stderr)
        sys.exit(1)

    session_path = str(DATA_DIR / TG_SESSION_NAME)
    client = TelegramClient(session_path, TG_API_ID, TG_API_HASH)
    await client.start()  # type: ignore[func-returns-value]

    print(f"Connected as: {(await client.get_me()).first_name}")  # type: ignore[union-attr]

    groups = GROUPS
    if group_filter:
        groups = [g for g in GROUPS if group_filter in g.identifier or group_filter in g.name.lower()]  # type: ignore[operator]
        if not groups:
            print(f"No group matching '{group_filter}'", file=sys.stderr)
            sys.exit(1)

    for group in groups:
        messages = await fetch_group(client, group, limit)
        if not messages:
            print(f"  No messages for {group.name}")
            continue

        path = output_path(group.name)
        existing = load_existing(path)
        all_msgs = [asdict(m) for m in messages] + existing
        save_messages(path, all_msgs)  # type: ignore[arg-type]
        print(f"  Saved to {path} ({len(messages)} new)")

    await client.disconnect()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Telegram Group Monitor")
    parser.add_argument("--limit", type=int, default=200, help="Messages to fetch per group")
    parser.add_argument("--group", type=str, default=None, help="Filter by group identifier")
    args = parser.parse_args()

    asyncio.run(run(args.limit, args.group))


if __name__ == "__main__":
    main()
