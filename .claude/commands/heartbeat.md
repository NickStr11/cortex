Запусти Heartbeat — сканирование AI/Tech трендов и генерация дайджеста.

## Prerequisites

Перед запуском проверь что .env содержит нужные ключи:
```bash
grep -q "GOOGLE_API_KEY" D:/code/2026/2/cortex/.env && echo "OK: GOOGLE_API_KEY" || echo "MISSING: GOOGLE_API_KEY — нужен для Gemini"
grep -q "GITHUB_TOKEN\|GH_TOKEN" D:/code/2026/2/cortex/.env && echo "OK: GITHUB_TOKEN" || echo "OPTIONAL: GITHUB_TOKEN — для GitHub trending (работает и без)"
```
Если GOOGLE_API_KEY отсутствует — скажи пользователю и останови.

## Инструкция

### Шаг 1 — Сбор данных

Выполни Python-скрипт для сбора трендов:

```bash
export PATH="/c/Users/User/.local/bin:$PATH" && cd /d/code/2026/2/cortex/tools/heartbeat && uv run python main.py --mode fetch
```

Скрипт выведет сырые данные: топ посты Hacker News, трендовые репозитории GitHub.

### Шаг 2 — Контекст

Прочитай CURRENT_CONTEXT.md чтобы понять текущие проекты и интересы.

### Шаг 3 — Анализ

На основе сырых данных и контекста проекта:
1. Выдели 5-10 самых релевантных трендов
2. Объясни почему каждый тренд важен (1 предложение)
3. Предложи конкретные задачи для /dispatch

### Шаг 4 — Вывод

Формат:

```
## Heartbeat [дата]

### Тренды
1. **[Trend]** — [почему важно] ([ссылка])
   - Actionable: [задача для агента]

### Рекомендуемые действия
- [ ] [задача для /dispatch] (агент: Jules/Codex, размер: S/M/L)

### Источники
- HN: X постов проанализировано
- GitHub: Y репозиториев
```
