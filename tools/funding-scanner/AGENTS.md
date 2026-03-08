# Funding Scanner

Локальный проект внутри `cortex`, но работать по нему нужно как по отдельному проекту.

## Scope

- Всё project-local хранить прямо в `tools/funding-scanner/`.
- Не смешивать контекст `funding-scanner` с другими тулзами из `cortex`.
- В корневые `PROJECT_CONTEXT.md` / `DEV_CONTEXT.md` `cortex` писать только короткую сводку, если это реально влияет на весь монорепо.

## Working Set

Перед содержательной задачей читать:
1. `AGENTS.md`
2. `memory/PROJECT_CONTEXT.md`
3. `memory/DEV_CONTEXT.md`
4. `inbox/now.md`

## Project Rules

- Главный критерий: данные должны быть максимально близки к оригинальной панели.
- Сначала точность данных, потом UI-полировка.
- Live и historical считать и проверять отдельно.
- Любую содержательную сверку с оригиналом сохранять в `runtime/research/`, а не оставлять только в чате.
- Если меняется направление работ, обновлять `memory/DEV_CONTEXT.md` и `inbox/now.md`.
