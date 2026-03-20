# Current Context

## Фокус
- **PharmOrder** — production на VPS (194.87.140.204:8000). Стабилен.
- **TG Digest** — NotebookLM deep research + raw TG chat, задеплоен на VM, timer 03:00 UTC
- **Kwork Automation** — production pipeline (D:\code\2026\3\kwork). Полный цикл: discovery → filter → draft → auto-send → followup.
- **Funding Scanner** — отдельный репо (D:\code\2026\3\funding-scanner). Dashboard на VM (34.159.55.61:8080).
- **MCP Stack** — Context7 (docs), Codex CLI 5.3 (websearch/code), Exa (semantic search), Playwright, Context Mode
- **Skills** — 15 local + 40 GSD + Superpowers plugin
- **OpenClaw** — второй ноут (nsv11), @cipherV2bot, openai-codex/gpt-5.4, Telegram DM-only
- **Diary система** — обкатана. PreCompact hook пишет diary автоматически.

## Что сделано (session 003, 2026-03-20)
- NotebookLM auth починен (Playwright MCP workaround), куки обновлены на VM
- Video skill → NotebookLM как основной путь для YouTube
- ops.sh починен (ROOT bug), ruff + pyright добавлены, pre-commit hook
- CLAUDE.md переработан (95 строк, path-scoped rules)
- GSD установлен (40+ команд), context monitor в statusline
- Все commands/skills проаудированы — всё работает

## Ближайшие шаги
- [ ] **Funding: EdgeX verifier** — сделать верификатор fundingRate vs forecastFundingRate (не просто переключить, а сравнить по монетам/моментам)
- [ ] **Funding: добавить BingX + Aster** — расширить coverage бирж
- [ ] **Funding: Codex action plan** — попросить Codex написать 3-шаговый план по parity с оригиналом
- [ ] **GSD обкатка** — при следующей multi-step задаче (funding exchanges или новый проект)
- [ ] **Обкатать /reflect** — синтез паттернов из diary после 3-5 записей (уже 3 записи есть)
- [ ] **PharmOrder: tg-pharma live smoke**
- [ ] **OpenClaw WSL2 миграция** — когда native Windows gateway начнёт сыпаться
- [ ] **Ротация Telegram tokens** — @cipher_think_bot (cortex) + @cipherV2bot (OpenClaw)

## Ссылки
- Старые записи: `archive/dev-context-*.md`
- Funding арбитраж: `memory/funding-arb.md`
- Funding research: `D:\code\2026\3\funding-scanner\runtime\research\`
- Субагент playbook: `memory/subagents-playbook.md`
- CLAUDE.md best practices: vibemeta.app, potapov.dev
