# Development Context Log

## Последнее обновление
- Дата: 2026-03-01

## Текущий статус
- Этап: TG Bridge — Telegram → Claude Code бридж работает.
- Последнее действие: сессия 13 — tg-bridge написан и протестирован, dotfiles-claude синкнут.
- Текущий фокус: tg-bridge (управление Claude Code с телефона через Telegram бота).
- Следующий шаг: анализ экспорта Telegram канала (заметки + аудио).

## История изменений

### 2026-03-01 — TG Bridge + SVG эксперименты (сессия 13)
- Что сделано:
  - tools/tg-bridge/main.py — Telegram → Claude Code бридж через long polling
  - Бот @cipher_think_bot принимает сообщения, прокидывает в `claude -p`, возвращает ответ
  - Whitelist по user_id (691773226), история 20 сообщений (history.json), /new для сброса
  - Фиксы: Windows encoding (PYTHONIOENCODING=utf-8), nested session (unset CLAUDECODE env)
  - dotfiles-claude синкнут с текущим ~/.claude/ (aboutme, ai-knowledge обновлены, push)
  - Эксперимент: image → SVG конвертация (vtracer, Inkscape CLI trace). Inkscape 64-scan лучший результат для сложных лого, но автотулы не тянут разбивку на семантические объекты
  - Inkscape установлен через winget (1.4.3)
- Решения: `claude -p` без `--continue` (конфликтует с интерактивной сессией), вместо этого ручная history.json. Автоматический трейсинг упирается в потолок на сложных иллюстрациях — нужен Gemini 3.1 Pro или ручная работа.

### 2026-03-01 — Telethon авторизован + дайджесты в продакшне (сессия 12)
- Что сделано:
  - Telethon авторизован через QR-код (из PowerShell пользователя). Блокер решён!
  - Сессия cortex_userbot.session создана и загружена на VM
  - Первый дайджест vibecod3rs: 1494 сообщения → Claude субагент (GOOGLE_API_KEY был просрочен)
  - Новый GOOGLE_API_KEY получен, Gemini digest работает
  - /tg-digest скилл создан (Telethon fetch → Gemini analysis → .md в канал)
  - Группа Вайбкодеры добавлена в config.py (vibecod3rs)
  - AI Mindset: username не работал → заменён на числовой ID (-1001497220445)
  - digest.py/daily.py: дайджест отправляется как .md файл (sendDocument), не текстом
  - Systemd timer: 03:00 UTC (06:00 MSK), обе группы фетчатся
  - VM: .env почищен от комментариев, все файлы синхронизированы
  - PharmOrder: улучшен поиск (multi-word fallback: "нурофен леди" → "Нурофен экспресс леди")
  - Создан .docx с заявкой для аптеки, отправлен маме в TG
- Решения: QR-авторизация > код (коды Telegram не доставлялись). Gemini > Claude для дайджестов (экономия токенов). .md файл > текст (нет лимита 4096 символов).

### 2026-03-01 — TG Monitor написан (сессия 11)
- Что сделано:
  - tools/tg-monitor/monitor.py — Telethon userbot, читает сообщения из TG-групп, сохраняет в JSON
  - tools/tg-monitor/digest.py — дайджест через Gemini, отправка в Telegram
  - tools/tg-monitor/config.py — список групп, фильтры по длине и ключевым словам
  - tools/tg-monitor/daily.py — объединяет heartbeat + tg-monitor в один запуск
  - tools/tg-monitor/deploy/ — systemd service + timer + setup-vm.sh
  - .gitignore обновлён — data/tg-groups/ и *.session исключены
- Блокер: Telethon auth — коды не приходили (решён в сессии 12 через QR).

### 2026-02-28 — Контент-пайплайн запущен (сессия 10)
- Что сделано:
  - PR #46 смержен (сессия 9 docs), разрешены конфликты с Agent-Reach из main
  - tools/pipeline/main.py — написан пайплайн DEV_CONTEXT → Gemini 3 Flash → Telegram
  - Gemini 3 Flash (gemini-3-flash-preview) — заменил Anthropic API (ключа нет)
  - GitHub Actions pipeline.yml — триггер на push DEV_CONTEXT.md в main
  - GitHub Secrets: GOOGLE_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
  - Пайплайн протестирован локально и через Actions — посты уходят в канал
  - Гайд "Новый комп за 5 минут" отправлен в Telegram (message_id=830)
  - Разобрались что VM нужна только для 24/7 бота, для пайплайна — не нужна
  - Изучили подход Серёжи Риса (sereja.tech) — публичный блог Hugo+Vercel, 82 статьи
- Решения: GitHub Actions > VM cron для пайплайна. GOOGLE_API_KEY вместо ANTHROPIC_API_KEY.
- Ключи в чате засвечены — перегенерить GOOGLE_API_KEY и TELEGRAM_BOT_TOKEN.

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

### 2026-02-26 — Reality check + cleanup + Research Agent-Reach (сессия 8)
- Что сделано:
  - idea-reality MCP подключен и протестирован (добавлен в прошлой сессии, заработал после рестарта)
  - Cortex reality check: signal 74/100, прямой конкурент Atman36/personal-assist-orchestrator (0 stars, macOS-only, 1 день работы). Cortex объективно зрелее.
  - Детальное сравнение Cortex vs pcorp: мы — CLI toolkit (cloud-first, cross-platform), они — standalone daemon (macOS, SQLite state)
  - #38 (Remote Control API) — исследовано, закрыто. Это remote desktop для CLI, не API для оркестрации. Dispatch через Issues остаётся.
  - #42 (idea-reality MCP) — закрыто, проверка пройдена.
  - Cipher (OpenClaw агент на VPS 89.19.208.38) — ревью: мёртвый проект, Docker не запущен, workspace-свалка. Всё полезное уже в Cortex.
  - cipher-knowledge репа — уже в архиве на GitHub.
  - VPS Timeweb — решено удалить (не выполняет функций, деньги списываются).
  - Исследован проект Agent-Reach (1.7k stars): Zero API fees подтверждено (скрейпинг, cookies, free tiers)
  - Вердикт по Agent-Reach: полная замена нецелесообразна, точечная интеграция (Jina Reader, bird CLI)
  - Отчет: research/agent-reach-analysis.md
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
- Inkscape 1.4.3 установлен (winget), доступен для CLI trace bitmap

## Инвентарь

### Команды (14)
council, dispatch, heartbeat, handoff, status, verify, new-project, screenshot, tdd, build-fix, learn, quick-commit, metrics, tg-digest, daily

### Агенты (4)
architect, code-reviewer, security-auditor, verify-agent

### Хуки (8)
check-secrets, check-filesize, pre-commit-check, protect-main, grab-screenshot, output-secret-filter, mcp-usage-tracker, expensive-tool-warning

### Tools (4)
heartbeat (HN/Reddit/GitHub trends), pipeline (DEV_CONTEXT → article → Telegram), tg-monitor (TG groups → digest → Telegram), tg-bridge (Telegram → Claude Code bridge)

### Workflows (4)
heartbeat.yml (cron), code-review.yml (PR review), jules-trigger.yml (auto-trigger), pipeline.yml (DEV_CONTEXT → Telegram)

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
- [x] Research: Agent-Reach (research/agent-reach-analysis.md)
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
- [x] Контент-пайплайн: DEV_CONTEXT → Gemini 3 Flash → Telegram (PR #47, pipeline.yml)
- [x] TG Monitor: Telethon userbot + Gemini digest + daily runner (tools/tg-monitor/)
- [x] Systemd timer для daily digest на VM (deploy/cortex-daily.timer)
- [x] Telethon авторизован (QR), сессия на VM, дайджесты работают
- [x] GOOGLE_API_KEY обновлён
- [x] /tg-digest скилл
- [x] TG Bridge: Telegram → Claude Code через @cipher_think_bot (tools/tg-bridge/)
- [x] dotfiles-claude синкнут с текущим состоянием
- [ ] Перегенерить TELEGRAM_BOT_TOKEN (засвечен в чате)
- [ ] Анализ экспорта Telegram канала (заметки + аудио)
- [ ] ~~Фриланс-бот~~ (отложен)

## Идеи / Backlog
- Контент-пайплайн: DEV_CONTEXT → статья через Claude API → Telegram канал (приватный → потом публичный)
- Personal OS v2: Obsidian MCP (поиск по vault в реальном времени)
- Self-improving rules (агент пишет новые правила при ошибках)
- Веб-дашборд для визуализации Issues/PR pipeline
- Open-source launch: r/ClaudeAI, Show HN
