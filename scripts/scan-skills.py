#!/usr/bin/env python3
"""Read-only skill curator scan.

Проходит по `.claude/skills/<skill>/SKILL.md`, отчитывает:
  - Stale: ни разу не упоминался в diary/memory за N дней (default 60)
  - Duplicates: похожие триггеры/description у разных skills
  - Broken refs: ссылки на несуществующие файлы внутри skill
  - Missing fields: нет name или description в frontmatter
  - Usage: сколько раз каждый skill упомянут в diary

Без auto-mutation. Только отчёт. Юзер сам решает что архивировать / мерджить.

Usage:
  python scripts/scan-skills.py                  # full report
  python scripts/scan-skills.py --stale-days 30  # custom stale threshold
  python scripts/scan-skills.py --json           # machine-readable
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

CORTEX_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", r"D:\code\2026\2\cortex"))
SKILLS_DIR = CORTEX_DIR / ".claude" / "skills"

USER_DIR = Path.home() / ".claude" / "projects" / "D--code-2026-2-cortex" / "memory"
DIARY_DIR = USER_DIR / "diary"


# --- Parsing ---


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Tiny YAML frontmatter parser. Returns (fields, body)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    fm_block = text[4:end].strip()
    body = text[end + 4 :].lstrip("\n")

    fields: dict[str, str] = {}
    for line in fm_block.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        val = val.strip()
        # Strip optional surrounding quotes
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        fields[key.strip()] = val
    return fields, body


def load_skills() -> dict[str, dict]:
    """Read all skills. Returns {name: {fields, body, path, mtime}}."""
    skills: dict[str, dict] = {}
    if not SKILLS_DIR.exists():
        return skills
    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fields, body = parse_frontmatter(text)
        skills[skill_dir.name] = {
            "fields": fields,
            "body": body,
            "path": skill_md,
            "mtime": skill_md.stat().st_mtime,
            "size": len(text),
        }
    return skills


# --- Checks ---


def usage_in_diary(skills: dict[str, dict]) -> dict[str, list[str]]:
    """For each skill, list diary files that mention it."""
    usage: dict[str, list[str]] = defaultdict(list)
    if not DIARY_DIR.exists():
        return usage
    for diary_md in sorted(DIARY_DIR.glob("*.md")):
        try:
            text = diary_md.read_text(encoding="utf-8").lower()
        except (OSError, UnicodeDecodeError):
            continue
        for skill_name in skills:
            # Match the skill name as a whole-ish word
            if re.search(rf"\b{re.escape(skill_name.lower())}\b", text):
                usage[skill_name].append(diary_md.name)
    return usage


def find_stale(skills: dict[str, dict], usage: dict, days: int) -> list[str]:
    """Skills not mentioned in last N days of diary AND not modified recently."""
    cutoff_ts = (datetime.now() - timedelta(days=days)).timestamp()
    cutoff_str = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    stale = []
    for name, info in skills.items():
        # Recent diary mention?
        recent_mention = any(
            d.split("_")[-1].rstrip(".md") >= cutoff_str
            for d in usage.get(name, [])
            if "_" in d
        )
        if recent_mention:
            continue
        # Recent skill file edit?
        if info["mtime"] >= cutoff_ts:
            continue
        stale.append(name)
    return stale


def find_duplicates(skills: dict[str, dict]) -> list[tuple[str, str, str]]:
    """Find skills with overlapping description keywords. Returns (skill1, skill2, reason)."""
    dupes = []
    descs = {n: info["fields"].get("description", "").lower() for n, info in skills.items()}

    # Strategy: shared significant tokens (3+ chars, non-stopword)
    stopwords = {
        "for", "the", "and", "use", "this", "that", "with", "from", "when", "skill",
        "пользователь", "это", "для", "при", "когда", "тоже", "если", "также",
    }

    def tokens(s: str) -> set[str]:
        return {t for t in re.findall(r"[a-zа-я]{3,}", s) if t not in stopwords}

    names = list(skills)
    for i, n1 in enumerate(names):
        for n2 in names[i + 1 :]:
            t1, t2 = tokens(descs[n1]), tokens(descs[n2])
            if not t1 or not t2:
                continue
            shared = t1 & t2
            jaccard = len(shared) / len(t1 | t2)
            if jaccard >= 0.4:
                dupes.append((n1, n2, f"jaccard={jaccard:.2f}, shared={sorted(shared)[:5]}"))
    return dupes


def find_broken_refs(skills: dict[str, dict]) -> dict[str, list[str]]:
    """Find references like `path/to/file` or `[text](path)` that don't exist."""
    broken: dict[str, list[str]] = defaultdict(list)
    # Pattern: markdown link with relative-looking path
    md_link = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    # Pattern: inline path-like in backticks
    inline = re.compile(r"`([./\w][\w./-]+\.\w+)`")

    for name, info in skills.items():
        skill_dir = info["path"].parent
        body = info["body"]
        candidates: set[str] = set()
        for m in md_link.finditer(body):
            url = m.group(1).split("#")[0].strip()
            if url.startswith(("http://", "https://", "mailto:", "#")):
                continue
            candidates.add(url)
        for m in inline.finditer(body):
            candidates.add(m.group(1))

        for c in candidates:
            # Try resolving relative to skill dir, then to repo root
            local = (skill_dir / c).resolve()
            repo = (CORTEX_DIR / c).resolve()
            if local.exists() or repo.exists():
                continue
            # Skip obvious URL-fragment artefacts
            if c.startswith("$") or c.startswith("<") or " " in c:
                continue
            # Skip placeholders (xxx, foo.bar, etc)
            if "xxx" in c.lower() or c.startswith("foo."):
                continue
            # Skip CamelCase.CONST patterns (Python attribute access, not file paths)
            if re.match(r"^[A-Z][a-zA-Z]+\.[A-Z]", c):
                continue
            # Skip module.attribute pattern (e.g. operator.add) — no slash, no file ext
            if "/" not in c and "\\" not in c:
                ext = c.rsplit(".", 1)[-1] if "." in c else ""
                # Likely a code reference, not a path
                if ext and not re.match(r"^[a-z]{2,5}$", ext):
                    continue
            broken[name].append(c)
    return broken


def find_missing_fields(skills: dict[str, dict]) -> dict[str, list[str]]:
    """Skills missing name/description in frontmatter."""
    issues: dict[str, list[str]] = defaultdict(list)
    for name, info in skills.items():
        fields = info["fields"]
        if not fields.get("name"):
            issues[name].append("no name")
        if not fields.get("description"):
            issues[name].append("no description")
        elif len(fields["description"]) < 20:
            issues[name].append(f"description too short ({len(fields['description'])} chars)")
    return issues


# --- Output ---


def render_text(report: dict, *, stale_days: int) -> str:
    out = []
    skills = report["skills"]
    out.append(f"# Skill scan — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    out.append(f"Skills directory: {SKILLS_DIR}")
    out.append(f"Total skills: {len(skills)}")
    out.append("")

    # Usage table
    out.append("## Usage в diary")
    out.append("")
    if not report["usage"]:
        out.append("(нет diary в `~/.claude/projects/.../memory/diary/`)")
    else:
        for name in sorted(skills, key=lambda n: -len(report["usage"].get(n, []))):
            count = len(report["usage"].get(name, []))
            marker = "🔥" if count >= 5 else ("✓" if count > 0 else "·")
            out.append(f"  {marker} {name}: {count} mentions")
    out.append("")

    # Stale
    out.append(f"## Stale (не упомянуты {stale_days}+ дней, не модифицированы {stale_days}+ дней)")
    out.append("")
    if report["stale"]:
        for name in report["stale"]:
            mtime = datetime.fromtimestamp(skills[name]["mtime"]).strftime("%Y-%m-%d")
            out.append(f"  ⚠️  {name} (last edit: {mtime})")
    else:
        out.append("  (нет stale skills)")
    out.append("")

    # Duplicates
    out.append("## Возможные дубликаты (по description)")
    out.append("")
    if report["duplicates"]:
        for n1, n2, why in report["duplicates"]:
            out.append(f"  ⚠️  {n1} ↔ {n2}  ({why})")
    else:
        out.append("  (нет явных дубликатов)")
    out.append("")

    # Broken refs
    out.append("## Broken refs внутри skills")
    out.append("")
    if report["broken_refs"]:
        for name, refs in report["broken_refs"].items():
            out.append(f"  {name}:")
            for r in refs:
                out.append(f"    ✗ {r}")
    else:
        out.append("  (нет broken refs)")
    out.append("")

    # Missing fields
    out.append("## Missing frontmatter fields")
    out.append("")
    if report["missing_fields"]:
        for name, issues in report["missing_fields"].items():
            out.append(f"  {name}: {', '.join(issues)}")
    else:
        out.append("  (frontmatter везде ок)")
    out.append("")

    out.append("---")
    out.append("Это read-only отчёт. Никаких авто-правок не делается.")
    out.append("Решение что архивировать / мерджить — за тобой.")
    return "\n".join(out)


def main() -> int:
    p = argparse.ArgumentParser(description="Read-only skill curator scan.")
    p.add_argument("--stale-days", type=int, default=60, help="threshold for stale (default 60)")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args()

    skills = load_skills()
    if not skills:
        print(f"no skills found in {SKILLS_DIR}", file=sys.stderr)
        return 1

    usage = usage_in_diary(skills)
    stale = find_stale(skills, usage, args.stale_days)
    duplicates = find_duplicates(skills)
    broken_refs = find_broken_refs(skills)
    missing_fields = find_missing_fields(skills)

    report = {
        "skills": skills,
        "usage": dict(usage),
        "stale": stale,
        "duplicates": duplicates,
        "broken_refs": dict(broken_refs),
        "missing_fields": dict(missing_fields),
    }

    if args.json:
        # Strip non-serializable fields
        out = {
            "total": len(skills),
            "usage": {k: len(v) for k, v in usage.items()},
            "stale": stale,
            "duplicates": [{"a": a, "b": b, "reason": r} for a, b, r in duplicates],
            "broken_refs": dict(broken_refs),
            "missing_fields": dict(missing_fields),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(render_text(report, stale_days=args.stale_days))
    return 0


if __name__ == "__main__":
    sys.exit(main())
