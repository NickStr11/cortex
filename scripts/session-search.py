#!/usr/bin/env python3
"""Session search через простой grep по diary/memory/reflections/research.

Без SQLite, без FTS5, без индексации. Просто проход по .md файлам и подсчёт
совпадений. На текущем объёме (60-100 doc) это в 5-7 раз быстрее FTS5 и
имеет zero state — индекс не устаревает.

Когда вырастет до 500+ файлов или появится потребность в bm25 — пересмотрим.
Пока YAGNI.

Usage:
  python scripts/session-search.py "OOM cortex-vm"
  python scripts/session-search.py "deploy" --limit 5
  python scripts/session-search.py "PharmOrder UUID" --since 2026-04-15
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

USER_PROJECT_DIR = Path.home() / ".claude" / "projects" / "D--code-2026-2-cortex"
MEMORY_DIR = USER_PROJECT_DIR / "memory"
DIARY_DIR = MEMORY_DIR / "diary"
REFLECTIONS_DIR = MEMORY_DIR / "reflections"

CORTEX_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", r"D:\code\2026\2\cortex"))
RESEARCH_DIR = CORTEX_DIR / "runtime" / "research"

SOURCES: list[tuple[str, Path, str]] = [
    ("diary", DIARY_DIR, "*.md"),
    ("memory", MEMORY_DIR, "*.md"),
    ("reflection", REFLECTIONS_DIR, "*.md"),
    ("research", RESEARCH_DIR, "*.md"),
]

CONTEXT_CHARS = 80  # вокруг матча


def collect_files(since_ts: float | None = None) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for label, root, pattern in SOURCES:
        if not root.exists():
            continue
        for f in root.glob(pattern):
            if not f.is_file() or f.name.startswith("_"):
                continue
            if since_ts and f.stat().st_mtime < since_ts:
                continue
            out.append((label, f))
    return out


def build_query(q: str) -> re.Pattern[str]:
    """All whitespace-separated tokens must appear in the file (case-insensitive)."""
    tokens = q.strip().split()
    if not tokens:
        raise SystemExit("empty query")
    # We compile a separate pattern per token but match each as substring.
    # To keep ranking simple, we OR them in one regex for snippet extraction
    # and check ALL match in scoring.
    return re.compile("|".join(re.escape(t) for t in tokens), re.IGNORECASE)


def score_file(text: str, tokens: list[str]) -> int:
    """Rough relevance: sum of token occurrences. Zero if any token missing."""
    text_l = text.lower()
    score = 0
    for t in tokens:
        c = text_l.count(t.lower())
        if c == 0:
            return 0
        score += c
    return score


def make_snippet(text: str, pattern: re.Pattern[str]) -> str:
    m = pattern.search(text)
    if not m:
        return ""
    start = max(0, m.start() - CONTEXT_CHARS)
    end = min(len(text), m.end() + CONTEXT_CHARS)
    snip = text[start:end]
    snip = re.sub(r"\s+", " ", snip).strip()
    if start > 0:
        snip = "..." + snip
    if end < len(text):
        snip = snip + "..."
    return snip


def extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines()[:20]:
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line.startswith("## "):
            return line[3:].strip()
    return fallback


def search(query: str, *, limit: int = 10, since: str | None = None) -> int:
    since_ts = None
    if since:
        try:
            since_ts = datetime.fromisoformat(since).timestamp()
        except ValueError:
            print(f"bad --since date: {since} (use YYYY-MM-DD)", file=sys.stderr)
            return 2

    tokens = query.strip().split()
    if not tokens:
        print("empty query", file=sys.stderr)
        return 2

    pattern = build_query(query)
    hits: list[tuple[int, str, Path, str, str, float]] = []

    for label, f in collect_files(since_ts):
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        score = score_file(text, tokens)
        if score == 0:
            continue
        title = extract_title(text, f.stem)
        snip = make_snippet(text, pattern)
        hits.append((score, label, f, title, snip, f.stat().st_mtime))

    if not hits:
        print("(no matches)")
        return 1

    # Sort: score desc, then mtime desc
    hits.sort(key=lambda h: (-h[0], -h[5]))

    for i, (score, label, f, title, snip, mtime) in enumerate(hits[:limit], 1):
        date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        print(f"\n[{i}] {label}/{f.name}  ({date})  hits={score}")
        print(f"    {title}")
        if snip:
            print(f"    {snip}")
        print(f"    → {f}")
    return 0


def stats() -> int:
    files = collect_files()
    by_label: dict[str, int] = {}
    total_size = 0
    for label, f in files:
        by_label[label] = by_label.get(label, 0) + 1
        total_size += f.stat().st_size
    print(f"sources scanned: {sum(by_label.values())} docs, {total_size / 1024:.1f} KB total")
    for label, n in sorted(by_label.items(), key=lambda x: -x[1]):
        print(f"  {label}: {n}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Session search через grep по Cortex memory.")
    p.add_argument("query", nargs="*", help="search terms (whitespace-separated, all must match)")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--since", help="YYYY-MM-DD")
    p.add_argument("--stats", action="store_true", help="show source counts only")
    args = p.parse_args()

    if args.stats:
        return stats()

    if not args.query:
        p.print_help()
        return 2

    return search(" ".join(args.query), limit=args.limit, since=args.since)


if __name__ == "__main__":
    sys.exit(main())
