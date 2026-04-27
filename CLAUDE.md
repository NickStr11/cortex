# Cortex

Personal AI monorepo. `.claude/` — платформа (commands, skills, hooks, agents). `tools/` — продукты (каждый самодостаточный).

## Стек

- Python 3.12+, `uv`, `pyright` (strict), `ruff`, `beartype`
- AI: Claude Code CLI (primary), Gemini (digests/image gen), Codex CLI MCP (second opinion)
- DB: SQLite | Infra: Google Cloud VM (cortex-vm), VPS 194.87.140.204 (PharmOrder)
- Смежный проект: **PharmOrder** (github.com/NickStr11/pharmorder)

## Commands

```bash
cd tools/<tool> && uv sync && uv run python main.py   # запуск тула
bash scripts/ops.sh test      # тесты
bash scripts/ops.sh lint      # ruff
bash scripts/ops.sh check     # pyright
bash scripts/ops.sh secrets   # секреты в tracked files
```

## Architecture

```
.claude/          → commands, skills, hooks, agents (платформа)
tools/<tool>/     → самодостаточные продукты (свой .venv, pyproject.toml)
docs/             → устойчивые правила (git-flow, python-rules, verify)
memory/           → diary + subagents-playbook (в git)
runtime/          → gitignored, сырые данные
archive/          → старые контексты (читать по запросу)
```

> `MEMORY.md`, feedback/project/user/reference/topic файлы и `reflections/` живут
> в `C:\Users\User\.claude\projects\D--code-2026-2-cortex\memory\` — per-user,
> автозагружаются в контекст, не версионируются в git.

## Conventions

- Плоская структура, минимум зависимостей. Код объясняет себя сам.
- 700 строк макс на файл, 70 строк на функцию, 4 уровня вложенности.
- Перед новой библиотекой — Web Search. Актуальные доки > знания модели.
- Новый скрипт/хук/тул → smoke test в той же сессии. Не оставлять непроверенным.
- Ошибки: сначала причина, затем фикс.
- Conventional Commits: `<type>(<scope>): <description>`. См. `docs/git-flow.md`
- **SSOT**: каждый факт живёт в ОДНОМ файле. Остальные ссылаются, не дублируют.

## Workflow

- Explore → Plan → Implement → Verify. Большие задачи → мелкие шаги.
- Git: коммить только по запросу (`/quick-commit`, "закоммить") или при `/handoff`.
- Quality gates автоматизированы через `pre-commit` git hook (tests + secrets + lint).
- Делегируй: 3+ шагов ресёрча → субагент. Независимые задачи → параллельные Task-ы. Перед делегированием — прочитай `memory/subagents-playbook.md`.
- Codex CLI MCP (`reasoningEffort: xhigh`): ресёрч, второе мнение. Использовать активно.

## Memory & Diary

Цикл: **наблюдение → рефлексия → поведение**.

> **Diary и CURRENT_CONTEXT живут в per-user shared folder, НЕ в git** —
> `~/.claude/projects/D--code-2026-2-cortex/`. Это решает проблему
> коллизий номеров между параллельными worktree-ветками. Все 5 worktree
> сразу видят одни и те же diary-файлы и общий CURRENT_CONTEXT.

- `/diary` → `~/.claude/projects/D--code-2026-2-cortex/memory/diary/NNN_YYYY-MM-DD.md`
- `/reflect` → синтез паттернов из diary в правила
- `/handoff` = `/diary` + обновление per-user `CURRENT_CONTEXT.md`
- PreCompact hook автоматически пишет в тот же per-user diary

## Where information goes

| Что | Куда |
|-----|------|
| Правило для агента | `CLAUDE.md` или `.claude/rules/` (в git) |
| Текущий фокус | `~/.claude/projects/D--code-2026-2-cortex/CURRENT_CONTEXT.md` (per-user) |
| Запись сессии | `/diary` → `~/.claude/projects/D--code-2026-2-cortex/memory/diary/` (per-user) |
| Паттерны | `/reflect` → `~/.claude/projects/D--code-2026-2-cortex/memory/MEMORY.md` (per-user) |
| Reusable workflow | `.claude/skills/` (в git) |
| Сырые данные | `runtime/` (gitignored) |

## When uncertain

- Если требования неясны — задай 2-3 уточняющих вопроса.
- После 2 неудачных попыток — остановись и объясни что пробовал и почему не сработало.
- Архитектурные решения — предложи варианты с трейдоффами, а не один ответ.

## Mandatory actions

| Момент | Действие |
|--------|----------|
| Старт сессии | Прочитать `~/.claude/projects/D--code-2026-2-cortex/CURRENT_CONTEXT.md` |
| После кода | Авто (pre-commit hook) |
| Значимые изменения | `/verify` |
| Финиш сессии | `/handoff` |

## Repo invariants

> Принято осознанно. Менять только при явном симптоме.

- Cortex = intentional personal monorepo. Lab + продукты вместе.
- `.claude/` = platform, `tools/` = products. Уже разведены.
- Claude Code = выбранный стек. Без vendor-neutral абстракций.
- Без future-proofing и extra layers без запроса.

## Instruction precedence

1. Явный запрос пользователя
2. `CLAUDE.md` + `.claude/rules/`
3. `~/.claude/CLAUDE.md` (global)
4. `~/.claude/projects/D--code-2026-2-cortex/memory/MEMORY.md`

## Reference

> Читать по запросу, не грузятся автоматически.

- `docs/verify.md` — verification workflow
- `docs/git-flow.md` — git conventions
- `docs/python-rules.md` — Python rules
- `docs/deploy-vps.md` — VPS deployment
- `memory/subagents-playbook.md` — делегирование
