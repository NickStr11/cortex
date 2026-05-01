# <project-name> recon — YYYY-MM-DD

> Шаблон для исследования внешних репо/проектов. Скопируй в `<project-name>-recon-YYYY-MM-DD.md`, заполни секции, удали этот блок.
>
> Цель recon-report — зафиксировать **проверенные** факты о внешнем проекте и явное решение что брать / что отвергнуть. Не пересказ README. Не подборка фич.

## Source

- **Repo:** <URL>
- **Local clone:** `runtime/research/<name>-src/` (если клонировал)
- **Checked commit:** `<git rev-parse HEAD>` ← обязательно для воспроизводимости
- **Date checked:** YYYY-MM-DD
- **Latest release:** `<tag>` / `<version>` (через `gh api repos/<owner>/<repo>/releases/latest`)

## What it is

1-2 абзаца что это **на самом деле** (не маркетинговое описание). Заточенность: agent runtime / library / context pack / template / etc.

## Architecture (verified claims only)

Только то что **проверил напрямую** через клонирование/Read. Каждый claim с указанием файла:

- `<feature>` — `<path/to/file.py>:<line>` ← цитата или короткое описание

> Не пиши что-то чего не проверил. Если фича заявлена в README но ты не открывал файл — пометь как `[⚠️ unverified — only README claim]`.

## Transferable ideas

Что **реально** можно принести в наш проект. Каждый пункт с оценкой:
- **Effort:** low / medium / high
- **Value:** low / medium / high
- **Risk:** какой риск при переносе (новые deps? архитектурные допущения?)

```
1. <idea> — Effort: low, Value: high. <обоснование>
2. ...
```

## Reject list

Что **не переносим**, явно с причиной. Чтобы не возвращаться к обсуждению через месяц:
- `<feature>` — почему отвергаем

## Security / safety notes

Если в исходном проекте есть unsafe defaults — зафиксировать чтобы случайно не унаследовать:
- plaintext credentials patterns
- privileged execution disguised as sandbox
- broad data persistence
- unauthenticated localhost APIs
- env passthrough без gating

## Verification log

Список tool-calls которые сделал для верификации (для будущей проверки):
- `gh api repos/X/Y --jq Z` → результат
- `git -C runtime/research/X-src rev-parse HEAD` → SHA
- `grep -r "feature_name" runtime/research/X-src/` → matches

## Next actions (если есть)

Конкретные шаги если решили что-то перенять. С приоритетом и зависимостями.

---

**Верификация заполнения:** перед коммитом убедись что:
- [ ] Source URL + commit hash указаны
- [ ] Каждый architecture claim имеет файл/строку
- [ ] В Transferable ideas нет того чего нет в коде источника
- [ ] Reject list объясняет **почему**, не только что
- [ ] Если клонировал — clone path в `.gitignore` или `runtime/research/<name>-src/` (gitignored по дефолту)
