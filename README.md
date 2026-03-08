# Cortex

Personal AI monorepo. Инструменты, автоматизации и Claude Code инфраструктура.

## Tools

| Tool | Статус | Назначение |
|------|--------|------------|
| **funding-scanner** | Active | Мониторинг funding rate арбитража CEX/DEX, дашборд, TG алерты |
| **kwork-monitor** | Active | Автоматизация Kwork.ru — создание кворков через Playwright |
| **tg-monitor** | Active | Telegram digest pipeline (MapReduce, Gemini). Deployed на VM |
| **heartbeat** | Active | Сканер трендов (HN, GitHub, Reddit, Product Hunt) |
| **tg-bridge** | Active | Telegram → Claude Code bridge (polling бот) |
| **pipeline** | Idle | Content pipeline (Gemini → Telegram) |
| **metrics** | Idle | Трекинг эффективности AI-агентов |
| **ui-ux** | Util | Design system БД (BM25 поиск стилей/цветов/шрифтов) |
| **scaffold** | Util | Генератор шаблонов для новых проектов |
| **data-prep** | Util | Подготовка данных для AI (токенизация, чанкинг) |
| **video** | Util | Извлечение аудио/субтитров из видео |

## Structure

```
cortex/
  tools/           — инструменты (каждый самодостаточный, свой .venv + pyproject.toml)
  .claude/         — Claude Code config
    commands/      — slash commands (/council, /dispatch, /heartbeat, /status, ...)
    agents/        — agent specs (architect, code-reviewer, security-auditor, verify-agent)
    skills/        — skills (systematic-debugging, subagent-dev, parallel-agents, banana)
    hooks/         — git hooks (check-secrets, protect-main, check-filesize, ...)
  .github/         — Actions (heartbeat cron, auto-review, jules trigger)
  docs/            — python-rules, git-flow, verify, deploy-vps
  research/        — заметки и анализы
```

## Stack

- Python 3.12+, `uv` для зависимостей
- Type checking: `pyright` (strict) + `beartype` (runtime)
- DB: SQLite
- AI: Claude Code (primary), Gemini (digests, image gen), Codex CLI MCP (second opinion)
- Infra: Google Cloud VM (cortex-vm), GitHub Actions

## Quick Start

```bash
git clone https://github.com/NickStr11/cortex
cd cortex

# Любой тул — отдельная среда
cd tools/funding-scanner && uv sync && uv run python main.py
cd tools/heartbeat && uv sync && uv run python main.py
```

## Operations

```bash
bash scripts/ops.sh test      # тесты (heartbeat, metrics)
bash scripts/ops.sh check     # typecheck (pyright)
bash scripts/ops.sh lint      # lint (ruff)
bash scripts/ops.sh secrets   # проверка секретов в tracked files
bash scripts/ops.sh sync      # установка зависимостей всех тулов
```

## License

[MIT](LICENSE)
