from __future__ import annotations

from datetime import datetime, timezone

from beartype import beartype

from formatter import format_raw_digest
from sources import GitHubRepo, HNStory, ProductHuntLaunch, RedditPost, XTrend


@beartype
def test_format_raw_digest() -> None:
    hn_stories = [
        HNStory(
            id=1,
            title="HN Story",
            url="http://hn.com",
            score=100,
            comments=10,
            author="auth",
            time=datetime.now(timezone.utc),
        )
    ]
    github_repos = [
        GitHubRepo(
            name="repo",
            full_name="org/repo",
            description="desc",
            url="http://github.com/repo",
            stars=500,
            language="Python",
            topics=["topic"],
            created_at="2023-01-01",
        )
    ]
    reddit_posts = [
        RedditPost(
            title="Reddit Post",
            url="http://reddit.com/post",
            score=200,
            comments=20,
            author="user",
            subreddit="sub",
            created_at=datetime.now(timezone.utc),
        )
    ]
    x_trends = [
        XTrend(name="Trend", url="http://x.com/trend", volume=1000)
    ]
    ph_launches = [
        ProductHuntLaunch(
            title="PH Launch",
            description="desc",
            url="http://ph.com",
            votes=100,
            comments=10,
            author="author",
            published_at=datetime.now(timezone.utc),
        )
    ]

    digest = format_raw_digest(
        hn_stories, github_repos, reddit_posts, ph_launches, x_trends
    )

    assert "Heartbeat Raw Data" in digest
    assert "Hacker News Top Stories (1 relevant)" in digest
    assert "HN Story" in digest
    assert "GitHub Trending Repos (1 found)" in digest
    assert "org/repo" in digest
    assert "Reddit Top Posts (1 found)" in digest
    assert "Reddit Post" in digest
    assert "Product Hunt Top Launches (1 found)" in digest
    assert "PH Launch" in digest
    assert "X Trending Topics (1 found)" in digest
    assert "Trend" in digest
