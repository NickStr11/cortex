# Cortex

Personal AI lab на Claude Code. Монорепо где **платформа** (`.claude/`) отделена от **продуктов** (`tools/`).

> ⚠️ Это **личный монорепо**, не продукт и не темплейт. Читать для идей, копировать на свой риск. Многие пути hardcoded под Windows / `D:\code\2026\2\cortex` / `~/.claude/projects/D--code-2026-2-cortex/`.

---

## Что внутри

```
.claude/          → платформа (commands, skills, hooks, agents, templates)
tools/            → 8+ самодостаточных продуктов (steam-sniper, max-transcribe, ...)
scripts/          → утилиты (session-search.py, scan-skills.py, ops.sh)
memory/           → subagents-playbook
docs/             → устойчивые правила (git-flow, python-rules, verify)
runtime/          → gitignored, сырые данные
archive/          → старые контексты
```

## Три слоя контекста

| Файл | Где | В git? | Срок жизни |
|------|-----|--------|------------|
| `CLAUDE.md` | репо | ✅ | месяцы (правила проекта) |
| `MEMORY.md` | `~/.claude/projects/.../memory/` | ❌ per-user | недели (индекс на feedback-файлы) |
| `CURRENT_CONTEXT.md` | `~/.claude/projects/.../` | ❌ per-user | дни (активные треки) |

Diary тоже в per-user folder — общая для всех worktree (5 параллельных копий ветки), без merge-конфликтов.

## Что читать первым

- **[`CLAUDE.md`](CLAUDE.md)** — правила проекта, 124 строки
- **[`memory/subagents-playbook.md`](memory/subagents-playbook.md)** — hub-and-spoke + model routing
- **[`.claude/commands/handoff.md`](.claude/commands/handoff.md)** — multi-chat handoff с агрегацией
- **[`.claude/templates/recon-report.md`](.claude/templates/recon-report.md)** — шаблон для исследования внешних репо
- **[`scripts/session-search.py`](scripts/session-search.py)** — простой grep по diary/memory с ranking
- **[`scripts/scan-skills.py`](scripts/scan-skills.py)** — read-only skill curator

## Стек

- Python 3.12+, `uv`, `pyright` (strict), `ruff`, `beartype`
- Claude Code CLI (primary), Codex CLI MCP (second opinion), Gemini (digests)
- SQLite, GCP VM, VPS Timeweb

## Инструменты (`tools/`)

| Tool | Что делает |
|------|------------|
| `steam-sniper` | Трекер цен на CS-скины с lis-skins.com, Telegram-алерты |
| `max-transcribe` | Транскрипция голосовых из Max через Playwright + whisper |
| `tg-monitor` | Daily-дайджесты из Telegram через Gemini / NotebookLM |
| `tg-bridge` | Bridge между Telegram-чатами |
| `tg-pharma` | Аптечный bot (фарм-ассистент) |
| `metrics` | Трекинг эффективности AI-агентов (Jules vs Codex) |
| `kwork-monitor` | Мониторинг фриланс-площадки |
| `ui-ux` | Заготовка под UI |

## Как это эволюционирует

```
Сессия → /diary в per-user folder
       ↓
       Накопление 7+ записей
       ↓
       /reflect → ищет паттерны (нарушения / повторы / анти-паттерны)
       ↓
       Обновляет CLAUDE.md и MEMORY.md
       ↓
       Правило в каждом новом чате грузится в system prompt
```

> **Честно про «автономию»:** это не автономия — это context tax ~210 строк (`CLAUDE.md` 124 + `MEMORY.md` ~90) в каждый промпт. Юзер не должен помнить правила, но Claude **читает их каждый раз**. Цена за единообразие поведения.

## Subagent stack

| Агент | Модель | Назначение |
|-------|--------|-----------|
| `architect` | Opus | архитектура, варианты с трейдоффами |
| `researcher` | Sonnet | ресёрч 3+ шагов, confidence-маркеры |
| `code-reviewer` | Sonnet | ревью после крупного куска |
| `max-transcriber` | Sonnet | голосовые из Max |
| `security-auditor` | Sonnet | аудит перед deploy |
| `tg-digest-reader` | Haiku | TG-дайджесты с GCP VM (просто читает текст) |

Hub-and-spoke: координатор не доверяет выводам субагентов слепо, верифицирует через прямой grep/read.

## Quality gates

- `pre-commit` git hook: 116 тестов (steam-sniper + metrics) за ~2с, secrets scan, ruff lint
- Hooks lifecycle: `PreToolUse` (secrets, gates) / `PostToolUse` (filesize, output filter) / `PreCompact` (auto-diary)

## Setup на новом компе

```bash
npm install -g @anthropic-ai/claude-code
git clone https://github.com/NickStr11/dotfiles-claude ~/.dotfiles-claude
bash ~/.dotfiles-claude/setup.sh
git clone https://github.com/NickStr11/cortex && cd cortex
claude
```

Per-user данные (`MEMORY.md`, `CURRENT_CONTEXT.md`, diary) не клонируются — нужно начать новый дневник или восстановить из OneDrive backup.

## Inspirations

- **Hermes Agent** (NousResearch, [github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)) — изучен через recon-report. Взяли идеи: session search (изначально FTS5, после критики переписали на grep — overkill на 61 документе), read-only skill curator, dry-run для миграций, recon-template. Отвергли: runtime, gateway, autonomous skill mutation, plaintext SUDO_PASSWORD pattern.
- **agentskills.io** — стандарт frontmatter для skills.
- **Karpathy LLM-wiki concept** ([gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)) — 80% паттерна уже работает через diary + reflect + MEMORY.

## Что отвергнуто явно

- Vendor-neutral абстракции (один разработчик)
- Future-proofing без явного триггера
- Autonomous user modeling в стиле Honcho (`aboutme.md` глубже после 22 сессий психоанализа)
- Autonomous skill mutation (single-writer + confirm надёжнее)
- Hermes runtime/gateway/dashboard (мы context pack, не agent product)

## Метрики

- Репо инициирован 2026-02-22, активный дневник с 2026-03-19
- 23 diary за ~6 недель
- 16 скиллов, 6 субагентов
- ~120 строк `CLAUDE.md`, ~90 `MEMORY.md`
- Index 580 KB на 61 документ (через `session-search.py stats`)

## License

[MIT](LICENSE) — но это личный монорепо, не open-source product. Issues / PR не принимаются.
