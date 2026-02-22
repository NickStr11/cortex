# Verification Workflow

Комплексная проверка качества кода.

## When to Use

- После завершения фичи
- Перед PR
- После рефакторинга

## Steps

1. **Build Check**: Run project build command
   ```bash
   npm run build 2>&1 | tail -20
   ```

   If build fails, STOP and fix errors.

2. **Type Check**: Verify type safety

   **TypeScript**:
   ```bash
   npx tsc --noEmit 2>&1 | head -30
   ```

   **Python**:
   ```bash
   pyright . 2>&1 | head -30
   ```

3. **Lint Check**: Check code style

   **JavaScript/TypeScript**:
   ```bash
   npm run lint 2>&1 | head -30
   ```

   **Python**:
   ```bash
   ruff check . 2>&1 | head -30
   ```

4. **Test Suite**: Run tests with coverage

   **JavaScript/TypeScript**:
   ```bash
   npm run test -- --coverage 2>&1 | tail -50
   ```

   **Python**:
   ```bash
   pytest --cov=. --cov-report=term 2>&1 | tail -50
   ```

   Target: 80% minimum coverage

5. **Security Scan**: Check for common issues

   **Check for debug statements**:
   ```bash
   # JavaScript/TypeScript
   grep -rn "console.log" --include="*.ts" --include="*.tsx" src/ 2>/dev/null | head -10

   # Python
   grep -rn "print(" --include="*.py" . 2>/dev/null | head -10
   ```

   **Check for secrets**:
   ```bash
   grep -rn "sk-" --include="*.ts" --include="*.js" --include="*.py" . 2>/dev/null | head -10
   grep -rn "api_key" --include="*.ts" --include="*.js" --include="*.py" . 2>/dev/null | head -10
   ```

6. **Diff Review**: Show what changed
   ```bash
   git diff --stat
   git diff HEAD~1 --name-only
   ```

## Output

After running all phases, produce a verification report:

```
VERIFICATION REPORT
==================

Build:     [PASS/FAIL]
Types:     [PASS/FAIL] (X errors)
Lint:      [PASS/FAIL] (X warnings)
Tests:     [PASS/FAIL] (X/Y passed, Z% coverage)
Security:  [PASS/FAIL] (X issues)
Diff:      [X files changed]

Overall:   [READY/NOT READY] for PR

Issues to Fix:
1. ...
2. ...
```

## Notes

- Fix issues as they appear before moving to next phase
- Target 80% test coverage minimum
- Remove all debug statements before committing
