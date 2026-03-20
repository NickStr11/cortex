Запусти полную проверку качества кода по docs/verify.md.

## Шаги

1. **Tests**: `bash scripts/ops.sh test`
2. **Lint**: `bash scripts/ops.sh lint`
3. **Types**: `bash scripts/ops.sh check`
4. **Secrets**: `bash scripts/ops.sh secrets`
5. **Diff**: `git diff --stat`

Каждый шаг — запусти команду, собери результат.
Если тесты падают — СТОП, предложи фикс.
Lint/types warnings допустимы, errors — нет.

В конце выведи:

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
