"""CLI wrapper to rebuild the steam-sniper listings snapshot database."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from listings_snapshot import SNAPSHOT_DB_PATH, build_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=SNAPSHOT_DB_PATH,
        help="Path to listings_snapshot.db",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=2000,
        help="SQLite insert batch size",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    result = build_snapshot(args.output, batch_size=args.batch_size)
    elapsed = time.perf_counter() - started
    size_mb = result["size_bytes"] / (1024 * 1024)
    print(
        f"snapshot ready: {result['rows']} rows -> {result['path']} "
        f"({size_mb:.1f} MB) in {elapsed:.1f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
