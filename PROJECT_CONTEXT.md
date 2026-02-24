# PROJECT_CONTEXT

## Проект
- Название: Cortex
- Цель: Персональная AI-корпорация — система оркестрации AI-агентов (Claude, Codex, Jules) через GitHub Issues. Консилиум AI-ролей планирует задачи, dispatch раскидывает по агентам, человек только мержит PR.

## Стек
- Orchestration: Claude Code CLI (основной мозг)
- Agents: OpenAI Codex (GitHub App), Google Jules (GitHub App), Claude Code Action
- PM: GitHub Issues + Projects (план-доска)
- Infrastructure: GitHub Actions (CI/CD, auto-review)

## Доступные ресурсы
- Claude Code — API подписка (Opus 4.6)
- ChatGPT Pro ($200/мес) — Codex включён (300-1500 задач/5ч)
- Jules — бесплатный тир
- Devin — пока не подключаем ($500/мес)

## Архитектура

```
/council (Claude CLI)
    ├── CPO agent → продуктовые задачи
    ├── CTO agent → технические задачи
    ├── CMO agent → маркетинг/growth
    └── Growth agent → метрики, эксперименты
         │
         ▼
GitHub Issues (план-доска)
         │
/dispatch (Claude CLI)
    ├── @codex → простые/средние таски
    ├── jules label → баги, рефакторинг
    └── claude-code-action → PR review
         │
         ▼
Pull Requests → Human merges ✓
```

## Этапы
1. [x] `/council` — slash-команда для AI-консилиума (роли, промпты, сводка)
2. [x] `/dispatch` — создание GitHub Issues с назначением агентов
3. [x] GitHub Apps — подключить Codex + Jules к репо
4. [x] GitHub Actions — claude-code-action для auto-review PR
5. [x] Heartbeat — авто-ресёрч AI/Tech трендов (HN + GitHub + Reddit → cron каждые 3 дня)
6. [x] Forge-port — хуки, агент, команды из claude-forge

## Definition of Done
- [x] `/council` генерирует задачи из PROJECT_CONTEXT.md
- [x] `/dispatch` создаёт Issues с правильными labels/assignees
- [x] Хотя бы один агент (Codex или Jules) успешно делает PR по issue
- [x] Полный цикл: план → issue → PR → merge
