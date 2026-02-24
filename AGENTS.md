# Cortex — AI Orchestration System

## Project Overview

Cortex is a personal AI corporation system. It orchestrates AI agents (Jules, Codex, Claude) via GitHub Issues. The human acts as CEO — sets goals, reviews PRs, merges. Agents do the actual work.

## Architecture

```
/council (Claude CLI) → generates tasks by role (CPO/CTO/CMO/Growth)
/dispatch (Claude CLI) → creates GitHub Issues with agent labels
GitHub Issues          → queue of tasks for agents
Jules / Codex          → pick up tasks, write code, create PRs
Human                  → reviews PRs, merges
```

## Tech Stack

- Language: Python 3.12+
- Package manager: uv
- Type checking: pyright (strict)
- Runtime types: beartype
- CLI: Claude Code (slash commands in .claude/commands/)
- Agents: Jules (Google), Codex (OpenAI), Claude Code Action
- PM: GitHub Issues + Projects

## Repository Structure

```
.claude/commands/    — Claude Code slash commands (/council, /dispatch, /heartbeat, /status)
.github/workflows/   — GitHub Actions (heartbeat cron)
docs/                — project documentation
tools/heartbeat/     — AI/Tech trend scanner (HN + GitHub)
tools/               — utility scripts
AGENTS.md            — this file (context for AI agents)
PROJECT_CONTEXT.md   — project goals and roadmap
DEV_CONTEXT.md       — development log and current status
```

## Current Status

Early stage. Setting up the orchestration infrastructure:
- [x] Project initialized
- [x] /council slash command created
- [ ] /dispatch slash command
- [ ] GitHub Actions for auto-triggering agents
- [ ] First full cycle: plan → issue → PR → merge

## Rules for Agents

1. **Always read PROJECT_CONTEXT.md** before starting work to understand current goals
2. **Small focused PRs** — one task per PR, no scope creep
3. **Python files** must start with `from __future__ import annotations` and use `@beartype`
4. **No secrets** in code — use environment variables
5. **Conventional commits**: `feat(scope): description` / `fix(scope): description`
6. **Max file size**: 700 lines, max function: 70 lines

## How to Assign Tasks to Jules

Add label `jules` to any GitHub Issue. Jules will:
1. Read the issue description
2. Explore the codebase
3. Implement the solution
4. Create a Pull Request

## Definition of Done

- [ ] `/council` generates tasks from PROJECT_CONTEXT.md
- [ ] `/dispatch` creates Issues with correct labels/assignees
- [ ] At least one agent (Jules or Codex) successfully makes a PR from an issue
- [ ] Full cycle works: plan → issue → PR → merge
