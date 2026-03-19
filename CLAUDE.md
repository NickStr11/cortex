# Project Rules

## 0. Repo Invariants

> Эти решения приняты осознанно. Не предлагай их менять без явного симптома.

- **Cortex = intentional personal monorepo.** И lab, и продукты. Не предлагать split.
- **`.claude/` = platform layer, `tools/` = products layer.** Уже разведены. Не разводить повторно.
- **Claude Code = выбранный стек.** Не предлагать vendor-neutral абстракции.
- **Не предлагать future-proofing, extra layers, архитектурные перестройки** без запроса пользователя.

### Роли root context files

| Файл | Роль | Когда читать |
|------|------|-------------|
| `CLAUDE.md` | Правила поведения агента | Автоматически |
| `PROJECT_CONTEXT.md` | Что за система, стек, структура | При старте |
| `CURRENT_CONTEXT.md` | Что активно прямо сейчас, следующий шаг | При старте |
| `DEV_CONTEXT.md` | Append-only история решений и handoff | По запросу / при handoff |
Это **разные функции**, не дублирование. Поднимать вопрос только если два файла реально описывают одно и то же.

### Instruction precedence

1. Явный запрос пользователя (всегда выше всего)
2. `CLAUDE.md` (project rules)
3. `~/.claude/CLAUDE.md` (global rules)
4. `memory/MEMORY.md` (accumulated patterns)
5. Остальные context files

### Context loading

- **При старте**: `CLAUDE.md` (auto) + `CURRENT_CONTEXT.md` + `PROJECT_CONTEXT.md`
- **По запросу**: `DEV_CONTEXT.md`, `memory/`, `knowledge/`
- **Не грузить** без необходимости: `DEV_CONTEXT.md` целиком (тяжёлый), файлы в `research/`

### Where new information goes

| Что | Куда |
|-----|------|
| Правило для агента | `CLAUDE.md` или `.claude/` |
| Состояние проекта, стек | `PROJECT_CONTEXT.md` |
| Текущий фокус, следующий шаг | `CURRENT_CONTEXT.md` |
| Завершённая работа, решения | `DEV_CONTEXT.md` (append) |
| Контекст одного тула | `tools/<tool>/memory/` или `tools/<tool>/inbox/` |
| Паттерны между сессиями | `memory/MEMORY.md` |
| Reusable reference | `docs/` (устойчивое) или `research/` (сырое) |
| Reusable workflow | `.claude/skills/` |
| Raw артефакт, сырые данные | `runtime/` (gitignored) |
| Код и реализация | `tools/<tool>/` |

- Tool-local > root-level когда инфа специфична для одного тула
- `PROJECT_CONTEXT` = долгая рамка, `CURRENT_CONTEXT` = что актуально сейчас, `DEV_CONTEXT` = как сюда пришли
- Не дублировать одно и то же в нескольких context files

### Structural review — порядок

При ревью структуры репо — hygiene-first:
1. Dirty worktree / незакоммиченные изменения
2. `.gitignore` / runtime hygiene
3. Кодировка и читаемость контекстных файлов
4. Мусор в корне
5. Консистентность scaffolds в `tools/`
6. Архитектурные предложения — **только если есть реальная боль**

Маркируй выводы: `confirmed issue` / `design preference` / `hypothesis`.

## 1. Quick Start

```bash
# Python tools — у каждого свой .venv
cd tools/<tool> && uv sync && uv run python main.py

# Проверки
bash scripts/ops.sh test      # тесты
bash scripts/ops.sh check     # pyright
bash scripts/ops.sh lint      # ruff
bash scripts/ops.sh secrets   # секреты в tracked files
```

Cortex = personal AI monorepo. `.claude/` — платформа (commands, skills, hooks, agents). `tools/` — продукты (каждый самодостаточный). Подробнее: `PROJECT_CONTEXT.md`.

## 2. Context & Memory

- Длинный контекст → предложи `/handoff` и новый чат.

## 3. Technical Rules

- Плоская структура, минимум зависимостей. Код объясняет себя сам.
- **700 строк** макс на файл, **70 строк** на функцию, **4 уровня** вложенности.
- Перед использованием новых библиотек — Web Search. Не полагайся на знания модели.
- При ошибке — сначала причина, затем конкретный фикс.

## 4. Workflow

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

## 5. Mandatory Actions

| Момент | Действие |
|--------|----------|
| **Старт сессии** | Прочитать CURRENT_CONTEXT.md и PROJECT_CONTEXT.md |
| **После кода** | Проверить build/тесты |
| **Перед PR** | `/verify` |
| **Финиш сессии** | `/handoff` |

## 6. Communication

- Русский по умолчанию. Без воды. Прямо и по существу.
- Ошибки: причина + фикс, без оценочных суждений.

## 7. Stack Defaults

> Конкретный стек — в PROJECT_CONTEXT.md

- **Frontend**: Next.js / HTML + Vanilla JS
- **Backend**: Python (3.12+) / Node.js (20+)
- **DB**: PostgreSQL (Supabase) / SQLite (локально)
- **PM**: `uv` (Python), `npm` (Node.js)
- Python: `docs/python-rules.md`

## 8. Security

- API-ключи → `.env` + `.gitignore`. Хуки блокируют автоматически.
- Ошибки → "Известные проблемы" в DEV_CONTEXT.md.

## 9. Reference

> Не грузятся автоматически — читать по запросу когда нужны.

- `docs/verify.md` — verification workflow
- `docs/git-flow.md` — git conventions
- `docs/python-rules.md` — Python rules
- `docs/deploy-vps.md` — VPS deployment
- `tools/ui-ux/GUIDE.md` — UI/UX design system
