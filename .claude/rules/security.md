---
paths: "**/.env, **/*.env.*, **/credentials*, **/secrets*"
---

# Security

- API-ключи только в `.env` (gitignored). Pre-commit hook блокирует секреты.
- При работе с `.env` — читать, использовать, но никогда не коммитить.
- Паттерны секретов: `sk-*`, `AIzaSy*`, `ghp_*` — блокируются автоматически.
