from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Topics to track — keywords grouped by category
TOPICS: dict[str, list[str]] = {
    "ai_agents": [
        "ai agent", "autonomous agent", "agentic",
        "crew ai", "autogen", "langchain", "langgraph",
    ],
    "llm": [
        "llm", "large language model",
        "gpt", "claude", "gemini", "anthropic", "openai",
    ],
    "coding_ai": [
        "copilot", "codex", "cursor", "aider",
        "claude code", "devin", "jules",
    ],
    "dev_tools": [
        "github actions", "ci/cd", "developer tools", "devops",
    ],
    "python": [
        "python", "fastapi", "django", "uv package", "ruff",
    ],
    "automation": [
        "automation", "workflow", "orchestration", "n8n", "zapier",
    ],
}

ALL_KEYWORDS: list[str] = [kw for keywords in TOPICS.values() for kw in keywords]

# Hacker News
HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
HN_TOP_STORIES_LIMIT = 100
HN_RESULTS_LIMIT = 20
HN_FETCH_WORKERS = 10

# GitHub
GITHUB_SEARCH_API = "https://api.github.com/search/repositories"
GITHUB_TOPICS = ["ai", "llm", "agents", "automation", "python"]
GITHUB_MIN_STARS = 5
GITHUB_LOOKBACK_DAYS = 3
GITHUB_RESULTS_LIMIT = 15

# Reddit
REDDIT_SUBREDDITS = ["MachineLearning", "artificial", "LocalLLaMA", "ChatGPT"]
REDDIT_RESULTS_LIMIT = 20

# X (Twitter)
X_RESULTS_LIMIT = 10

# Anthropic (digest mode only)
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_MAX_TOKENS = 4096
