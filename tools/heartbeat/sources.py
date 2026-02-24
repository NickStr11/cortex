from __future__ import annotations

import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

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


@beartype
def _http_get_json(url: str) -> dict | list:  # type: ignore[type-arg]
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "cortex-heartbeat/0.1"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


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
def fetch_all() -> dict[str, list[HNStory] | list[GitHubRepo]]:
    return {
        "hn": fetch_hn_stories(),
        "github": fetch_github_trending(),
    }
