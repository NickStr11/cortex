# Git Flow Workflow

Стандартный Git-воркфлоу для проектов.

## 1. Инициализация репозитория

```bash
git init
git add .
git commit -m "init: project scaffold"
```

## 2. Conventional Commits

Формат коммитов: `<type>(<scope>): <description>`

| Type | Когда |
|------|-------|
| `feat` | Новый функционал |
| `fix` | Баг-фикс |
| `refactor` | Рефакторинг без изменения поведения |
| `docs` | Документация |
| `style` | Форматирование, пробелы |
| `test` | Тесты |
| `chore` | Конфиг, зависимости, CI |
| `init` | Начальная инициализация |

**Примеры:**
```bash
git commit -m "feat(auth): add Google OAuth login"
git commit -m "fix(api): handle null response from supplier"
git commit -m "refactor(db): extract query builder into separate module"
git commit -m "docs: update README with setup instructions"
```

## 3. Branch Naming

Формат: `<type>/<short-description>`

```bash
git checkout -b feat/google-oauth
git checkout -b fix/null-supplier-response
git checkout -b refactor/query-builder
```

## 4. Рабочий цикл

```bash
# 1. Создать ветку
git checkout -b feat/new-feature

# 2. Работать, коммитить часто
git add -A
git commit -m "feat(module): add basic structure"

# 3. Перед мержем — проверить (docs/verify.md)

# 4. Мерж в main
git checkout main
git merge feat/new-feature
git branch -d feat/new-feature
```

## 5. Pre-commit проверки

Перед каждым коммитом убедиться:

```bash
# Нет debug statements
grep -rn "console.log\|print(" --include="*.py" --include="*.ts" --include="*.js" src/ 2>/dev/null

# Нет секретов
grep -rn "sk-\|api_key\|password=" --include="*.py" --include="*.ts" --include="*.js" . 2>/dev/null

# Нет TODO/FIXME в коммите (опционально)
grep -rn "TODO\|FIXME\|HACK" --include="*.py" --include="*.ts" . 2>/dev/null | head -10
```

## 6. Полезные команды

```bash
# Последние коммиты
git log --oneline -10

# Что изменилось
git diff --stat

# Откатить последний коммит (сохранив изменения)
git reset --soft HEAD~1

# Stash (отложить изменения)
git stash
git stash pop

# Интерактивный rebase (склеить коммиты)
git rebase -i HEAD~3
```

## 7. .gitignore

Убедись что `.gitignore` содержит:
- `.env`, `.env.*`
- `*-credentials*.json`, `*.pem`, `*.key`
- `__pycache__/`, `node_modules/`
- `.venv/`, `venv/`
- IDE файлы (`.idea/`, `.vscode/`)
