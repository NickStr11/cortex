---
paths: tools/**/*.py
---

# Python tools

- Каждый tool — самодостаточный: свой `pyproject.toml`, `.venv`, зависимости.
- `uv` для зависимостей, `uv run` для запуска. Без глобальных pip install.
- `beartype` для runtime type checking на публичных функциях.
- Строгий pyright: `from __future__ import annotations` в каждом файле.
- Импорты: stdlib → third-party → local. ruff сортирует автоматически.
- Запуск: `cd tools/<tool> && uv sync && uv run python main.py`
- Подробнее: `docs/python-rules.md`
