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
import re
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
HN_LINE_RE = re.compile(
    r"^\d+\.\s+\*\*(?P<title>.+?)\*\*\s+\(score:\s*(?P<score>\d+),\s*comments:\s*(?P<comments>\d+)\)$"
)
REDDIT_LINE_RE = re.compile(
    r"^\d+\.\s+\*\*(?P<title>.+?)\*\*\s+\(score:\s*(?P<score>\d+),\s*comments:\s*(?P<comments>\d+),\s*r/(?P<subreddit>\S+)\)$"
)


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
def extract_hn_links(raw_heartbeat: str, limit: int = 5) -> list[tuple[str, str, int, int]]:
    """Extract top HN stories from raw heartbeat markdown."""
    lines = raw_heartbeat.splitlines()
    in_hn = False
    results: list[tuple[str, str, int, int]] = []

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## Hacker News Top Stories"):
            in_hn = True
            continue
        if in_hn and stripped.startswith("## "):
            break
        if not in_hn:
            continue

        match = HN_LINE_RE.match(stripped)
        if not match:
            continue
        if index + 1 >= len(lines):
            continue

        url = lines[index + 1].strip()
        if not url.startswith("http"):
            continue

        results.append((
            match.group("title"),
            url,
            int(match.group("score")),
            int(match.group("comments")),
        ))
        if len(results) >= limit:
            break

    return results


@beartype
def extract_reddit_posts(raw_heartbeat: str, limit: int = 5) -> list[tuple[str, str, int, int, str]]:
    """Extract top Reddit posts from raw heartbeat markdown."""
    lines = raw_heartbeat.splitlines()
    in_reddit = False
    results: list[tuple[str, str, int, int, str]] = []

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## Reddit Top Posts"):
            in_reddit = True
            continue
        if in_reddit and stripped.startswith("## "):
            break
        if not in_reddit:
            continue

        match = REDDIT_LINE_RE.match(stripped)
        if not match:
            continue
        if index + 1 >= len(lines):
            continue

        url = lines[index + 1].strip()
        if not url.startswith("http"):
            continue

        results.append((
            match.group("title"),
            url,
            int(match.group("score")),
            int(match.group("comments")),
            match.group("subreddit"),
        ))
        if len(results) >= limit:
            break

    return results


@beartype
def summarize_links_ru(
    stories: list[tuple[str, str, int, int]] | list[tuple[str, str, int, int, str]],
    source_name: str,
    header: str,
) -> str | None:
    """Generate short Russian comments for links from any source."""
    if not stories or not os.environ.get("GOOGLE_API_KEY"):
        return None

    from google import genai

    prompt = f"""Ниже топовые ссылки с {source_name}.

Для КАЖДОЙ ссылки дай короткий комментарий на русском:
- 1 строка на ссылку
- не выдумывай факты, которых нет в названии, домене, score и comments
- можно осторожно интерпретировать, почему ссылка интересна
- без воды, без маркетингового тона
- сохраняй оригинальный title на английском

Формат строго такой:
### {header}
1. [Original Title](url) — короткий русский комментарий
2. [Original Title](url) — короткий русский комментарий
"""

    payload_lines: list[str] = []
    for index, story in enumerate(stories, start=1):
        title, url, score, comments = story[0], story[1], story[2], story[3]
        extra = f"\nsubreddit=r/{story[4]}" if len(story) > 4 else ""
        payload_lines.append(
            f"{index}. title={title}\nurl={url}\nscore={score}\ncomments={comments}{extra}"
        )

    try:
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{prompt}\n\n" + "\n".join(payload_lines),
        )
    except Exception as e:
        print(f"  {source_name} summarize error: {e}")
        return None

    text = response.text or ""
    return text.strip() or None


@beartype
def summarize_hn_links_ru(stories: list[tuple[str, str, int, int]]) -> str | None:
    """Generate short Russian comments for top HN links."""
    return summarize_links_ru(stories, "Hacker News", "HN Ссылки")


@beartype
def summarize_reddit_links_ru(stories: list[tuple[str, str, int, int, str]]) -> str | None:
    """Generate short Russian comments for top Reddit posts."""
    return summarize_links_ru(stories, "Reddit", "Reddit Ссылки")


@beartype
def fetch_x_ai_trends() -> str | None:
    """Fetch AI/agents/automation trends from X/Twitter via Gemini grounded search."""
    if not os.environ.get("GOOGLE_API_KEY"):
        return None

    from google import genai
    from google.genai import types

    print("  Fetching X/Twitter AI trends via Gemini Search...")

    prompt = """Найди 5-7 самых обсуждаемых постов в Twitter/X за последние 24 часа
по темам: AI agents, AI automation, AI business cases, LLM, Claude, GPT, Codex.

Для каждого поста:
- автор (@handle)
- суть поста (1 строка на русском)
- ссылка если есть
- примерный engagement (likes/reposts если видно)

Формат:
### X/Twitter Тренды
1. @handle — суть поста на русском
2. @handle — суть поста на русском

Если конкретных постов не нашлось — дай топ обсуждаемые темы по AI в Twitter.
Не выдумывай посты и авторов. Если данных мало — так и скажи."""

    try:
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        text = response.text or ""
        return text.strip() or None
    except Exception as e:
        print(f"  X/Twitter trends error: {e}")
        return None


@beartype
def format_heartbeat_for_daily(raw_heartbeat: str, date_label: str) -> str:
    """Build a concise heartbeat block for the daily digest."""
    sections: list[str] = []

    # HN
    hn_stories = extract_hn_links(raw_heartbeat)
    hn_summary = summarize_hn_links_ru(hn_stories)
    if hn_summary:
        sections.append(hn_summary)
    elif hn_stories:
        lines = ["### HN Ссылки"]
        for index, (title, url, score, comments) in enumerate(hn_stories, start=1):
            lines.append(
                f"{index}. [{title}]({url}) — {score} points, {comments} comments"
            )
        sections.append("\n".join(lines))

    # Reddit
    reddit_posts = extract_reddit_posts(raw_heartbeat)
    reddit_summary = summarize_reddit_links_ru(reddit_posts)
    if reddit_summary:
        sections.append(reddit_summary)
    elif reddit_posts:
        lines = ["### Reddit Ссылки"]
        for index, (title, url, score, comments, sub) in enumerate(reddit_posts, start=1):
            lines.append(
                f"{index}. [{title}]({url}) — r/{sub}, {score} points, {comments} comments"
            )
        sections.append("\n".join(lines))

    # X/Twitter (via Gemini grounded search)
    x_trends = fetch_x_ai_trends()
    if x_trends:
        sections.append(x_trends)

    if sections:
        body = "\n\n".join(sections)
        return f"*Heartbeat — {date_label}*\n\n{body}"

    # Fallback: raw heartbeat truncated
    fallback = raw_heartbeat[:1500]
    if len(raw_heartbeat) > 1500:
        fallback += "\n..."
    return f"*Heartbeat — {date_label}*\n\n{fallback}"


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
            has_verification_issues,
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
            if has_verification_issues(verify_result):
                print(f"    WARNING: verification flagged issues in {group_name}")
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
            parts.append(format_heartbeat_for_daily(hb, now[:10]))

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
