# Development Context Log

## Последнее обновление
- Дата: 2026-02-27

## Текущий статус
- Этап: Feature-complete + новый вектор — контент-пайплайн + Google Cloud VM.
- Последнее действие: dotfiles-claude репо, Google Cloud VM, Telegram бот, анализ AI Mindset видео.
- Текущий фокус: пайплайн сессии → статья → Telegram канал. Ожидание экспорта Telegram канала с заметками.
- Следующий шаг: получить экспорт @cipher_think_bot канала → проанализировать заметки/аудио → написать пайплайн генерации статей → задеплоить на VM.

## История изменений

### 2026-02-27 — Personal OS v2 + Google Cloud VM + контент-пайплайн (сессия 9)
- Что сделано:
  - Разбор двух AI Mindset видео (Founder OS #22 + POS sprint) — полный анализ субтитров через субагентов
  - Эксперимент: статья из логов сессии 8 ("Как я проверил свой AI-проект на уникальность") — получилось читабельно
  - dotfiles-claude: приватный GitHub репо с настройками ~/.claude/ (CLAUDE.md, aboutme.md, ai-rules, skills, memory)
  - Хук sync-memory.py: MEMORY.md автоматически пушится в dotfiles-claude при завершении сессии
  - Хук pull-dotfiles.py: автопулл dotfiles при старте сессии (1 раз в день)
  - setup.sh: одна команда разворачивает всё на новом компе
  - Google Cloud VM: cortex-vm (e2-small, europe-west3-b, Ubuntu 22.04, IP 34.159.55.61)
  - Cortex склонирован на VM, Python + git установлены
  - Telegram бот @cipher_think_bot подключён к приватному каналу (chat_id: -1001434709177)
  - Токен и chat_id сохранены в .env на VM
- Решения: контент-пайплайн (сессия → статья → Telegram) — следующий конкретный шаг. Нужен Anthropic API ключ на VM.
- Ожидание: экспорт Telegram канала с личными заметками и аудио для анализа.

### 2026-02-26 — Reality check + cleanup (сессия 8)
- Что сделано:
  - idea-reality MCP подключен и протестирован (добавлен в прошлой сессии, заработал после рестарта)
  - Cortex reality check: signal 74/100, прямой конкурент Atman36/personal-assist-orchestrator (0 stars, macOS-only, 1 день работы). Cortex объективно зрелее.
  - Детальное сравнение Cortex vs pcorp: мы — CLI toolkit (cloud-first, cross-platform), они — standalone daemon (macOS, SQLite state)
  - #38 (Remote Control API) — исследовано, закрыто. Это remote desktop для CLI, не API для оркестрации. Dispatch через Issues остаётся.
  - #42 (idea-reality MCP) — закрыто, проверка пройдена.
  - Cipher (OpenClaw агент на VPS 89.19.208.38) — ревью: мёртвый проект, Docker не запущен, workspace-свалка. Всё полезное уже в Cortex.
  - cipher-knowledge репа — уже в архиве на GitHub.
  - VPS Timeweb — решено удалить (не выполняет функций, деньги списываются).
- Решения: Открытых Issues — 0. Cipher закрыт, VPS удаляется. Cortex — единственный активный проект.

### 2026-02-25 — Council + Research + Personal OS (сессия 7)
- Что сделано:
  - /council → сгенерирован спринт из 4 задач (P2-P5, P1 убран — API ключ не нужен)
  - Задиспатчены Jules: #30 (metrics tests), #31 (CONTRIBUTING+LICENSE), #32 (new-project), #33 (heartbeat PH)
  - Jules закрыл 3/4: PR #34 (docs), PR #35 (metrics 99% coverage), PR #36 (scaffold). #33 в работе.
  - AI Mindset дайджест: 8 видео → research/ai-mindset-digest.md (закоммичен)
  - Анализ дневника: 603 записи Obsidian (2022-2026) → aboutme.md (Personal OS foundation)
  - Обсуждение: Obsidian как инфраструктура для AI-агентов (skills, rules, MCP)
  - Personal OS setup: структура AI/ в Obsidian vault (aboutme, rules, skills, knowledge)
  - Симлинки ~/.claude/ → Obsidian vault (aboutme.md, ai-rules/, ai-knowledge/)
  - Глобальный ~/.claude/CLAUDE.md создан — ссылается на aboutme + rules + knowledge
  - Философия в aboutme.md дополнена: эволюция мировоззрения (стоицизм → тёмный поворот → детерминизм), ключевые авторы, главное противоречие
- Решения: ANTHROPIC_API_KEY не нужен. Personal OS v1 настроен — Obsidian = single source of truth через симлинки.

### 2026-02-25 — Sync + финализация (сессия 6)
- Что сделано:
  - Jules завершил все 3 задачи: /quick-commit (PR #27), /metrics (PR #28), README landing (PR #29)
  - DEV_CONTEXT.md обновлён, прогресс синхронизирован
- Решения: Cortex полностью завершён. Все запланированные фичи реализованы.

### 2026-02-24 — Council спринт + cleanup (сессия 5)
- Что сделано:
  - `/learn` — мета-анализ: Jules >> Codex, 0% тестов → 97%, hotspots в heartbeat
  - `/council` — сгенерирован план из 5 задач (P1-P5)
  - Закрыты stale Issues: #7, #10, #13
  - PROJECT_CONTEXT.md — все 6 этапов и DoD отмечены [x] (PR #23)
  - DEV_CONTEXT.md синхронизирован с реальностью (PR #22)
  - Задиспатчены Jules: /quick-commit (#24), /metrics (#25), README (#26)
  - Установлен uv (был не установлен на системе)
- Решения: Cortex feature-complete. Следующий шаг — реальный продукт (фриланс-бот) или open-source launch.

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
- Интеграции: Context7 MCP, Sequential Thinking MCP, Playwright MCP, idea-reality MCP, Codex CLI MCP

## Инвентарь

### Команды (12)
council, dispatch, heartbeat, handoff, status, verify, new-project, screenshot, tdd, build-fix, learn, quick-commit, metrics

### Агенты (4)
architect, code-reviewer, security-auditor, verify-agent

### Хуки (8)
check-secrets, check-filesize, pre-commit-check, protect-main, grab-screenshot, output-secret-filter, mcp-usage-tracker, expensive-tool-warning

### Workflows (3)
heartbeat.yml (cron), code-review.yml (PR review), jules-trigger.yml (auto-trigger)

## Известные проблемы
- Codex не триггерится через Issues — только через chatgpt.com вручную
- Codex плохо справляется с ресёрч/кодовыми задачами — годится для доков/шаблонов
- tools/video/extract.py: баг — хардкодит output dir для URL (workaround: --output flag)

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
- [x] DEV_CONTEXT.md и PROJECT_CONTEXT.md синхронизированы
- [x] Все milestones и DoD выполнены
- [x] Stale Issues закрыты (#7, #10, #13)
- [x] /quick-commit команда (PR #27, Jules)
- [x] /metrics — трекинг агентов (PR #28, Jules)
- [x] README как landing page (PR #29, Jules)
- [x] Metrics tests 99% coverage (PR #35, Jules)
- [x] CONTRIBUTING.md + LICENSE (PR #34, Jules)
- [x] /new-project scaffold (PR #36, Jules)
- [x] Heartbeat + Product Hunt (#33, Jules)
- [x] AI Mindset дайджест (research/ai-mindset-digest.md)
- [x] aboutme.md — персональный контекст (Obsidian vault)
- [x] Personal OS v1: Obsidian vault → симлинки → ~/.claude/ (aboutme, rules, knowledge)
- [x] idea-reality MCP — pre-build проверка идей на уникальность
- [x] Cortex reality check (signal 74, конкурент слабее)
- [x] #38 Remote Control API — исследовано, не подходит для dispatch
- [x] Cipher cleanup — репа в архиве, VPS удаляется
- [x] dotfiles-claude — приватный репо, автосинк памяти между компами
- [x] Google Cloud VM (cortex-vm, e2-small, 34.159.55.61) — задеплоен, Cortex склонирован
- [x] Telegram бот подключён к приватному каналу (chat_id: -1001434709177)
- [ ] Контент-пайплайн: сессия → статья → Telegram (в процессе)
- [ ] Анализ экспорта Telegram канала (заметки + аудио)
- [ ] ~~Фриланс-бот~~ (отложен)

## Идеи / Backlog
- Контент-пайплайн: DEV_CONTEXT → статья через Claude API → Telegram канал (приватный → потом публичный)
- Personal OS v2: Obsidian MCP (поиск по vault в реальном времени)
- Self-improving rules (агент пишет новые правила при ошибках)
- Веб-дашборд для визуализации Issues/PR pipeline
- Open-source launch: r/ClaudeAI, Show HN
