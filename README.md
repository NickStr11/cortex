# Cortex

Personal AI monorepo. Инструменты, автоматизации и Claude Code инфраструктура.

## New Machine Setup

```bash
# 1. Claude Code
npm install -g @anthropic-ai/claude-code

# 2. Dotfiles (глобальные правила, aboutme, ai-rules, глобальные хуки)
git clone https://github.com/NickStr11/dotfiles-claude ~/.dotfiles-claude
bash ~/.dotfiles-claude/setup.sh

# 3. Cortex
git clone https://github.com/NickStr11/cortex
cd cortex

# 4. Секреты
cp .env.example .env
# заполнить: GOOGLE_API_KEY, TELEGRAM_BOT_TOKEN, EXA_API_KEY, etc.

# 5. MCP серверы (auth где нужно)
# Codex CLI — откроет браузер для ChatGPT Pro auth:
npx codex-cli-mcp
# Остальные (context7, exa, playwright, etc.) подхватятся из .mcp.json

# 6. Запуск
claude
```

## Tools

| Tool | Статус | Назначение |
|------|--------|------------|
| **funding-scanner** | Active | Мониторинг funding rate арбитража CEX/DEX, дашборд, TG алерты |
| **kwork-monitor** | Active | Автоматизация Kwork.ru — создание кворков через Playwright |
| **tg-monitor** | Active | Telegram digest pipeline (MapReduce, Gemini). Deployed на VM |
| **tg-pharma** | Active | AI-бот для аптечных операций (остатки, история, заказы) |
| **heartbeat** | Active | Сканер трендов (HN, GitHub, Reddit, Product Hunt) |
| **tg-bridge** | Active | Telegram → Claude Code bridge (polling бот) |
| **pipeline** | Idle | Content pipeline (Gemini → Telegram) |
| **metrics** | Idle | Трекинг эффективности AI-агентов |
| **ui-ux** | Util | Design system БД (BM25 поиск стилей/цветов/шрифтов) |
| **scaffold** | Util | Генератор шаблонов для новых проектов |
| **data-prep** | Util | Подготовка данных для AI (токенизация, чанкинг) |
| **video** | Util | Извлечение аудио/субтитров из видео |

## Claude Code Infrastructure

### Skills (14 custom + Superpowers plugin)
| Skill | Назначение |
|-------|------------|
| `skill-forge` | Мета-скилл: генерация скиллов через Exa research |
| `frontend-design` | Production-grade UI с дизайн-системой |
| `gsd-method` | Spec-driven разработка (Get Shit Done) |
| `autoresearch` | Автономные ML-эксперименты (a la Karpathy) |
| `crewai-agents` | Мульти-агент команды с ролями |
| `langgraph-agents` | Граф-based воркфлоу с условными переходами |
| `mcp-builder` | Создание MCP серверов (Python/Node) |
| `webapp-testing` | E2E тестирование через Playwright |
| `eval` | Post-session self-evaluation |
| `banana` | Генерация изображений через Gemini |
| `video` | Анализ видео (URL или локальный файл) |
| `docx` | Создание/редактирование Word документов |
| `xlsx` | Работа с Excel файлами |
| `pdf` | Работа с PDF файлами |

### Commands (14)
`/council` `/dispatch` `/verify` `/handoff` `/quick-commit` `/status` `/heartbeat` `/build-fix` `/tdd` `/learn` `/metrics` `/new-project` `/screenshot` `/tg-digest`

### Hooks (8)
`check-secrets` `check-filesize` `protect-main` `pre-commit-check` `expensive-tool-warning` `mcp-usage-tracker` `grab-screenshot` `output-secret-filter`

### Agents (3)
`architect` `code-reviewer` `security-auditor`

### MCP Servers (7)
`context7` (docs) · `codex-cli` (GPT-5, websearch) · `exa` (semantic search) · `playwright` (browser) · `sequential-thinking` · `context-mode` (context compression) · `idea-reality` (duplicate check)

## Structure

```
cortex/
  tools/           — инструменты (каждый самодостаточный, свой .venv + pyproject.toml)
  .claude/
    commands/      — 14 slash commands
    agents/        — 3 agent specs
    skills/        — 14 skills
    hooks/         — 8 hooks
    settings.json  — project hooks config
  .github/         — Actions (heartbeat cron, auto-review, jules trigger)
  docs/            — python-rules, git-flow, verify, deploy-vps
  .mcp.json        — MCP server definitions (project-level)
  .env.example     — все переменные окружения
  CLAUDE.md        — правила агента
  PROJECT_CONTEXT  — стек и архитектура
  CURRENT_CONTEXT  — активный фокус
  DEV_CONTEXT      — append-only история решений
```

## Stack

- Python 3.12+, `uv` для зависимостей
- Type checking: `pyright` (strict) + `beartype` (runtime)
- DB: SQLite
- AI: Claude Code (primary), Gemini (digests, image gen), Codex CLI MCP (second opinion)
- Infra: Google Cloud VM (cortex-vm), VPS (PharmOrder), GitHub Actions

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
