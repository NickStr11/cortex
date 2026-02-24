# Development Context Log

## Последнее обновление
- Дата: 2026-02-24

## Текущий статус
- Этап: MVP завершён + forge-port. Система полностью рабочая.
- Последнее действие: Портированы хуки, агент и команды из claude-forge. Jules написал тесты (97% coverage).
- Следующий шаг: /council для планирования следующего спринта или новый проект (фриланс-бот)

## История изменений

### 2026-02-24 — Heartbeat + forge-port + тесты (сессия 4)
- Что сделано:
  - Heartbeat модуль: Python-скрипт сканирует HN + GitHub Trending + Reddit
  - `/heartbeat` slash-команда для ручного запуска
  - `.github/workflows/heartbeat.yml` — cron каждые 3 дня
  - Первый запуск heartbeat: 6 HN постов, 15 GitHub репо
  - Auto-review PR: `.github/workflows/code-review.yml` (Jules, PR #14)
  - Forge-port: 3 хука, 1 агент, 3 команды из claude-forge (PR #19)
  - Jules добавил Reddit в heartbeat (PR #18)
  - Jules написал тесты для heartbeat: 97% coverage (PR #21)
  - `/learn` — мета-анализ: Jules >> Codex для кодовых задач
- Решения: Codex плохо справляется с ресёрч-задачами, Jules надёжнее для кода.

### 2026-02-23 — Тест Codex + исследование рынка (сессия 3)
- Что сделано:
  - Протестирован Codex через chatgpt.com — полный цикл за 1м 45с (PR #8)
  - Собран дайджест по AI-агентам (Codex/Jules/Devin/Claude Code/Cursor/Aider)
  - Зафиксирован паттерн "AI-корпорация" через GitHub Issues

### 2026-02-23 — Исследование и инициализация (сессия 2)
- Что сделано:
  - Исследован референс-воркфлоу "Персональная Корпорация"
  - Скопирован шаблон → D:\code\2026\2\cortex
  - PROJECT_CONTEXT.md заполнен
  - /council и /dispatch команды созданы
  - GitHub Apps подключены (Jules + Codex)
  - AGENTS.md, gh CLI авторизован
  - Первый полный цикл: Issue #2 → Jules → PR → Merge

## Технические детали
- Архитектура: CLI команды → GitHub Issues → AI агенты (Jules/Codex) → PR → Human merge
- Стек: Python 3.12, uv, beartype, Claude Code CLI, GitHub Actions
- Интеграции: Context7 MCP, Sequential Thinking MCP, Playwright MCP

## Инвентарь

### Команды (10)
council, dispatch, heartbeat, handoff, status, verify, new-project, screenshot, tdd, build-fix, learn

### Агенты (4)
architect, code-reviewer, security-auditor, verify-agent

### Хуки (8)
check-secrets, check-filesize, pre-commit-check, protect-main, grab-screenshot, output-secret-filter, mcp-usage-tracker, expensive-tool-warning

### Workflows (3)
heartbeat.yml (cron), code-review.yml (PR review), jules-trigger.yml (auto-trigger)

## Известные проблемы
- Codex не триггерится через Issues — только через chatgpt.com вручную
- ANTHROPIC_API_KEY не добавлен в GitHub Secrets (heartbeat cron и code-review не работают)
- Codex плохо справляется с ресёрч/кодовыми задачами — годится для доков/шаблонов

## Прогресс
- [x] /council — AI-консилиум
- [x] /dispatch — создание Issues с назначением агентов
- [x] GitHub Apps (Jules + Codex)
- [x] AGENTS.md
- [x] gh CLI авторизован
- [x] Первый цикл: Issue → Jules → PR → Merge
- [x] Codex протестирован (PR #8)
- [x] Heartbeat — авто-ресёрч трендов (HN + GitHub + Reddit)
- [x] Auto-review PR (code-review.yml)
- [x] Forge-port: хуки, агент, команды
- [x] Тесты heartbeat (97% coverage)
- [ ] ANTHROPIC_API_KEY в GitHub Secrets
- [ ] Фриланс-бот (новый проект)

## Идеи / Backlog
- Веб-дашборд для визуализации Issues/PR pipeline
- AutoGen AGENTS.md через DSPy
- /quick-commit команда
- Heartbeat v3: больше источников (Product Hunt, AI блоги)
