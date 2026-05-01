#!/usr/bin/env python3
"""Session search через SQLite FTS5 поверх diary, memory, research-заметок.

Индексирует:
  - ~/.claude/projects/D--code-2026-2-cortex/memory/diary/*.md   (per-user diary)
  - ~/.claude/projects/D--code-2026-2-cortex/memory/*.md         (feedback/project/personal/reference)
  - ~/.claude/projects/D--code-2026-2-cortex/memory/reflections/*.md
  - runtime/research/*.md                                        (если есть)

БД: ~/.claude/projects/D--code-2026-2-cortex/memory/search-index.db
Зависимости: только stdlib (sqlite3 c FTS5 — встроен в python 3.7+)

Usage:
  python scripts/session-search.py reindex                       # полный reindex
  python scripts/session-search.py "OOM cortex-vm"               # поиск
  python scripts/session-search.py "OOM" --limit 5               # top-5
  python scripts/session-search.py "deploy" --since 2026-04-15   # только новее
  python scripts/session-search.py stats                         # размер индекса
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Windows console fix — cp1251 ломает кириллицу и unicode-стрелки.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

# Where to look
USER_PROJECT_DIR = Path.home() / ".claude" / "projects" / "D--code-2026-2-cortex"
MEMORY_DIR = USER_PROJECT_DIR / "memory"
DIARY_DIR = MEMORY_DIR / "diary"
REFLECTIONS_DIR = MEMORY_DIR / "reflections"

# Cortex repo runtime (worktree-local)
CORTEX_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", r"D:\code\2026\2\cortex"))
RESEARCH_DIR = CORTEX_DIR / "runtime" / "research"

# Index DB
INDEX_DB = MEMORY_DIR / "search-index.db"

# What sources to scan: (label, glob_root, glob_pattern)
SOURCES = [
    ("diary", DIARY_DIR, "*.md"),
    ("memory", MEMORY_DIR, "*.md"),  # feedback/project/personal/reference at root
    ("reflection", REFLECTIONS_DIR, "*.md"),
    ("research", RESEARCH_DIR, "*.md"),
]


def get_conn() -> sqlite3.Connection:
    INDEX_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(INDEX_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create FTS5 virtual table + meta table for mtimes."""
    conn.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(
            path UNINDEXED,
            label UNINDEXED,
            mtime UNINDEXED,
            title,
            body,
            tokenize='unicode61 remove_diacritics 2'
        );
        CREATE TABLE IF NOT EXISTS meta (
            path TEXT PRIMARY KEY,
            mtime REAL NOT NULL
        );
    """)
    conn.commit()


def extract_title(text: str, fallback: str) -> str:
    """First H1/H2 in markdown, fallback to filename."""
    for line in text.splitlines()[:20]:
        if line.startswith("# "):
            return line[2:].strip()
        if line.startswith("## "):
            return line[3:].strip()
    return fallback


def reindex(conn: sqlite3.Connection, *, full: bool = False) -> tuple[int, int, int]:
    """Reindex all sources. Returns (added, updated, removed)."""
    init_schema(conn)

    if full:
        conn.execute("DELETE FROM docs")
        conn.execute("DELETE FROM meta")

    # Collect current files
    current_files: dict[Path, tuple[str, float]] = {}
    for label, root, pattern in SOURCES:
        if not root.exists():
            continue
        for f in root.glob(pattern):
            if f.is_file() and f.name != "_TEMPLATE.md":
                current_files[f] = (label, f.stat().st_mtime)

    # Existing in index
    existing = {row["path"]: row["mtime"] for row in conn.execute("SELECT path, mtime FROM meta")}

    added = updated = removed = 0

    # Add or update changed
    for f, (label, mtime) in current_files.items():
        path_str = str(f)
        if path_str in existing and existing[path_str] >= mtime:
            continue  # up-to-date

        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            print(f"skip {f.name}: {e}", file=sys.stderr)
            continue

        title = extract_title(text, f.stem)

        # Remove old entry if exists
        conn.execute("DELETE FROM docs WHERE path = ?", (path_str,))
        conn.execute("DELETE FROM meta WHERE path = ?", (path_str,))

        # Insert
        conn.execute(
            "INSERT INTO docs (path, label, mtime, title, body) VALUES (?, ?, ?, ?, ?)",
            (path_str, label, mtime, title, text),
        )
        conn.execute("INSERT INTO meta (path, mtime) VALUES (?, ?)", (path_str, mtime))

        if path_str in existing:
            updated += 1
        else:
            added += 1

    # Remove gone files
    current_paths = {str(f) for f in current_files}
    for path_str in list(existing):
        if path_str not in current_paths:
            conn.execute("DELETE FROM docs WHERE path = ?", (path_str,))
            conn.execute("DELETE FROM meta WHERE path = ?", (path_str,))
            removed += 1

    conn.commit()
    return added, updated, removed


_FTS_OPS = {"AND", "OR", "NOT", "NEAR"}


def normalize_fts_query(q: str) -> str:
    """Make user input FTS5-safe: quote tokens with dashes/special chars.

    - If user already used quotes/operators — leave as-is
    - Otherwise split by whitespace and quote each token (implicit AND)
    """
    q = q.strip()
    if not q:
        return q
    # Heuristic: if there's already a quote or known FTS op, trust the user
    if '"' in q or any(f" {op} " in f" {q} " for op in _FTS_OPS):
        return q
    tokens = q.split()
    return " ".join(f'"{t}"' for t in tokens)


def search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 10,
    since: str | None = None,
) -> list[sqlite3.Row]:
    """FTS5 search with bm25 ranking."""
    init_schema(conn)

    where_clauses = ["docs MATCH ?"]
    params: list[object] = [normalize_fts_query(query)]

    if since:
        try:
            ts = datetime.fromisoformat(since).timestamp()
            where_clauses.append("mtime >= ?")
            params.append(ts)
        except ValueError:
            print(f"bad --since date: {since} (use YYYY-MM-DD)", file=sys.stderr)
            sys.exit(2)

    sql = f"""
        SELECT path, label, mtime, title,
               snippet(docs, 4, '«', '»', '...', 12) AS snip,
               bm25(docs) AS rank
        FROM docs
        WHERE {' AND '.join(where_clauses)}
        ORDER BY rank
        LIMIT ?
    """
    params.append(limit)
    return list(conn.execute(sql, params))


def fmt_mtime(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def cmd_search(args: argparse.Namespace) -> int:
    conn = get_conn()
    # Auto-reindex on every search (cheap — only changed files re-read)
    added, updated, removed = reindex(conn)
    if added + updated + removed:
        print(f"[index: +{added} ~{updated} -{removed}]", file=sys.stderr)

    rows = search(conn, args.query, limit=args.limit, since=args.since)
    if not rows:
        print("(no matches)")
        return 1

    for i, row in enumerate(rows, 1):
        path = Path(row["path"])
        # Show short path: <label>/<filename>
        short = f"{row['label']}/{path.name}"
        snip = re.sub(r"\s+", " ", row["snip"] or "").strip()
        print(f"\n[{i}] {short}  ({fmt_mtime(row['mtime'])})")
        print(f"    {row['title']}")
        print(f"    {snip}")
        print(f"    → {path}")
    return 0


def cmd_reindex(args: argparse.Namespace) -> int:
    conn = get_conn()
    added, updated, removed = reindex(conn, full=args.full)
    print(f"reindex: +{added} added, ~{updated} updated, -{removed} removed")
    total = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
    print(f"total docs in index: {total}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    conn = get_conn()
    init_schema(conn)
    total = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
    by_label = conn.execute("""
        SELECT label, COUNT(*) AS n FROM docs GROUP BY label ORDER BY n DESC
    """).fetchall()
    db_size = INDEX_DB.stat().st_size if INDEX_DB.exists() else 0

    print(f"index: {INDEX_DB}")
    print(f"size: {db_size / 1024:.1f} KB")
    print(f"total docs: {total}")
    for row in by_label:
        print(f"  {row['label']}: {row['n']}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Session search через SQLite FTS5 поверх Cortex memory.")
    sub = p.add_subparsers(dest="cmd")

    p_search = sub.add_parser("search", help="(default) search query")
    p_search.add_argument("query", help="FTS5 query (поддерживает operators: AND, OR, NOT, NEAR/N, prefix*)")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--since", help="YYYY-MM-DD")

    p_re = sub.add_parser("reindex", help="rebuild index")
    p_re.add_argument("--full", action="store_true", help="drop and rebuild (else incremental)")

    sub.add_parser("stats", help="index stats")

    # Default: if first arg is not a known subcommand, treat as search query
    args_raw = sys.argv[1:]
    if args_raw and args_raw[0] not in {"search", "reindex", "stats", "-h", "--help"}:
        args_raw = ["search", *args_raw]

    args = p.parse_args(args_raw)
    if args.cmd == "search":
        return cmd_search(args)
    if args.cmd == "reindex":
        return cmd_reindex(args)
    if args.cmd == "stats":
        return cmd_stats(args)
    p.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
