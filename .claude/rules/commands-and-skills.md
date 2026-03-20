---
paths: .claude/commands/*.md, .claude/skills/**/*.md
---

# Commands & Skills

- Команды (`/command`) — short prompts, вызываются пользователем.
- Скиллы — полные workflows с frontmatter (name, description, allowed-tools).
- Если повторяешь flow больше 2 раз — превращай в скилл.
- Тестируй скилл сразу после создания: вызови и проверь что работает.
- Аргументы через `$ARGUMENTS` в теле команды.
