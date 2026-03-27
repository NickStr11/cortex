<!-- L0: Чеклист верификации — тесты, линт, секреты, pyright перед коммитом -->
# Verification Workflow

Комплексная проверка качества кода перед коммитом/PR.

## Quick Run

```bash
bash scripts/ops.sh test      # тесты (heartbeat, metrics)
bash scripts/ops.sh lint      # ruff lint все tools
bash scripts/ops.sh check     # pyright typecheck
bash scripts/ops.sh secrets   # секреты в tracked files
```

## Steps

1. **Tests**: `bash scripts/ops.sh test`
   - Если тесты падают — СТОП, чинить.

2. **Lint**: `bash scripts/ops.sh lint`
   - ruff check по всем активным tools
   - Автофикс: `uv run ruff check --fix .` внутри конкретного tool

3. **Types**: `bash scripts/ops.sh check`
   - pyright strict по всем tools
   - Допустимо: warnings. Недопустимо: errors.

4. **Secrets**: `bash scripts/ops.sh secrets`
   - Проверка на утечки API-ключей в tracked files
   - Должно быть "Clean."

5. **Diff Review**: `git diff --stat`
   - Глазами проверить что изменилось

## Output

```
VERIFICATION REPORT
===================
Tests:     [PASS/FAIL] (X passed)
Lint:      [PASS/FAIL] (X issues)
Types:     [PASS/FAIL] (X errors)
Secrets:   [PASS/FAIL]
Diff:      [X files changed]

Overall:   [READY/NOT READY]
```

## When to Use

- `/verify` — запускает этот workflow
- Перед PR
- После рефакторинга
- При `/handoff` если были значимые изменения кода
