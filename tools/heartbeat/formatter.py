from __future__ import annotations

from datetime import datetime, timezone

from beartype import beartype

from sources import GitHubRepo, HNStory


@beartype
def format_raw_digest(
    hn_stories: list[HNStory],
    github_repos: list[GitHubRepo],
) -> str:
    lines: list[str] = [
        f"# Heartbeat Raw Data — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "",
        f"## Hacker News Top Stories ({len(hn_stories)} relevant)",
        "",
    ]

    for i, story in enumerate(hn_stories, 1):
        lines.append(
            f"{i}. **{story.title}** "
            f"(score: {story.score}, comments: {story.comments})"
        )
        lines.append(f"   {story.url}")
        lines.append("")

    lines.extend([
        f"## GitHub Trending Repos ({len(github_repos)} found)",
        "",
    ])

    for i, repo in enumerate(github_repos, 1):
        lang = f" [{repo.language}]" if repo.language else ""
        lines.append(f"{i}. **{repo.full_name}**{lang} ({repo.stars} stars)")
        if repo.description:
            lines.append(f"   {repo.description}")
        lines.append(f"   {repo.url}")
        if repo.topics:
            lines.append(f"   Topics: {', '.join(repo.topics[:5])}")
        lines.append("")

    lines.extend([
        "---",
        f"Fetched: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
    ])

    return "\n".join(lines)
