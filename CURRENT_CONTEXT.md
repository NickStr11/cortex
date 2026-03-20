# Current Context

## Фокус
- **PharmOrder** — production на VPS (194.87.140.204:8000). Стабилен.
- **TG Digest** — NotebookLM deep research + raw TG chat, задеплоен на VM, timer 03:00 UTC
- **Kwork Automation** — production pipeline (D:\code\2026\3\kwork). Полный цикл: discovery → filter → draft → auto-send → followup.
- **Funding Scanner** — отдельный репо (D:\code\2026\3\funding-scanner). Dashboard на VM (34.159.55.61:8080).
- **MCP Stack** — Context7 (docs), Codex CLI 5.3 (websearch/code), Exa (semantic search), Context Mode
- **Skills** — 14 custom + Superpowers plugin = 28 total
- **OpenClaw** — второй ноут (nsv11), @cipherV2bot, openai-codex/gpt-5.4, Telegram DM-only
- **Diary система** — обкатана (сессия 001). PreCompact hook пишет diary автоматически.

## Ближайшие шаги
- [ ] **Funding: TON EXTENDED → DRIFT** — проверить через official API обе ноги перед входом (101 APR, обе ноги стабильны 30d)
- [ ] **Funding: EdgeX адаптер** — переключить на forecastFundingRate (original ближе к forecast, не settled)
- [ ] **Обкатать /reflect** — синтез паттернов из diary после 3-5 записей
- [ ] **Обкатать superpowers workflow** на живой задаче (brainstorm → plan → execute)
- [ ] **OpenClaw WSL2 миграция** — когда native Windows gateway начнёт сыпаться
- [ ] **Ротация Telegram tokens** — @cipher_think_bot (cortex) + @cipherV2bot (OpenClaw)
- [ ] **claw-memory GitHub repo** — отдельная память для Клешни
- [ ] PharmOrder: tg-pharma live smoke

## Ссылки
- Старые записи: `archive/dev-context-*.md`
- Funding арбитраж: `memory/funding-arb.md`
- Funding research: `D:\code\2026\3\funding-scanner\runtime\research\`
- Субагент playbook: `memory/subagents-playbook.md`
