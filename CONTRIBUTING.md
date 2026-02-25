# Contributing to Cortex

First off, thank you for considering contributing to Cortex! It's people like you that make Cortex such a great tool.

## 🚀 How It Works: The AI-Corporation Workflow

Cortex is not just a repository; it's an AI-orchestrated corporation. We follow a unique workflow:

1.  **Council Planning**: We use the `/council` command to analyze the project status and generate strategic tasks.
2.  **Dispatching**: Tasks are converted into GitHub Issues using the `/dispatch` command.
3.  **Agent Execution**: Specialized AI agents like **Jules** or **Codex** pick up these issues based on labels (`jules` or `codex`), implement solutions, and create Pull Requests.
4.  **Human Review**: As the CEO of your instance, you (or the maintainers) review the PRs, run `/verify`, and merge them.

## 🛠 Getting Started

### Prerequisites

- [Python 3.12+](https://www.python.org/downloads/)
- [uv](https://github.com/astral-sh/uv) (Fast Python package installer and resolver)
- [Claude Code](https://claude.ai/code) (The primary orchestration interface)

### Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/cortex.git
    cd cortex
    ```
2.  **Install dependencies**:
    Cortex uses a modular structure. Dependencies are managed per tool:
    ```bash
    cd tools/heartbeat && uv sync
    cd ../metrics && uv sync
    ```
3.  **Initialize Claude Code**:
    Launch `claude` in the project root to access custom slash commands.

## 📜 Code Style & Rules

To maintain high quality and agent compatibility, we enforce strict rules:

### Python Rules
- **Modern Syntax**: Use `from __future__ import annotations`.
- **Type Safety**: Strict type hinting is mandatory. Use `list[str]` instead of `List[str]` and `X | None` instead of `Optional[X]`.
- **Runtime Checking**: All public functions must be decorated with `@beartype`.
- **Complexity**:
    - Maximum **700 lines** per file.
    - Maximum **70 lines** per function.
    - Maximum **4 levels** of nesting.
- **Tools**: Use `uv run pyright` for type checking and `uv run pytest` for testing within tool directories.

See [docs/python-rules.md](docs/python-rules.md) for more details.

### Git Workflow
- **Conventional Commits**: We use the `<type>(<scope>): <description>` format (e.g., `feat(heartbeat): add Reddit source`).
- **Branching**: Never commit directly to `main`. Create a feature branch (`feat/your-feature`) and submit a PR.

See [docs/git-flow.md](docs/git-flow.md) for more details.

### Verification
Before submitting a PR, ensure your changes pass the verification suite:
```bash
/verify
```
Or manually run the steps outlined in [docs/verify.md](docs/verify.md).

## 🤝 Community

If you have questions or want to discuss ideas, feel free to open an Issue or start a Discussion!

---

*Cortex — Your Personal AI-Corporation*
