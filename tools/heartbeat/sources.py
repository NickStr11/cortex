from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from beartype import beartype

from config import (
    ALL_KEYWORDS,
    GITHUB_LOOKBACK_DAYS,
    GITHUB_MIN_STARS,
    GITHUB_RESULTS_LIMIT,
    GITHUB_SEARCH_API,
    GITHUB_TOPICS,
    HN_API_BASE,
    HN_FETCH_WORKERS,
    HN_RESULTS_LIMIT,
    HN_TOP_STORIES_LIMIT,
    PH_FEED_URL,
    PH_RESULTS_LIMIT,
    REDDIT_RESULTS_LIMIT,
    REDDIT_SUBREDDITS,
    X_RESULTS_LIMIT,
)


@dataclass
class HNStory:
    id: int
    title: str
    url: str
    score: int
    comments: int
    author: str
    time: datetime


@dataclass
class GitHubRepo:
    name: str
    full_name: str
    description: str
    url: str
    stars: int
    language: str | None
    topics: list[str]
    created_at: str


@dataclass
class RedditPost:
    title: str
    url: str
    score: int
    comments: int
    author: str
    subreddit: str
    created_at: datetime


@dataclass
class XTrend:
    name: str
    url: str
    volume: int | None


@dataclass
class ProductHuntLaunch:
    title: str
    description: str
    url: str
    votes: int
    comments: int
    author: str
    published_at: datetime


@beartype
def fetch_reddit_posts() -> list[RedditPost]:
    subreddits = "+".join(REDDIT_SUBREDDITS)
    url = f"https://www.reddit.com/r/{subreddits}/top.json?t=week&limit={REDDIT_RESULTS_LIMIT}"

    try:
        data = _http_get_json(url)
    except Exception:
        return []

    if not isinstance(data, dict):
        return []

    posts: list[RedditPost] = []
    children = data.get("data", {}).get("children", [])

    for child in children:
        item = child.get("data", {})
        if not item:
            continue

        posts.append(RedditPost(
            title=item.get("title", ""),
            url=f"https://reddit.com{item.get('permalink', '')}",
            score=item.get("score", 0),
            comments=item.get("num_comments", 0),
            author=item.get("author", "unknown"),
            subreddit=item.get("subreddit", "unknown"),
            created_at=datetime.fromtimestamp(
                item.get("created_utc", 0), tz=timezone.utc
            ),
        ))

    return posts


@beartype
def fetch_x_trends() -> list[XTrend]:
    """Fetch trending topics from X.

    Currently a placeholder as the free API is limited.
    TODO: Implement once a reliable free source is found.
    """
    return []


@beartype
def _http_get(url: str) -> bytes:
    # Reddit and other APIs often block default Python/urllib User-Agents.
    # Using a common browser-like User-Agent to ensure better compatibility.
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


@beartype
def _http_get_json(url: str) -> dict | list:  # type: ignore[type-arg]
    return json.loads(_http_get(url).decode())


@beartype
def _matches_keywords(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in ALL_KEYWORDS)


@beartype
def _fetch_hn_item(story_id: int) -> HNStory | None:
    try:
        item = _http_get_json(f"{HN_API_BASE}/item/{story_id}.json")
    except Exception:
        return None

    if not isinstance(item, dict) or item.get("type") != "story":
        return None

    title = item.get("title", "")
    if not _matches_keywords(title):
        return None

    return HNStory(
        id=item["id"],
        title=title,
        url=item.get("url", f"https://news.ycombinator.com/item?id={item['id']}"),
        score=item.get("score", 0),
        comments=item.get("descendants", 0),
        author=item.get("by", "unknown"),
        time=datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc),
    )


@beartype
def fetch_hn_stories() -> list[HNStory]:
    raw_ids = _http_get_json(f"{HN_API_BASE}/topstories.json")
    if not isinstance(raw_ids, list):
        return []
    story_ids: list[int] = raw_ids[:HN_TOP_STORIES_LIMIT]

    stories: list[HNStory] = []
    with ThreadPoolExecutor(max_workers=HN_FETCH_WORKERS) as pool:
        futures = {pool.submit(_fetch_hn_item, sid): sid for sid in story_ids}
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                stories.append(result)

    stories.sort(key=lambda s: s.score, reverse=True)
    return stories[:HN_RESULTS_LIMIT]


@beartype
def fetch_product_hunt_launches() -> list[ProductHuntLaunch]:
    try:
        content = _http_get(PH_FEED_URL).decode()
        root = ET.fromstring(content)
    except Exception:
        return []

    # Atom namespace
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    launches: list[ProductHuntLaunch] = []

    for entry in root.findall("atom:entry", ns):
        title = entry.findtext("atom:title", "", ns)
        link_elem = entry.find("atom:link[@rel='alternate']", ns)
        url = link_elem.get("href", "") if link_elem is not None else ""

        content_html = entry.findtext("atom:content", "", ns)
        # Extract description from the first <p>
        desc_match = re.search(r"<p>(.*?)</p>", content_html, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else ""

        author_elem = entry.find("atom:author/atom:name", ns)
        author = author_elem.text if author_elem is not None else "unknown"

        published_str = entry.findtext("atom:published", "", ns)
        try:
            # Format: 2026-02-24T14:37:19-08:00
            # Python's fromisoformat handles this in 3.11+
            published_at = datetime.fromisoformat(published_str)
        except Exception:
            published_at = datetime.now(timezone.utc)

        if _matches_keywords(title) or _matches_keywords(description):
            launches.append(ProductHuntLaunch(
                title=title,
                description=description,
                url=url,
                votes=0,  # RSS doesn't provide votes
                comments=0,
                author=author,
                published_at=published_at,
            ))

    return launches[:PH_RESULTS_LIMIT]


@beartype
def fetch_github_trending() -> list[GitHubRepo]:
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=GITHUB_LOOKBACK_DAYS)
    ).strftime("%Y-%m-%d")

    repos: list[GitHubRepo] = []
    seen: set[str] = set()

    for topic in GITHUB_TOPICS:
        query = f"topic:{topic} created:>{cutoff} stars:>{GITHUB_MIN_STARS}"
        url = (
            f"{GITHUB_SEARCH_API}"
            f"?q={urllib.parse.quote(query)}"
            f"&sort=stars&order=desc&per_page=10"
        )
        try:
            data = _http_get_json(url)
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        for item in data.get("items", []):
            full_name = item["full_name"]
            if full_name in seen:
                continue
            seen.add(full_name)
            repos.append(GitHubRepo(
                name=item["name"],
                full_name=full_name,
                description=item.get("description", "") or "",
                url=item["html_url"],
                stars=item["stargazers_count"],
                language=item.get("language"),
                topics=item.get("topics", []),
                created_at=item.get("created_at", ""),
            ))

    repos.sort(key=lambda r: r.stars, reverse=True)
    return repos[:GITHUB_RESULTS_LIMIT]


@beartype
def fetch_all() -> dict[str, (
    list[HNStory] | list[GitHubRepo] | list[RedditPost] | list[XTrend] | list[ProductHuntLaunch]
)]:
    return {
        "hn": fetch_hn_stories(),
        "github": fetch_github_trending(),
        "reddit": fetch_reddit_posts(),
        "ph": fetch_product_hunt_launches(),
        "x": fetch_x_trends(),
    }
