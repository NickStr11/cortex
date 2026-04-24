#!/usr/bin/env bash
# Restore BGM tracks for huashu-design skill (video/animation export).
# Tracks are gitignored (27MB total), fetch on demand.
set -euo pipefail

TARGET="$(cd "$(dirname "$0")/.." && pwd)/.claude/skills/huashu-design/assets"
REPO="https://raw.githubusercontent.com/alchaincyf/huashu-design/main/assets"

if [ ! -d "$TARGET" ]; then
    echo "huashu-design skill not found. Clone first:"
    echo "  cd .claude/skills && git clone --depth 1 https://github.com/alchaincyf/huashu-design.git"
    exit 1
fi

TRACKS=(
    "bgm-ad.mp3"
    "bgm-educational-alt.mp3"
    "bgm-educational.mp3"
    "bgm-tech.mp3"
    "bgm-tutorial-alt.mp3"
    "bgm-tutorial.mp3"
)

for track in "${TRACKS[@]}"; do
    if [ -f "$TARGET/$track" ]; then
        echo "skip  $track (exists)"
        continue
    fi
    echo "fetch $track"
    curl -fsSL "$REPO/$track" -o "$TARGET/$track"
done

echo "Done. $(ls -1 "$TARGET"/bgm-*.mp3 2>/dev/null | wc -l) tracks in $TARGET"
