# Development Context Log

> Последние записи. Архив до 03-16: `archive/dev-context-pre-mar16.md`

## 2026-03-19 — Дайджест-ревью + Generative-UI MCP

### Что сделано

**Дайджест 18.03 — разбор:**
- Прочитали дайджест за 18.03 через `journalctl -u cortex-daily.service` на VM
- Три блока: Heartbeat (GitHub/HN/PH), FUNDthe (крипта), Вайбкодеры
- Ресёрч трёх тем из дайджеста через Exa

**Codex Subagents (ресёрч):**
- GA с 16.03. Кастомные агенты через TOML в `~/.codex/agents/`, параллельное выполнение
- Концептуально = наш Agent tool + skills. Плюс Codex — выбор модели (spark для мелочи)
- Вывод: подтверждает наш подход, ничего нового для внедрения

**Generative-UI-MCP (установлен):**
- `claude mcp add generative-ui -- npx generative-ui-mcp` — добавлен в локальный конфиг
- MCP сервер для on-demand загрузки дизайн-гайдлайнов (chart, diagram, mockup, art, interactive)
- Дополняет `tools/ui-ux/` (стили/палитры) чартами и SVG-визуализациями

**justdoit скилл (ресёрч):**
- serejaris/justdoit (28 stars) — execution pack для Codex. Аналог superpowers brainstorm→plan→execute
- Скип, у нас уже покрыто. Но `ris-claude-code` (119 stars) можно глянуть при случае

**Memory:**
- Сохранён feedback `digest-lookup.md` — дайджест искать через journalctl на VM, не локально

### Решения
- Generative-UI-MCP — добавить (дополняет ui-ux для dashboard-проектов)
- Codex Subagents — не внедрять, наш подход эквивалентен
- justdoit — скип

---

## 2026-03-18 — OpenClaw аудит + Superpowers + Skills upgrade

### Что сделано

**OpenClaw второй ноут — аудит и ресёрч:**
- Проверили nickCodex-READY repo (ветка `codex/openclaw-second-laptop-setup`): структура, скрипты, документация
- Ресёрч OpenClaw экосистемы через Exa: memory plugins, subagents, Telegram routing, persona drift
- Аудит текущей native Windows схемы → рекомендация мигрировать в WSL2 (gateway структурно сломан на native Windows: orphan processes, PATH freeze, Scheduled Task hangs)
- Топовые memory plugins: Supermemory (603 stars, cloud), Hindsight (self-hosted, auto-inject), Mem0 (self-hosted, semantic)
- Persona drift — известная проблема (issue #43295), не решена в ядре

**Claude Code — 3 апгрейда:**
1. **Superpowers v5.0.5** — установлен как plugin через marketplace (`claude plugin install superpowers@superpowers-marketplace`). 14 skills: brainstorming, writing-plans, executing-plans, TDD, code-review, verification, git-worktrees, и др.
2. **Agent Teams** — уже был включён (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`)
3. **anthropics/skills** — добавлены pdf, xlsx, docx из официального repo (96K stars)

**Cleanup:**
- Удалены 4 дублирующих skill: `systematic-debugging`, `subagent-dev`, `parallel-agents` (заменены superpowers plugin), `skill-creator` (дублирует skill-forge)
- Итого: 14 custom skills + 14 superpowers plugin = 28 total (sweet spot 20-30)

### Решения
- Superpowers — plugin, не копия файлов. Обновляется через `claude plugin update superpowers`
- Hindsight > Supermemory для Клешни (self-hosted, без vendor lock)
- Native Windows OpenClaw → мигрировать в WSL2 при первых проблемах (WSL-MIGRATION.md готов)
- claw-memory — отдельный GitHub repo для памяти Клешни, не мешать с bootstrap repo

### Клонированные repo (D:\code\2026\3\)
- `superpowers/` — obra/superpowers v5.0.5 (reference, plugin установлен отдельно)
- `anthropics-skills/` — anthropics/skills (source для pdf/xlsx/docx)
- `nickCodex-READY/` — ветка codex/openclaw-second-laptop-setup

---

## 2026-03-16 — Skill Forge + 4 новых скилла + видео-анализ

### Что сделано

**Skill Forge** — мета-скилл для генерации других скиллов:
- `.claude/skills/skill-forge/SKILL.md` — 5-шаговый процесс: Parse Intent → Exa Research (3 параллельных поиска) → Distill → Generate SKILL.md → Confirm
- Quality gates: 3+ code blocks, 3+ common issues, no placeholders
- Концепция "Спецназ" из видео Founder OS #21: дать агенту контекст через Exa перед задачей

**4 скилла сгенерированы параллельно через skill-forge паттерн:**
- `.claude/skills/crewai-agents/SKILL.md` — 606 строк, 30 code blocks. Мульти-агент команды с ролями.
- `.claude/skills/langgraph-agents/SKILL.md` — 596 строк, 23 code blocks. Граф-based воркфлоу с условными переходами.
- `.claude/skills/autoresearch/SKILL.md` — автономные ML-эксперименты (Karpathy). 3-файловая архитектура.
- `.claude/skills/gsd-method/SKILL.md` — 382 строки. Spec-driven разработка для Claude Code.

**Видео-анализ (Founder OS #21)**:
- YouTube `MAzH18vpVFM` — AI Mindset community, Саша Павляев + Александр (infra engineer)
- Анализ через NotebookLM (yt-dlp заблокирован bot detection)
- Темы: Skills + MCP "Спецназ", CloudMem (SQLite persistent memory), personal AI OS

**Ресёрч GitHub AI трендов** (через Exa):
- OpenClaw 210K+, OpenCode 122K, autoresearch 37K, DeerFlow 25K, Hive 9.5K
- Фреймворки: CrewAI 44.6K, LangGraph 25K, Pydantic AI 15K
- Методы: GSD, BMAD, Ralph Loop, Claude Flow/Ruflo

**Claude-Mem исследование**:
- 22K+ stars, thedotmack, TypeScript + SQLite + Bun
- На Windows проблемы (Bun, пути, systemd). Текущий MEMORY.md достаточен.

### Решения
- Exa MCP подтверждён как основной инструмент семантического поиска (лучше WebSearch для AI/dev тем)
- Claude-Mem — отложен, текущая memory система достаточна
- NotebookLM — не MCP, а skill (`/notebooklm`), CLI `notebooklm-py` v0.3.3

---

## 2026-03-13 — tg-pharma fixes + PharmOrder inventory panel

**tg-pharma:**
- Перевели на отдельный бот `@pharmorder_ops_bot` (не шарит токен с рабочим ботом заказов)
- Ужесточили write detection: read-like фразы не угоняют write-команды в `purchase_stats`
- Направление: structured extraction + constraint resolver + verifier вместо патчинга фраз по одной

**PharmOrder inventory panel (VPS):**
- `min_qty per item`: `setInvMin` сохраняет через `/api/inventory/set-min` API (раньше localStorage)
- `invEditMin` переписан — in-place DOM swap, без `loadInventory()`
- Qty input ширина: 36px → 48px
- Stats badge: `invCount` = все позиции, `invStats` = "X позиц. · Y в наличии · Z шт."
- Root cause qty not saving: `invQuickSet` вызывал `loadInventory()` → перерисовка DOM уничтожала значения. Заменено на `_refreshInvStats()`
- Garbled toasts ('????') → нормальный русский текст

---

## 2026-03-12 — PharmOrder EAN override + tg-pharma batch

**EAN override mechanism:**
- Проблема: EAN `4670033321227` (Азитромицин) записан под неверным `id_name=449780` (Цетиризин)
- Fix: `/opt/pharmorder/src/data/ean_overrides.json` — JSON с патчами по EAN+supplier
- `db.py` → `apply_ean_overrides()` после каждого синка
- Ручной патч-лист, добавляется по мере обнаружения

**tg-pharma batch mode:**
- Batch mode: accumulate inventory tasks → apply as one confirmed batch
- New intents: `start_batch`, `stop_batch`, `show_batch`, `apply_batch`, `clear_batch`
- Runtime fix: убиты дубли процессов (409 Conflict)

---

## 2026-03-11 — tg-pharma bot_refs

- Переход с heavy `bot_analytics.db` на lightweight `bot_refs.db`
- Builder: `tools/tg-pharma/build_refs.py`
- 91,335 names, 90,693 makers, 22,019 alias rows, 29.9 MB
- `BotRefsClient` для identity/alias resolution, `bot_analytics.db` = legacy fallback
