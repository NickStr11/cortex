#!/usr/bin/env python3
"""Cortex Heartbeat — AI/Tech trend scanner.

Usage:
    uv run python main.py --mode fetch     # Raw data (for /heartbeat slash command)
    uv run python main.py --mode digest    # Fetch + Anthropic analysis (for GitHub Action)
"""
from __future__ import annotations

import argparse
import io
import sys

from beartype import beartype

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


@beartype
def cmd_fetch() -> None:
    from formatter import format_raw_digest
    from sources import fetch_all

    print("Fetching trends...", file=sys.stderr)
    data = fetch_all()
    raw_md = format_raw_digest(data["hn"], data["github"])  # type: ignore[arg-type]
    print(raw_md)


@beartype
def cmd_digest() -> None:
    from analyzer import analyze_with_claude
    from formatter import format_raw_digest
    from sources import fetch_all

    print("Fetching trends...", file=sys.stderr)
    data = fetch_all()
    raw_md = format_raw_digest(data["hn"], data["github"])  # type: ignore[arg-type]

    print("Analyzing with Claude...", file=sys.stderr)
    digest = analyze_with_claude(raw_md)
    print(digest)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cortex Heartbeat")
    parser.add_argument(
        "--mode",
        choices=["fetch", "digest"],
        default="fetch",
        help="fetch = raw data, digest = fetch + AI analysis",
    )
    args = parser.parse_args()

    if args.mode == "fetch":
        cmd_fetch()
    else:
        cmd_digest()


if __name__ == "__main__":
    main()
