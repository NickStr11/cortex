from __future__ import annotations

from unittest.mock import MagicMock, patch

from beartype import beartype

from sources import (
    GitHubRepo,
    HNStory,
    ProductHuntLaunch,
    RedditPost,
    _http_get,
    _http_get_json,
    _matches_keywords,
    fetch_all,
    fetch_github_trending,
    fetch_hn_stories,
    fetch_product_hunt_launches,
    fetch_reddit_posts,
)


@beartype
def test_matches_keywords() -> None:
    assert _matches_keywords("This is about AI agent") is True
    assert _matches_keywords("Something about Python") is True
    assert _matches_keywords("Totally unrelated topic") is False


@beartype
@patch("sources._http_get_json")
def test_fetch_reddit_posts(mock_get: MagicMock) -> None:
    mock_get.return_value = {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "Test Post",
                        "permalink": "/r/test/comments/123/",
                        "score": 100,
                        "num_comments": 10,
                        "author": "user1",
                        "subreddit": "MachineLearning",
                        "created_utc": 1672531200,
                    }
                }
            ]
        }
    }

    posts = fetch_reddit_posts()
    assert len(posts) == 1
    assert isinstance(posts[0], RedditPost)
    assert posts[0].title == "Test Post"
    assert posts[0].score == 100
    assert posts[0].subreddit == "MachineLearning"


@beartype
@patch("sources._http_get_json")
def test_fetch_hn_stories(mock_get: MagicMock) -> None:
    # First call for top stories IDs
    # Second call for the item itself
    def side_effect(url: str) -> list[int] | dict[str, MagicMock]:
        if "topstories.json" in url:
            return [1, 2]
        if "item/1.json" in url:
            return {
                "id": 1,
                "type": "story",
                "title": "AI Agent is here",
                "url": "http://example.com/ai",
                "score": 50,
                "descendants": 5,
                "by": "author1",
                "time": 1672531200,
            }
        if "item/2.json" in url:
            return {
                "id": 2,
                "type": "story",
                "title": "Unrelated",
                "score": 10,
                "by": "author2",
                "time": 1672531200,
            }
        return {}

    mock_get.side_effect = side_effect

    stories = fetch_hn_stories()
    # Only 1 story matches keywords
    assert len(stories) == 1
    assert isinstance(stories[0], HNStory)
    assert stories[0].title == "AI Agent is here"


@beartype
@patch("sources._http_get_json")
def test_fetch_github_trending(mock_get: MagicMock) -> None:
    mock_get.return_value = {
        "items": [
            {
                "name": "cortex",
                "full_name": "org/cortex",
                "description": "AI agent framework",
                "html_url": "http://github.com/org/cortex",
                "stargazers_count": 1000,
                "language": "Python",
                "topics": ["ai", "agents"],
                "created_at": "2023-01-01T00:00:00Z",
            }
        ]
    }

    repos = fetch_github_trending()
    assert len(repos) >= 1  # Might be more because of multiple GITHUB_TOPICS
    assert isinstance(repos[0], GitHubRepo)
    assert repos[0].name == "cortex"
    assert repos[0].stars == 1000


@beartype
@patch("sources._http_get_json")
def test_fetch_reddit_posts_error(mock_get: MagicMock) -> None:
    mock_get.side_effect = Exception("API error")
    posts = fetch_reddit_posts()
    assert posts == []


@beartype
@patch("sources._http_get")
def test_fetch_product_hunt_launches(mock_get: MagicMock) -> None:
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>AI Agent Tool</title>
    <link rel="alternate" href="https://example.com/ai-agent"/>
    <content type="html">&lt;p&gt;A cool AI agent for coding&lt;/p&gt;</content>
    <author><name>John Doe</name></author>
    <published>2026-02-25T12:00:00Z</published>
  </entry>
  <entry>
    <title>Unrelated Product</title>
    <link rel="alternate" href="https://example.com/unrelated"/>
    <content type="html">&lt;p&gt;Nothing to do with AI&lt;/p&gt;</content>
    <author><name>Jane Doe</name></author>
    <published>2026-02-25T13:00:00Z</published>
  </entry>
</feed>
"""
    mock_get.return_value = xml_content.encode()

    launches = fetch_product_hunt_launches()
    # Only 1 launch matches keywords (AI agent)
    assert len(launches) == 1
    assert isinstance(launches[0], ProductHuntLaunch)
    assert launches[0].title == "AI Agent Tool"
    assert launches[0].author == "John Doe"


@beartype
@patch("sources._http_get")
def test_fetch_product_hunt_launches_error(mock_get: MagicMock) -> None:
    mock_get.side_effect = Exception("PH error")
    launches = fetch_product_hunt_launches()
    assert launches == []


@beartype
@patch("sources._http_get_json")
@patch("sources.fetch_product_hunt_launches")
def test_fetch_all(mock_ph: MagicMock, mock_get: MagicMock) -> None:
    mock_get.return_value = {}
    mock_ph.return_value = []
    res = fetch_all()
    assert "hn" in res
    assert "github" in res
    assert "reddit" in res
    assert "ph" in res
    assert "x" in res


@beartype
@patch("urllib.request.urlopen")
def test_http_get(mock_urlopen: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.read.return_value = b"raw data"
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    result = _http_get("http://example.com")
    assert result == b"raw data"


@beartype
@patch("sources._http_get")
def test_http_get_json(mock_get: MagicMock) -> None:
    mock_get.return_value = b'{"key": "value"}'
    result = _http_get_json("http://example.com")
    assert result == {"key": "value"}
