from __future__ import annotations

from datetime import datetime, timezone

from beartype import beartype

from sources import GitHubRepo, HNStory, ProductHuntLaunch, RedditPost, XTrend


@beartype
def format_raw_digest(
    hn_stories: list[HNStory],
    github_repos: list[GitHubRepo],
    reddit_posts: list[RedditPost],
    ph_launches: list[ProductHuntLaunch],
    x_trends: list[XTrend],
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
        f"## Reddit Top Posts ({len(reddit_posts)} found)",
        "",
    ])

    for i, post in enumerate(reddit_posts, 1):
        lines.append(
            f"{i}. **{post.title}** "
            f"(score: {post.score}, comments: {post.comments}, r/{post.subreddit})"
        )
        lines.append(f"   {post.url}")
        lines.append("")

    lines.extend([
        f"## Product Hunt Top Launches ({len(ph_launches)} found)",
        "",
    ])

    for i, launch in enumerate(ph_launches, 1):
        lines.append(f"{i}. **{launch.title}** (by {launch.author})")
        if launch.description:
            lines.append(f"   {launch.description}")
        lines.append(f"   {launch.url}")
        lines.append("")

    if x_trends:
        lines.extend([
            f"## X Trending Topics ({len(x_trends)} found)",
            "",
        ])
        for i, trend in enumerate(x_trends, 1):
            volume = f" ({trend.volume} posts)" if trend.volume else ""
            lines.append(f"{i}. **{trend.name}**{volume}")
            lines.append(f"   {trend.url}")
            lines.append("")

    lines.extend([
        "---",
        f"Fetched: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
    ])

    return "\n".join(lines)
