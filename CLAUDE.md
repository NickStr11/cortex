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
memory/           → diary, MEMORY.md, topic files
runtime/          → gitignored, сырые данные
archive/          → старые контексты (читать по запросу)
```

## Conventions

- Плоская структура, минимум зависимостей. Код объясняет себя сам.
- 700 строк макс на файл, 70 строк на функцию, 4 уровня вложенности.
- Перед новой библиотекой — Web Search. Актуальные доки > знания модели.
- Новый скрипт/хук/тул → smoke test в той же сессии. Не оставлять непроверенным.
- Ошибки: сначала причина, затем фикс.
- Conventional Commits: `<type>(<scope>): <description>`. См. `docs/git-flow.md`

## Workflow

- Explore → Plan → Implement → Verify. Большие задачи → мелкие шаги.
- Git: коммить только по запросу (`/quick-commit`, "закоммить") или при `/handoff`.
- Quality gates автоматизированы через `pre-commit` git hook (tests + secrets + lint).
- Делегируй: 3+ шагов ресёрча → субагент. Независимые задачи → параллельные Task-ы. Перед делегированием — прочитай `memory/subagents-playbook.md`.
- Codex CLI MCP (`reasoningEffort: xhigh`): ресёрч, второе мнение. Использовать активно.

## Memory & Diary

Цикл: **наблюдение → рефлексия → поведение**.

- `/diary` → `memory/diary/NNN_YYYY-MM-DD.md`
- `/reflect` → синтез паттернов из diary в правила
- `/handoff` = `/diary` + обновление CURRENT_CONTEXT.md
- PreCompact hook автоматически вызывает `/diary`

## Where information goes

| Что | Куда |
|-----|------|
| Правило для агента | `CLAUDE.md` или `.claude/rules/` |
| Текущий фокус | `CURRENT_CONTEXT.md` |
| Запись сессии | `/diary` → `memory/diary/` |
| Паттерны | `/reflect` → `memory/MEMORY.md` |
| Reusable workflow | `.claude/skills/` |
| Сырые данные | `runtime/` (gitignored) |

## When uncertain

- Если требования неясны — задай 2-3 уточняющих вопроса.
- После 2 неудачных попыток — остановись и объясни что пробовал и почему не сработало.
- Архитектурные решения — предложи варианты с трейдоффами, а не один ответ.

## Mandatory actions

| Момент | Действие |
|--------|----------|
| Старт сессии | Прочитать `CURRENT_CONTEXT.md` |
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
4. `memory/MEMORY.md`

## Reference

> Читать по запросу, не грузятся автоматически.

- `docs/verify.md` — verification workflow
- `docs/git-flow.md` — git conventions
- `docs/python-rules.md` — Python rules
- `docs/deploy-vps.md` — VPS deployment
- `memory/subagents-playbook.md` — делегирование
