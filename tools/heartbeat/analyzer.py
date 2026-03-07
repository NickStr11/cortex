from __future__ import annotations

from beartype import beartype

from config import ANTHROPIC_MAX_TOKENS, ANTHROPIC_MODEL, PROJECT_ROOT

ANALYSIS_PROMPT = """\
You are a technology strategist for a personal AI corporation project.

Given:
1. Raw trend data from Hacker News, GitHub Trending, Reddit, Product Hunt, and X
2. The project context (goals, stack, current status)

Produce a concise Heartbeat digest in this format:

### HN Ссылки
CRITICAL: Every single HN link MUST have a Russian description after "—". No exceptions. Do NOT output bare links without descriptions.

Format (follow EXACTLY):
1. [Original Title](url) — описание на русском что это и почему интересно
2. [Original Title](url) — описание на русском что это и почему интересно

Include ALL HN stories from raw data, not just relevant ones. If you skip the Russian description for even one link, the output is invalid.

### Relevant Trends
1. **[Trend Name]** — [1-sentence why it matters] ([link])
   - Actionable: [concrete task for an AI agent]

(5-10 most relevant trends from ALL sources)

### Recommended Actions
- [ ] [Task description for /dispatch] (agent: Jules/Codex, size: S/M/L)

(3-5 concrete tasks)

### Stats
- HN stories analyzed: X
- GitHub repos analyzed: Y
- Reddit posts analyzed: Z
- Product Hunt launches analyzed: P
- X trends analyzed: W

Rules:
- The "HN Ссылки" section MUST come first, with Russian descriptions for every HN link
- Focus trends on what's relevant to PROJECT_CONTEXT (AI agents, orchestration, Python, automation)
- Every recommendation must be specific enough to become a GitHub Issue
- Be concise, no filler
"""


@beartype
def read_project_context() -> str:
    context_path = PROJECT_ROOT / "PROJECT_CONTEXT.md"
    if context_path.exists():
        return context_path.read_text(encoding="utf-8")
    return "(PROJECT_CONTEXT.md not found)"


@beartype
def analyze_with_claude(raw_data: str) -> str:
    import anthropic

    project_context = read_project_context()

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=ANTHROPIC_MAX_TOKENS,
        messages=[{
            "role": "user",
            "content": (
                f"{ANALYSIS_PROMPT}\n\n"
                f"## PROJECT_CONTEXT.md\n{project_context}\n\n"
                f"## Raw Trend Data\n{raw_data}"
            ),
        }],
    )

    return message.content[0].text  # type: ignore[union-attr]
