# PROJECT_CONTEXT

## Проект
- Название: Cortex
- Тип: Personal AI monorepo — инструменты, автоматизации, Claude Code инфраструктура
- Репо: github.com/NickStr11/cortex (private)

## Стек
- Python 3.12+, `uv` (зависимости), `pyright` (strict), `beartype` (runtime types)
- AI: Claude Code CLI (primary), Gemini (digests/image gen), Codex CLI MCP (second opinion)
- DB: SQLite
- CI: GitHub Actions (heartbeat cron, auto-review, jules trigger, pipeline)
- Infra: Google Cloud VM (cortex-vm, 34.159.55.61), VPS 194.87.140.204 (PharmOrder)

## Ресурсы
- Claude Code — Max подписка (Opus 4.6)
- ChatGPT Pro ($200/мес) — Codex CLI MCP
- Google Cloud — $300 кредитов (до мая 2026)
- Jules — бесплатный тир

## Два слоя

### Meta-layer (переносимый)
- `.claude/` — commands, agents, skills, hooks (актуальный список в README)
- `.github/workflows/` — 4 автоматизации
- `docs/` — python-rules, git-flow, verify, deploy-vps
- Переносим между проектами через dotfiles-claude

### Tools-layer (инструменты)
- `tools/funding-scanner` — мониторинг funding rate арбитража, deployed на VM
- `tools/kwork-monitor` — автоматизация Kwork.ru (Playwright)
- `tools/tg-monitor` — Telegram digest pipeline (MapReduce, Gemini), deployed на VM
- `tools/heartbeat` — сканер трендов (HN, GitHub, Reddit, Product Hunt)
- `tools/tg-bridge` — Telegram → Claude Code bridge
- `tools/pipeline` — content pipeline (Gemini → Telegram)
- `tools/metrics` — трекинг эффективности AI-агентов
- `tools/tg-pharma` — AI-бот для аптечных операций (остатки, история, заказы)
- `tools/ui-ux`, `tools/scaffold`, `tools/data-prep`, `tools/video` — утилиты

## Смежный проект
- **PharmOrder** (github.com/NickStr11/pharmorder) — аптечная система заказов, VPS production

## Orchestration (оригинальная идея, выполнена)
Полный цикл /council → /dispatch → GitHub Issues → Jules/Codex → PR → merge — работает.
Jules надёжен для кода. Codex GitHub App слабый, Codex CLI MCP мощный.
