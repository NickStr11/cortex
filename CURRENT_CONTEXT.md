# Current Context

## Фокус
- **PharmOrder** — production на VPS (194.87.140.204:8000). Стабилен.
- **TG Digest** — NotebookLM deep research + raw TG chat, задеплоен на VM, timer 03:00 UTC
- **Kwork Automation** — production pipeline (D:\code\2026\3\kwork). Полный цикл: discovery → filter → draft → auto-send → followup.
- **Funding Scanner** — отдельный репо (D:\code\2026\3\funding-scanner). Dashboard на VM (34.159.55.61:8080).
- **MCP Stack** — Context7 (docs), Codex CLI (websearch/code), Exa (semantic search), Context Mode, Generative-UI (charts/diagrams)
- **Skills** — 14 custom + Superpowers v5.0.5 plugin (14) = 28 total
- **OpenClaw** — второй ноут (nsv11), @cipherV2bot, openai-codex/gpt-5.4, Telegram DM-only

## Ближайшие шаги
- [ ] **Обкатать superpowers workflow** на живой задаче (brainstorm → plan → execute)
- [ ] **OpenClaw WSL2 миграция** — когда native Windows gateway начнёт сыпаться
- [ ] **Ротация Telegram tokens** — @cipher_think_bot (cortex) + @cipherV2bot (OpenClaw)
- [ ] **claw-memory GitHub repo** — отдельная память для Клешни
- [ ] PharmOrder: tg-pharma live smoke
- [ ] Funding Scanner: сверка historical rates

## Ссылки
- Полная история: `DEV_CONTEXT.md`
- Funding арбитраж: `memory/funding-arb.md`
- Субагент playbook: `memory/subagents-playbook.md`
