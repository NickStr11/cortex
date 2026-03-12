# Current Context

## 2026-03-12 tg-pharma batch draft
- `tools/tg-pharma` now has batch mode for stacked text/voice inventory tasks.
- New chat controls: `start_batch`, `show_batch`, `apply_batch`, `clear_batch`, `stop_batch`.
- While batch is active, inventory writes (`set/add/subtract/delete/restore`) are accumulated into `ChatState.batch_items` instead of going straight into single-item pending confirm.
- `apply_batch` creates one pending snapshot and then applies entries sequentially with per-item audit log and partial-failure retention.
- Live runtime is clean on the separate bot token (`@pharmorder_ops_bot`): one `python -u main.py`, build marker `2026-03-12-batch-draft-1`, no `409 Conflict`, stderr empty.

## 2026-03-11 tg-pharma bot_refs
- `tools/tg-pharma` switched from heavy local `bot_analytics.db` to lightweight `bot_refs.db` + live VPS `sklit_cache.db`/`order_history.db`.
- New builder: `tools/tg-pharma/build_refs.py`
- New DB: `tools/tg-pharma/data/bot_refs.db`
- Current refs build: 91,335 names, 90,693 makers, 22,019 alias rows, 29.9 MB (without `HISTEAN`).
- `main.py` now uses `BotRefsClient` as the identity/alias layer; `bot_analytics.db` remains only as legacy fallback.

## 2026-03-11 Hot Update
- `tools/tg-pharma` now prefers local analytics built from `C:\Users\User\Desktop\SKLIT`.
- Local DB: `D:\code\2026\2\cortex\tools\tg-pharma\data\bot_analytics.db`
- Contents: 92,323 catalog products, 141,496 alias EAN rows, 85,733 purchase lines.
- Fallback order: local analytics SQLite -> VPS SSH history/catalog.

## Фокус
- **PharmOrder** — production на VPS (194.87.140.204:8000). Созвездие matrix_suppliers пустая — жду доп. инфу для фикса синка.
- **TG Digest** — NotebookLM deep research + raw TG chat, задеплоен на VM, timer 03:00 UTC
- **Kwork Automation** — production pipeline (D:\code\2026\3\kwork). Полный цикл: discovery → filter → draft → auto-send → followup. Живые диалоги с клиентами.
- **Funding Scanner** — отдельный репо (D:\code\2026\3\funding-scanner). Dashboard на VM (34.159.55.61:8080), 10 бирж, hourly cron. Historical rates расходятся на PARADEX/EXTENDED/HYPERLIQUID.

## Ближайшие шаги
- [ ] PharmOrder: скрин СКЛИТ с матрицей Созвездия → supplier-level matrix badges
- [ ] PharmOrder: заполнить matrix_suppliers из product_post.dbf в sync_standalone.py
- [ ] PharmOrder: локальный index.html разошёлся с VPS (Codex deploy) — не синкать вслепую
- [ ] PharmOrder: tg-pharma in `tools/tg-pharma/` — conversational Flash 3 bot, добить live Telegram smoke на `resolve_product` / `purchase_stats` / `set_inventory`, не запускать вместе с `tg-bridge` на том же token
- [ ] Funding Scanner: сверка historical rates с оригиналом (PARADEX дельта до -51%)
- [ ] Перегенерить TELEGRAM_BOT_TOKEN (засвечен в чате)

## Ссылки
- Полная история: `DEV_CONTEXT.md`
- Funding арбитраж: `memory/funding-arb.md`
- Субагент playbook: `memory/subagents-playbook.md`
