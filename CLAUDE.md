# Project Rules

## 0. Repo Invariants

> Эти решения приняты осознанно. Не предлагай их менять без явного симптома.

- **Cortex = intentional personal monorepo.** И lab, и продукты. Не предлагать split.
- **`.claude/` = platform layer, `tools/` = products layer.** Уже разведены. Не разводить повторно.
- **Claude Code = выбранный стек.** Не предлагать vendor-neutral абстракции.
- **Не предлагать future-proofing, extra layers, архитектурные перестройки** без запроса пользователя.

### Context files

| Файл | Роль | Когда читать |
|------|------|-------------|
| `CLAUDE.md` | Правила + проект + стек | Автоматически |
| `CURRENT_CONTEXT.md` | Что активно прямо сейчас, следующий шаг | При старте |

Старые записи (до diary): `archive/dev-context-*.md` — читать по запросу.

### Instruction precedence

1. Явный запрос пользователя (всегда выше всего)
2. `CLAUDE.md` (project rules)
3. `~/.claude/CLAUDE.md` (global rules)
4. `memory/MEMORY.md` (accumulated patterns)

### Where new information goes

| Что | Куда |
|-----|------|
| Правило для агента | `CLAUDE.md` или `.claude/` |
| Текущий фокус, следующий шаг | `CURRENT_CONTEXT.md` |
| Запись сессии | `/diary` → `memory/diary/` |
| Паттерны между сессиями | `/reflect` → `CLAUDE.md` + `memory/MEMORY.md` |
| Контекст одного тула | `tools/<tool>/memory/` или `tools/<tool>/inbox/` |
| Reusable reference | `docs/` (устойчивое) или `research/` (сырое) |
| Reusable workflow | `.claude/skills/` |
| Raw артефакт, сырые данные | `runtime/` (gitignored) |
| Код и реализация | `tools/<tool>/` |

## 1. Project

Cortex — personal AI monorepo. `.claude/` — платформа (commands, skills, hooks, agents). `tools/` — продукты (каждый самодостаточный). Переносим между проектами через dotfiles-claude.

- Репо: github.com/NickStr11/cortex (private)
- Смежный проект: **PharmOrder** (github.com/NickStr11/pharmorder) — аптечная система заказов, VPS production

### Стек

- Python 3.12+, `uv` (зависимости), `pyright` (strict), `beartype` (runtime types)
- AI: Claude Code CLI (primary), Gemini (digests/image gen), Codex CLI MCP (second opinion)
- DB: SQLite
- CI: GitHub Actions (heartbeat cron, auto-review, jules trigger, pipeline)
- Infra: Google Cloud VM (cortex-vm), VPS 194.87.140.204 (PharmOrder)
- Frontend: Next.js / HTML + Vanilla JS
- PM: `uv` (Python), `npm` (Node.js)
- Python rules: `docs/python-rules.md`

### Ресурсы

- Claude Code — Max подписка (Opus 4.6)
- ChatGPT Pro ($200/мес) — Codex CLI MCP
- Google Cloud — $300 кредитов (до мая 2026)

## 2. Quick Start

```bash
# Python tools — у каждого свой .venv
cd tools/<tool> && uv sync && uv run python main.py

# Проверки
bash scripts/ops.sh test      # тесты
bash scripts/ops.sh check     # pyright
bash scripts/ops.sh lint      # ruff
bash scripts/ops.sh secrets   # секреты в tracked files
```

## 3. Memory & Diary

Память работает в цикле: **наблюдение → рефлексия → поведение**.

- **`/diary`** — записывает сессию в `memory/diary/NNN_YYYY-MM-DD.md`
- **`/reflect`** — синтезирует паттерны из diary в правила CLAUDE.md
- **PreCompact hook** — автоматически вызывает `/diary` перед сжатием контекста
- **`/handoff`** = `/diary` + обновление CURRENT_CONTEXT.md

Длинный контекст → предложи `/handoff` и новый чат.

## 4. Technical Rules

- Плоская структура, минимум зависимостей. Код объясняет себя сам.
- **700 строк** макс на файл, **70 строк** на функцию, **4 уровня** вложенности.
- Перед использованием новых библиотек — Web Search. Не полагайся на знания модели.
- При ошибке — сначала причина, затем конкретный фикс.

## 5. Workflow

- Перед значительными изменениями — план. Большие задачи → мелкие шаги.
- Git: коммить ТОЛЬКО по запросу (`/quick-commit`, "закоммить") или при `/handoff`. Не коммить в main напрямую.
- Не запускай `npm run dev` / `python -m ...` автоматически.
- Quality Gates: Build → Types → Lint → Tests (80%+) → Security → Diff.
- Conventional Commits: `<type>(<scope>): <description>`. Детали: `docs/git-flow.md`

### Делегирование — субагенты и Codex
- **Не делай сам то что можно делегировать.** Подписки оплачены — выжимай максимум.
- 3+ шагов ресёрча → субагент Explore, не 5 последовательных Grep руками.
- Независимые задачи → параллельные Task-ы в одном сообщении.
- Проверки/аудит → `run_in_background`, не блокируй основную работу.
- **Codex CLI MCP** (`reasoningEffort: xhigh`): ресёрч, второе мнение, веб-поиск. Использовать активно.
- Полный playbook: `memory/subagents-playbook.md`

## 6. Mandatory Actions

| Момент | Действие |
|--------|----------|
| **Старт сессии** | Прочитать CURRENT_CONTEXT.md |
| **После кода** | Проверить build/тесты |
| **Перед PR** | `/verify` |
| **Финиш сессии** | `/handoff` |

## 7. Communication

- Русский по умолчанию. Без воды. Прямо и по существу.
- Ошибки: причина + фикс, без оценочных суждений.

## 8. Security

- API-ключи → `.env` + `.gitignore`. Хуки блокируют автоматически.

## 9. Reference

> Не грузятся автоматически — читать по запросу когда нужны.

- `docs/verify.md` — verification workflow
- `docs/git-flow.md` — git conventions
- `docs/python-rules.md` — Python rules
- `docs/deploy-vps.md` — VPS deployment
- `tools/ui-ux/GUIDE.md` — UI/UX design system
