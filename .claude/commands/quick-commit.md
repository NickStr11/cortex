# /quick-commit — Быстрый Git Workflow

Описание изменений: $ARGUMENTS

## Инструкция

Эта команда автоматизирует полный цикл git workflow для текущих изменений.

### Шаг 1 — Анализ и подготовка

1. Проанализируй описание изменений из `$ARGUMENTS`.
2. Определи **тип** (type) изменений согласно `docs/git-flow.md`:
   - `feat` — новый функционал
   - `fix` — баг-фикс
   - `docs` — документация
   - `refactor` — рефакторинг
   - `style` — форматирование
   - `test` — тесты
   - `chore` — конфигурация/зависимости
3. Сформулируй краткое описание на английском (subject) для коммита и slug для ветки.
4. Определи подходящий **scope** (например: `commands`, `heartbeat`, `deps`), если это возможно.

### Шаг 2 — Создание ветки

Создай новую ветку с правильным именем:
```bash
git checkout -b <type>/<slug>
```
*ВНИМАНИЕ: Никогда не коммить в `main` напрямую.*

### Шаг 3 — Фиксация изменений

1. Добавь все измененные файлы:
   ```bash
   git add -A
   ```
2. Создай коммит с conventional message:
   ```bash
   git commit -m "<type>(<scope>): <subject>"
   ```

### Шаг 4 — Пуш и Pull Request

1. Отправь ветку в репозиторий:
   ```bash
   git push origin <type>/<slug>
   ```
2. Создай Pull Request через GitHub CLI:
   ```bash
   gh pr create \
     --title "<type>(<scope>): <subject>" \
     --body "Automated PR created via /quick-commit. Original description: $ARGUMENTS"
   ```

### Шаг 5 — Отчёт

Выведи результат выполнения:
- ✅ Ветка `<type>/<slug>` создана
- ✅ Коммит: `<type>(<scope>): <subject>`
- ✅ PR создан: [ссылка на PR]
