# Cortex — Claude Code Infrastructure

## Что здесь

Cortex содержит переносимую Claude Code обвязку: commands, agents, skills, hooks.
Всё живёт в `.claude/` и работает в любом проекте через dotfiles-claude.

## Commands (14)

Slash-команды для Claude Code CLI:

| Команда | Назначение |
|---------|------------|
| `/council` | AI-консилиум (CPO/CTO/CMO) → генерация задач |
| `/dispatch` | Создание GitHub Issues с назначением агентов |
| `/heartbeat` | Сканер трендов (HN, GitHub, Reddit, Product Hunt) |
| `/status` | Статус проекта |
| `/verify` | Проверка качества кода (build, types, lint, tests, security) |
| `/handoff` | Сохранение прогресса перед сменой сессии |
| `/quick-commit` | Быстрый Git workflow |
| `/tg-digest` | Telegram digest через Gemini |
| `/new-project` | Scaffold нового проекта |
| `/screenshot` | Скриншот из буфера обмена |
| `/tdd` | Test-Driven Development workflow |
| `/build-fix` | Диагностика и починка ошибок билда |
| `/learn` | Мета-обучение: анализ паттернов работы |
| `/metrics` | Трекинг эффективности агентов |

## Agents (4)

Specs в `.claude/agents/` — используются как субагенты через Task tool:

- **architect** — планирование архитектуры и стека
- **code-reviewer** — ревью кода (качество, безопасность, читаемость)
- **security-auditor** — аудит безопасности перед деплоем
- **verify-agent** — проверка Definition of Done

## Skills (7)

В `.claude/skills/`:

- **systematic-debugging** — 4-фазный root cause analysis (из obra/superpowers)
- **subagent-dev** — fresh subagent per task + двойной review
- **parallel-agents** — dispatch агента на каждый независимый домен
- **banana** — генерация изображений через Gemini Pro Image
- **screenshot**, **frontend-design**, **webapp-testing** — project skills

## Hooks (8)

Git hooks в `.claude/hooks/`:

- `check-secrets` — блокировка коммитов с API ключами
- `protect-main` — защита main ветки
- `check-filesize` — лимит размера файлов
- `pre-commit-check` — pre-commit валидация
- `output-secret-filter` — фильтрация секретов из output
- `mcp-usage-tracker` — мониторинг использования MCP
- `expensive-tool-warning` — предупреждение о дорогих операциях
- `grab-screenshot` — автозахват скриншотов

## Workflows (4)

GitHub Actions в `.github/workflows/`:

- `heartbeat.yml` — cron сканер трендов (каждые 3 дня)
- `code-review.yml` — auto-review Pull Requests
- `jules-trigger.yml` — триггер Jules по label на Issue
- `pipeline.yml` — контент-пайплайн (DEV_CONTEXT → Telegram)

## External Agents

- **Jules** (Google) — надёжен для кода и рефакторинга, бесплатный тир
- **Codex CLI MCP** — второе мнение, веб-поиск, reasoningEffort: xhigh
- **Codex GitHub App** — слабый, годится только для доков/шаблонов

## Rules for Agents

> Полные правила — в `CLAUDE.md`. Здесь только quick reference.

- Читай `CURRENT_CONTEXT.md` перед работой
- Conventional commits: `feat(scope): description`
- Python: `@beartype` + type annotations
