"""Daily Digest Runner — combines heartbeat + tg-monitor + NotebookLM deep research.

Usage:
    uv run python tools/tg-monitor/daily.py                    # full run (with NotebookLM)
    uv run python tools/tg-monitor/daily.py --dry-run          # no telegram
    uv run python tools/tg-monitor/daily.py --skip-heartbeat   # tg-monitor only
    uv run python tools/tg-monitor/daily.py --skip-tg          # heartbeat only
    uv run python tools/tg-monitor/daily.py --no-nlm           # skip NotebookLM, use old Gemini

Requires env:
    TG_API_ID, TG_API_HASH          — for Telethon userbot
    GOOGLE_API_KEY                  — for Gemini digest
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID — for sending
    notebooklm CLI in PATH          — for deep research (optional, falls back to Gemini)
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

import time

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
MARKDOWN_LINK_LINE_RE = re.compile(r"^\d+\.\s+\[.+?\]\(https?://.+?\)\s+—\s+.+$")
X_TREND_LINE_RE = re.compile(r"^\d+\.\s+@[\w.]+.*—\s+.+$")
X_FAIL_MARKERS = (
    "к сожалению",
    "не могу получить доступ",
    "не могу предоставить",
    "не удалось найти",
    "общую информацию",
    "основано на анализе результатов поиска",
    "поскольку конкретные посты не найдены",
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
- не добавляй свои оценки, скепсис, вопросы или мета-комментарии (типа "статья из будущего?", "спорно", "интересно, что...")
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

    contents = f"{prompt}\n\n" + "\n".join(payload_lines)
    text: str = ""
    for attempt in range(2):
        try:
            client = genai.Client()
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=contents,
            )
            text = (response.text or "").strip()
            if text:
                break
        except Exception as e:
            print(f"  {source_name} summarize error (attempt {attempt + 1}): {e}")
            if attempt == 0:
                time.sleep(2)

    return text or None


@beartype
def summarize_hn_links_ru(stories: list[tuple[str, str, int, int]]) -> str | None:
    """Generate short Russian comments for top HN links."""
    return summarize_links_ru(stories, "Hacker News", "HN Ссылки")


@beartype
def summarize_reddit_links_ru(stories: list[tuple[str, str, int, int, str]]) -> str | None:
    """Generate short Russian comments for top Reddit posts."""
    return summarize_links_ru(stories, "Reddit", "Reddit Ссылки")


@beartype
def _validate_summary(summary: str, expected_links: int) -> bool:
    """Check that summary contains real markdown links (at least 50% of expected)."""
    link_count = len(re.findall(r"\[.+?\]\(https?://.+?\)", summary))
    min_required = max(1, expected_links // 2)
    return link_count >= min_required


@beartype
def _sanitize_link_section(summary: str, header: str, expected_links: int) -> str | None:
    """Keep only a clean markdown section with numbered links."""
    lines = summary.splitlines()
    try:
        start_index = next(i for i, line in enumerate(lines) if line.strip() == f"### {header}")
    except StopIteration:
        return None

    sanitized = [f"### {header}"]
    item_count = 0

    for line in lines[start_index + 1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if MARKDOWN_LINK_LINE_RE.match(stripped):
            sanitized.append(stripped)
            item_count += 1
            continue
        if stripped.startswith("### ") and item_count > 0:
            break
        if item_count > 0:
            break

    min_required = max(1, expected_links // 2) if expected_links > 0 else 1
    if item_count < min_required:
        return None
    return "\n".join(sanitized)


@beartype
def _sanitize_x_section(summary: str) -> str | None:
    """Keep only a clean X/Twitter section, skip fallback chatter."""
    lowered = summary.lower()
    if any(marker in lowered for marker in X_FAIL_MARKERS):
        return None

    lines = summary.splitlines()
    try:
        start_index = next(i for i, line in enumerate(lines) if line.strip() == "### X/Twitter Тренды")
    except StopIteration:
        return None

    sanitized = ["### X/Twitter Тренды"]
    item_count = 0

    for line in lines[start_index + 1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if X_TREND_LINE_RE.match(stripped):
            sanitized.append(stripped)
            item_count += 1
            continue
        if stripped.startswith("### ") and item_count > 0:
            break
        if item_count > 0:
            break

    if item_count < 2:
        return None
    return "\n".join(sanitized)


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

Если конкретных постов не нашлось — верни только слово EMPTY.
Не выдумывай посты и авторов."""

    try:
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        text = (response.text or "").strip()
        if not text:
            return None
        # Filter out empty/failed responses
        fail_markers = ["не удалось найти", "к сожалению", "EMPTY"]
        if any(m in text for m in fail_markers) and "@" not in text:
            print("  X/Twitter: no real data, skipping")
            return None
        return text
    except Exception as e:
        print(f"  X/Twitter trends error: {e}")
        return None


@beartype
def format_heartbeat_for_daily(raw_heartbeat: str, date_label: str) -> str:
    """Build a concise heartbeat block for the daily digest."""
    sections: list[str] = []

    # HN
    try:
        hn_stories = extract_hn_links(raw_heartbeat, limit=10)
        hn_summary = summarize_hn_links_ru(hn_stories)
        clean_hn_summary = (
            _sanitize_link_section(hn_summary, "HN Ссылки", len(hn_stories))
            if hn_summary and _validate_summary(hn_summary, len(hn_stories))
            else None
        )
        if clean_hn_summary:
            sections.append(clean_hn_summary)
        elif hn_stories:
            lines = ["### HN Ссылки"]
            for index, (title, url, score, comments) in enumerate(hn_stories, start=1):
                lines.append(
                    f"{index}. [{title}]({url}) — {score} points, {comments} comments"
                )
            sections.append("\n".join(lines))
    except Exception as e:
        print(f"  HN section error: {e}")

    # Reddit
    try:
        reddit_posts = extract_reddit_posts(raw_heartbeat)
        reddit_summary = summarize_reddit_links_ru(reddit_posts)
        clean_reddit_summary = (
            _sanitize_link_section(reddit_summary, "Reddit Ссылки", len(reddit_posts))
            if reddit_summary and _validate_summary(reddit_summary, len(reddit_posts))
            else None
        )
        if clean_reddit_summary:
            sections.append(clean_reddit_summary)
        elif reddit_posts:
            lines = ["### Reddit Ссылки"]
            for index, (title, url, score, comments, sub) in enumerate(reddit_posts, start=1):
                lines.append(
                    f"{index}. [{title}]({url}) — r/{sub}, {score} points, {comments} comments"
                )
            sections.append("\n".join(lines))
    except Exception as e:
        print(f"  Reddit section error: {e}")

    # X/Twitter (via Gemini grounded search)
    try:
        x_trends = fetch_x_ai_trends()
        clean_x_trends = _sanitize_x_section(x_trends) if x_trends else None
        if clean_x_trends:
            sections.append(clean_x_trends)
    except Exception as e:
        print(f"  X/Twitter section error: {e}")

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


@beartype
def _nlm_cmd(*args: str, timeout: int = 60) -> tuple[int, str]:
    """Run notebooklm CLI command and return (returncode, stdout)."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        ["notebooklm", *args],
        capture_output=True,
        timeout=timeout,
        env=env,
    )
    stdout = result.stdout.decode("utf-8", errors="replace").strip() if result.stdout else ""
    return result.returncode, stdout


@beartype
def notebooklm_deep_research(
    hn_links: list[tuple[str, str, int, int]],
    reddit_links: list[tuple[str, str, int, int, str]],
    tg_digest: str | None,
    date_label: str,
) -> str | None:
    """Create NotebookLM notebook with all sources, get cross-referenced AI trends analysis."""
    import json
    import shutil
    import tempfile

    if not shutil.which("notebooklm"):
        print("  NotebookLM CLI not found in PATH, skipping")
        return None

    # Check auth
    rc, out = _nlm_cmd("auth", "check", "--json")
    if rc != 0:
        print("  NotebookLM: auth failed, skipping deep research")
        return None

    # Create notebook
    title = f"AI Trends {date_label}"
    rc, out = _nlm_cmd("create", title, "--json")
    if rc != 0:
        print(f"  NotebookLM: create failed: {out[:200]}")
        return None

    try:
        notebook = json.loads(out)
        notebook_id = notebook["notebook"]["id"]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  NotebookLM: parse error: {e}")
        return None

    _nlm_cmd("use", notebook_id)
    source_ids: list[str] = []

    # Add HN article URLs (top 7)
    for story_title, url, score, comments in hn_links[:7]:
        rc, out = _nlm_cmd("source", "add", url, "--json", timeout=30)
        if rc == 0:
            try:
                src = json.loads(out)
                source_ids.append(src["source"]["id"])
                print(f"    + HN: {story_title[:50]}")
            except (json.JSONDecodeError, KeyError):
                pass

    # Add Reddit URLs (top 5)
    for story_title, url, score, comments, sub in reddit_links[:5]:
        rc, out = _nlm_cmd("source", "add", url, "--json", timeout=30)
        if rc == 0:
            try:
                src = json.loads(out)
                source_ids.append(src["source"]["id"])
                print(f"    + Reddit: {story_title[:50]}")
            except (json.JSONDecodeError, KeyError):
                pass

    # Add TG chat as text source (raw messages or digest)
    tg_tmp: str | None = None
    if tg_digest:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8",
        ) as f:
            f.write(tg_digest)  # already has header from _collect_raw_chat or digest
            tg_tmp = f.name
        rc, out = _nlm_cmd("source", "add", tg_tmp, "--json", timeout=30)
        if rc == 0:
            try:
                src = json.loads(out)
                source_ids.append(src["source"]["id"])
                print("    + TG digest")
            except (json.JSONDecodeError, KeyError):
                pass

    # Cleanup temp file
    if tg_tmp and os.path.exists(tg_tmp):
        os.unlink(tg_tmp)

    if not source_ids:
        print("  NotebookLM: no sources added successfully")
        return None

    # Wait for all sources to process
    print(f"  Waiting for {len(source_ids)} sources to process...")
    for sid in source_ids:
        _nlm_cmd("source", "wait", sid, "--timeout", "120", timeout=130)

    # Ask for deep cross-referenced analysis
    print("  Asking NotebookLM for deep analysis...")
    analysis_prompt = (
        "Проанализируй ВСЕ загруженные источники вместе. "
        "Найди пересечения и паттерны между ними.\n\n"
        "Структура ответа (markdown, русский):\n\n"
        "## Главные тренды\n"
        "Что обсуждают сразу в нескольких источниках. "
        "Конкретные проекты, компании, технологии.\n\n"
        "## Восходящие темы\n"
        "Что только начинает появляться, но уже есть сигналы из 2+ источников.\n\n"
        "## Инструменты и проекты\n"
        "Конкретные тулы, библиотеки, продукты которые набирают тягу. "
        "Ссылки если есть.\n\n"
        "## Из Telegram-сообщества\n"
        "Живые обсуждения из русскоязычных AI-чатов. "
        "Цитируй реальные высказывания участников, покажи о чём спорят, "
        "что пробуют, какие инструменты обсуждают. "
        "Упоминай имена авторов интересных мыслей.\n\n"
        "## Что стоит проверить\n"
        "2-3 темы которые стоит изучить глубже.\n\n"
        "Правила:\n"
        "- Только факты из источников, не выдумывай\n"
        "- Конкретика > абстракции\n"
        "- Если тема есть в нескольких источниках — отметь это\n"
        "- Ссылки на оригинальные статьи где возможно\n"
        "- Telegram-источник — это ЖИВОЙ ЧАТ, не саммари. "
        "Цитируй, передавай атмосферу, показывай реальные мнения людей"
    )

    rc, out = _nlm_cmd("ask", analysis_prompt, "--json", timeout=90)
    if rc != 0:
        print(f"  NotebookLM ask failed: {out[:200]}")
        return None

    try:
        answer = json.loads(out)
        result_text: str = answer.get("answer", "")
        return result_text if result_text else None
    except json.JSONDecodeError:
        return out if out else None


@beartype
def _collect_raw_chat(hours: int) -> str | None:
    """Collect enriched+filtered TG messages as readable chat log for NotebookLM."""
    try:
        sys.path.insert(0, str(TG_MONITOR_DIR))
        from digest import load_recent_messages, enrich_messages, filter_top_messages

        groups_messages = load_recent_messages(hours)
        if not groups_messages:
            return None

        all_lines: list[str] = []
        for group_name, messages in groups_messages.items():
            enriched = enrich_messages(messages)
            top = filter_top_messages(enriched)
            if len(top) < 5:
                top = sorted(enriched, key=lambda m: str(m.get("date", "")))

            all_lines.append(f"\n## {group_name}\n")
            for msg in top[:80]:  # cap per group
                sender = msg.get("sender_name", "?")
                text = str(msg.get("text", "")).strip()
                date = str(msg.get("date", ""))[:16]
                if not text or len(text) < 10:
                    continue
                # Truncate very long messages
                if len(text) > 500:
                    text = text[:500] + "..."
                reply_ctx = ""
                if msg.get("reply_to_text"):
                    reply_text = str(msg["reply_to_text"])[:100]
                    reply_sender = msg.get("reply_to_sender", "?")
                    reply_ctx = f" [в ответ {reply_sender}: {reply_text}]"
                all_lines.append(f"[{date}] {sender}{reply_ctx}: {text}")

        if not all_lines:
            return None

        raw_chat = "# Telegram AI Communities — Live Chat\n" + "\n".join(all_lines)
        print(f"  Raw chat log: {len(raw_chat)} chars, {len(all_lines)} lines")
        return raw_chat
    except Exception as e:
        print(f"  Raw chat collect error: {e}")
        return None


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Daily Digest Runner")
    parser.add_argument("--dry-run", action="store_true", help="Don't send to Telegram")
    parser.add_argument("--skip-heartbeat", action="store_true", help="Skip heartbeat")
    parser.add_argument("--skip-tg", action="store_true", help="Skip TG monitor")
    parser.add_argument("--no-nlm", action="store_true", help="Skip NotebookLM, use old Gemini")
    parser.add_argument("--hours", type=int, default=24, help="Time window for TG digest")
    args = parser.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not args.dry_run and (not token or not chat_id):
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    date_label = now[:10]
    print(f"Daily Digest — {now}")

    # Phase 1: Collect raw data
    raw_heartbeat: str | None = None
    hn_links: list[tuple[str, str, int, int]] = []
    reddit_links: list[tuple[str, str, int, int, str]] = []

    if not args.skip_heartbeat:
        raw_heartbeat = run_heartbeat()
        if raw_heartbeat:
            hn_links = extract_hn_links(raw_heartbeat, limit=10)
            reddit_links = extract_reddit_posts(raw_heartbeat)

    # Phase 2: TG Monitor
    tg_digest_text: str | None = None
    tg_raw_chat: str | None = None
    if not args.skip_tg:
        run_tg_fetch()
        tg_raw_chat = _collect_raw_chat(args.hours)
        tg_digest_text = run_tg_digest(args.dry_run, args.hours)

    # Phase 3: Deep research via NotebookLM (or fallback to Gemini)
    parts: list[str] = []
    used_nlm = False

    # Prefer raw chat for NotebookLM (живее), fallback digest for Gemini
    nlm_tg_source = tg_raw_chat or tg_digest_text
    if not args.no_nlm and (hn_links or reddit_links or nlm_tg_source):
        print("\n[4/4] NotebookLM deep research...")
        deep = notebooklm_deep_research(hn_links, reddit_links, nlm_tg_source, date_label)
        if deep:
            parts.append(f"# AI Intelligence Briefing — {date_label}\n\n{deep}")
            # Append source links
            link_lines: list[str] = []
            for title, url, *_ in hn_links[:10]:
                link_lines.append(f"- [{title}]({url})")
            for title, url, *rest in reddit_links[:5]:
                sub = rest[2] if len(rest) > 2 else ""
                prefix = f"r/{sub}: " if sub else ""
                link_lines.append(f"- {prefix}[{title}]({url})")
            if link_lines:
                parts.append("## Источники\n" + "\n".join(link_lines))
            used_nlm = True

    # Fallback: old Gemini approach
    if not used_nlm:
        if not args.no_nlm:
            print("  NotebookLM unavailable, falling back to Gemini summaries")
        if raw_heartbeat:
            parts.append(format_heartbeat_for_daily(raw_heartbeat, date_label))
        if tg_digest_text:
            parts.append(tg_digest_text)

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

    caption = f"AI Intelligence Briefing — {date_str}" if used_nlm else f"Daily Digest — {date_str}"
    msg_id = send_file_to_telegram(md_path, caption, token, chat_id)
    print(f"Sent to Telegram: message_id={msg_id}")


if __name__ == "__main__":
    main()
