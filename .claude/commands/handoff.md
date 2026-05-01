Сохрани прогресс сессии перед закрытием.

Diary и CURRENT_CONTEXT живут в **per-user shared folder**, общем для всех worktree, НЕ в git:
- `~/.claude/projects/D--code-2026-2-cortex/memory/diary/`
- `~/.claude/projects/D--code-2026-2-cortex/CURRENT_CONTEXT.md`

Из git-bash на Windows: `/c/Users/User/.claude/projects/D--code-2026-2-cortex/...`

Шаги:

1. Запиши дневниковую запись (выполни всё из `/diary`) — это ТВОЯ запись за этот чат
2. Прочитай **последние 5 файлов** в `~/.claude/projects/D--code-2026-2-cortex/memory/diary/` (включая только что созданный):
   - Если другие чаты тоже сегодня писали — там их записи (без коллизий, общая папка)
   - Используй для понимания общего контекста при обновлении CURRENT_CONTEXT
3. Обнови `~/.claude/projects/D--code-2026-2-cortex/CURRENT_CONTEXT.md` на основе агрегации:
   - **Текущий фокус** — что активно во ВСЕХ треках (не только своём)
   - **Ближайшие шаги** — объедини из всех diary, не затирай чужое
   - **Ссылки** — если появились новые в любом diary
   - Если конфликт статусов — поверь более свежему diary (бо́льший номер = позднее)
4. **НЕ коммить в git** — diary и CURRENT_CONTEXT теперь не версионируются (per-user). Файлы просто на диске.
5. **Skill scan если прошло 7+ дней:**
   - Проверь `runtime/cache/last-skill-scan.txt` (timestamp последнего скана)
   - Если файла нет ИЛИ прошло 7+ дней:
     - Прогони `python scripts/scan-skills.py > runtime/skill-scans/YYYY-MM-DD.md` (создай папку если надо)
     - Запиши текущую дату в `runtime/cache/last-skill-scan.txt`
     - В CURRENT_CONTEXT добавь короткий пункт «Skill scan сделан: stale=X, broken-refs=Y» если нашлось что-то новое
   - Если меньше 7 дней — пропускай молча
6. Скажи: «Можно делать /clear. Последний diary: NNN. Треков подхвачено: X.»

## Правила агрегации

- Не затирай чужие пункты в CURRENT_CONTEXT — только дополняй и актуализируй
- Если два чата делали одну задачу — слей оба diary в один пункт, укажи оба источника
- Параллельно запущенные `/handoff` — race возможен. Если CURRENT_CONTEXT.md изменён <30 сек назад — перечитай свежую версию перед записью.
