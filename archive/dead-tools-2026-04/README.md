<!-- L0: Архив мёртвых tools, перенесено 2026-04-16 -->
# Dead tools — 2026-04

Инструменты, перенесённые из `tools/` в архив. Функция заменена или никогда не запускалась всерьёз.

## heartbeat/
Сканер AI/tech трендов → формировал дайджесты. GitHub workflow удалён в `891694d`. Заменён на TG daily digest (systemd timer на VM, 03:00 UTC). Последний live-апгрейд: `5caab06`.

**Зачем сохранён:** рабочий код источников/форматера, эталон при переделке digest.

## pipeline/
Контент-пайплайн Gemini 3 Flash → Telegram (PR #47, `d4dd3c1`). Заменён связкой `tg-monitor` + `tg-pharma`. Осталось 2 файла: `main.py`, `pyproject.toml`.

**Зачем сохранён:** для истории, если понадобится простой AI→TG pipeline.

## scaffold/
Была пустая (только `.venv/` в gitignore). Удалена полностью, не в архиве.

---

**Восстановить:** `git mv archive/dead-tools-2026-04/<tool> tools/<tool>`
