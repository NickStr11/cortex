#!/usr/bin/env python3
"""Cortex Scaffolder — Create a new project from the Cortex template.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime

from beartype import beartype

PROJECT_CONTEXT_TEMPLATE = """# PROJECT_CONTEXT

## Проект
- Название: {name}
- Цель: {description}

## Стек
- Orchestration: Claude Code CLI
- Agents: Jules, Codex
- PM: GitHub Issues
- Infrastructure: GitHub Actions
- Stack details: {stack}

## Архитектура
(Describe your architecture here)

## Этапы
1. [ ] Инициализация проекта
2. [ ] Определение базовой архитектуры

## Definition of Done
- [ ] Фича протестирована
- [ ] PR создан и подтверждён
"""

DEV_CONTEXT_TEMPLATE = """# Development Context Log

## Последнее обновление
- Дата: {date}

## Текущий статус
- Этап: Инициализация
- Последнее действие: Проект создан из Cortex шаблона
- Следующий шаг: Настроить PROJECT_CONTEXT.md

## История изменений

### {date} — Инициализация
- Что сделано:
  - Проект развернут из шаблона Cortex
- Решения: Использование Cortex для оркестрации AI-агентов.

## Технические детали
- Архитектура:
- Стек: {stack}

## Прогресс
- [x] Инициализация из шаблона
- [ ] Настроить PROJECT_CONTEXT.md
"""

README_TEMPLATE = """# {name}

{description}

---

## 🚀 Quick Start

1.  **Start the engine**:
    Launch [Claude Code](https://claude.ai/code) in the project root.
2.  **Run your first Council**:
    ```bash
    /council
    ```
3.  **Dispatch tasks**:
    ```bash
    /dispatch
    ```

---

## 🛠 Features (Powered by Cortex)
- Multi-agent orchestration via GitHub Issues.
- Automated trend scanning with `/heartbeat`.
- Built-in safety hooks and CI/CD workflows.

## 📝 License
This project is open-source.
"""

@beartype
def ignore_files(path: str, names: list[str]) -> list[str]:
    ignored = {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        ".env",
        "video_output",
        "init-project.sh",
    }
    to_ignore = [
        name for name in names
        if name in ignored
        or name.endswith(".pyc")
        or name.endswith(".log")
        or (name.endswith(".json") and name not in {".mcp.json", "settings.json"})
    ]

    # Specifically ignore tools/scaffold to keep the template clean
    if os.path.basename(path) == "tools" and "scaffold" in names:
        to_ignore.append("scaffold")

    return to_ignore

@beartype
def scaffold_project(
    name: str,
    description: str,
    stack: str,
    target_dir: str,
    source_dir: str
) -> None:
    if os.path.exists(target_dir):
        print(f"Error: Directory {target_dir} already exists.")
        sys.exit(1)

    print(f"Creating project '{name}' in {target_dir}...")

    # Use absolute paths for source and target
    abs_source = os.path.abspath(source_dir)
    abs_target = os.path.abspath(target_dir)

    shutil.copytree(abs_source, abs_target, ignore=ignore_files)

    current_date = datetime.now().strftime("%Y-%m-%d")

    # Overwrite context files
    with open(os.path.join(abs_target, "PROJECT_CONTEXT.md"), "w", encoding="utf-8") as f:
        f.write(PROJECT_CONTEXT_TEMPLATE.format(name=name, description=description, stack=stack))

    with open(os.path.join(abs_target, "DEV_CONTEXT.md"), "w", encoding="utf-8") as f:
        f.write(DEV_CONTEXT_TEMPLATE.format(date=current_date, stack=stack))

    with open(os.path.join(abs_target, "README.md"), "w", encoding="utf-8") as f:
        f.write(README_TEMPLATE.format(name=name, description=description))

    # Init git
    try:
        # Check if git is available
        subprocess.run(["git", "--version"], capture_output=True, check=True)

        subprocess.run(["git", "init"], cwd=abs_target, check=True)
        subprocess.run(["git", "add", "."], cwd=abs_target, check=True)
        subprocess.run(["git", "commit", "-m", "init: project scaffold from Cortex template"], cwd=abs_target, check=True)
        print("Git repository initialized.")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Warning: Failed to initialize git repository: {e}")

@beartype
def main() -> None:
    parser = argparse.ArgumentParser(description="Cortex Scaffolder")
    parser.add_argument("--name", required=True, help="Project name")
    parser.add_argument("--description", required=True, help="Project description")
    parser.add_argument("--stack", required=True, help="Project stack")
    parser.add_argument("--target", required=True, help="Target directory")
    parser.add_argument("--source", default=".", help="Source template directory")

    args = parser.parse_args()

    scaffold_project(
        name=args.name,
        description=args.description,
        stack=args.stack,
        target_dir=args.target,
        source_dir=args.source
    )
    print(f"Project '{args.name}' successfully created.")

if __name__ == "__main__":
    main()
