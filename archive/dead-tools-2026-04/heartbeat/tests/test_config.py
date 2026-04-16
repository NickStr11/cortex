from __future__ import annotations

from beartype import beartype

from config import ALL_KEYWORDS, TOPICS


@beartype
def test_topics_structure() -> None:
    assert isinstance(TOPICS, dict)
    assert len(TOPICS) > 0
    for category, keywords in TOPICS.items():
        assert isinstance(category, str)
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        for kw in keywords:
            assert isinstance(kw, str)


@beartype
def test_all_keywords() -> None:
    assert isinstance(ALL_KEYWORDS, list)
    expected_count = sum(len(keywords) for keywords in TOPICS.values())
    assert len(ALL_KEYWORDS) == expected_count
    for kw in ALL_KEYWORDS:
        assert any(kw in keywords for keywords in TOPICS.values())
