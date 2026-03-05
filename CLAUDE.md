# Project Rules

## 1. Context & Memory

- **DEV_CONTEXT.md** — лог разработки. Читай при старте, обновляй при завершении.
- **PROJECT_CONTEXT.md** — описание проекта, стек, этапы. Читай при старте.
- Длинный контекст → предложи `/handoff` и новый чат.

## 2. Technical Rules

- Плоская структура, минимум зависимостей. Код объясняет себя сам.
- **700 строк** макс на файл, **70 строк** на функцию, **4 уровня** вложенности.
- Перед использованием новых библиотек — Web Search. Не полагайся на знания модели.
- При ошибке — сначала причина, затем конкретный фикс.

## 3. Workflow

- Перед значительными изменениями — план. Большие задачи → мелкие шаги.
- Git: коммить ТОЛЬКО по запросу (`/quick-commit`, "закоммить") или при `/handoff`. Не коммить в main напрямую.
- Не запускай `npm run dev` / `python -m ...` автоматически.
- Quality Gates: Build → Types → Lint → Tests (80%+) → Security → Diff.
- Conventional Commits: `<type>(<scope>): <description>`. Детали: @docs/git-flow.md

### Делегирование — субагенты и Codex
- **Не делай сам то что можно делегировать.** Подписки оплачены — выжимай максимум.
- 3+ шагов ресёрча → субагент Explore, не 5 последовательных Grep руками.
- Независимые задачи → параллельные Task-ы в одном сообщении.
- Проверки/аудит → `run_in_background`, не блокируй основную работу.
- **Codex CLI MCP** (`reasoningEffort: xhigh`): ресёрч, второе мнение, веб-поиск. Использовать активно.
- Полный playbook: @memory/subagents-playbook.md

## 4. Mandatory Actions

| Момент | Действие |
|--------|----------|
| **Старт сессии** | Прочитать DEV_CONTEXT.md, PROJECT_CONTEXT.md и последний дейлик из Obsidian (`C:/Program Files/Obsidian/obsVaultPC/GameChanger/Daily/`) |
| **После кода** | Проверить build/тесты |
| **Перед PR** | `/verify` |
| **Финиш сессии** | `/handoff` |

## 5. Communication

- Русский по умолчанию. Без воды. Прямо и по существу.
- Ошибки: причина + фикс, без оценочных суждений.

## 6. Stack Defaults

> Конкретный стек — в PROJECT_CONTEXT.md

- **Frontend**: Next.js / HTML + Vanilla JS
- **Backend**: Python (3.12+) / Node.js (20+)
- **DB**: PostgreSQL (Supabase) / SQLite (локально)
- **PM**: `uv` (Python), `npm` (Node.js)
- Python: @docs/python-rules.md

## 7. Security

- API-ключи → `.env` + `.gitignore`. Хуки блокируют автоматически.
- Ошибки → "Известные проблемы" в DEV_CONTEXT.md.

## 8. Reference

- @docs/verify.md — verification workflow
- @docs/git-flow.md — git conventions
- @docs/python-rules.md — Python rules
- @docs/deploy-vps.md — VPS deployment
- @tools/ui-ux/GUIDE.md — UI/UX design system
