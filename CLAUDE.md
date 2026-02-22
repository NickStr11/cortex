# Project Rules

## 1. Context & Memory

- **DEV_CONTEXT.md** — главный лог разработки. Читай при старте сессии, обновляй при завершении.
- **PROJECT_CONTEXT.md** — описание проекта, стек, этапы. Читай при старте.
- Если контекст разговора становится слишком длинным — предложи обновить DEV_CONTEXT.md и начать новый чат.
- Используй абсолютные пути. Проверяй существование файлов перед операциями.

## 2. Technical Rules

### Code Style
- Плоская структура, минимум зависимостей.
- Код должен объяснять себя сам.
- При ошибке — сначала причина, затем конкретный фикс.

### File Size Limits
- **Максимум 700 строк** на файл (идеал: 300-500).
- **Максимум 50-70 строк** на функцию.
- **Максимум 4 уровня** вложенности.

### Documentation & APIs
- Перед использованием новых библиотек (обновлённых после 2024) — делай Web Search.
- Если дана ссылка — прочитай источник полностью перед кодингом.
- Не полагайся на знания модели для экосистем с частыми релизами.

## 3. Development Workflow

### Planning
- Перед значительными изменениями — сначала план.
- Разбивай большие задачи на мелкие проверяемые шаги.

### Execution
- Git First: инициализируй Git сразу, коммить после каждой рабочей фичи.
- Не запускай `npm run dev` / `python -m ...` автоматически. Используй build-команды для проверки ошибок.
- Перед новой подзадачей очищай контекст.

### Verification
- Quality Gates: Build → Types → Lint → Tests (80%+) → Security → Diff.
- Удаляй `console.log`, `print()` перед коммитом.
- Проверяй секреты в коде.
- Подробный workflow: `docs/verify.md`.

### Git
- Conventional Commits: `<type>(<scope>): <description>`.
- Branch naming: `<type>/<short-description>`.
- Подробный workflow: `docs/git-flow.md`.

## 4. Mandatory Actions

| Момент | Действие |
|--------|----------|
| **Старт проекта** | Заполнить `PROJECT_CONTEXT.md` |
| **Старт сессии** | Прочитать `DEV_CONTEXT.md` и `PROJECT_CONTEXT.md` |
| **После кода** | Проверить build/тесты. Обновить `DEV_CONTEXT.md` |
| **Перед PR** | Запустить verification (см. `docs/verify.md`) |
| **Финиш сессии** | Записать "Следующий шаг" в `DEV_CONTEXT.md` |

## 5. Communication

- **Язык**: Русский по умолчанию, если пользователь не перешёл на английский.
- **Без воды**: Никаких "Отличный выбор!", "Я с радостью помогу". Прямо и по существу.
- **Ошибки**: Укажи на ошибку и предложи фикс, без оценочных суждений.

## 6. Stack Defaults

> Конкретный стек определяется в `PROJECT_CONTEXT.md` для каждого проекта.

- **Frontend**: Next.js / HTML + Vanilla JS.
- **Backend**: Python (3.12+) или Node.js (20+).
- **Database**: PostgreSQL (Supabase) для продакшена, SQLite для локальных скриптов.
- **Package Manager**: `uv` для Python, `npm` для Node.js.
- Python-специфика: `docs/python-rules.md`.

## 7. Security

- Никогда не хардкодь API-ключи. Используй `.env` + `.gitignore`.
- Проверяй код на `sk-`, `api_key`, `password=` перед коммитом.
- Не игнорируй ошибки — записывай в "Известные проблемы" в DEV_CONTEXT.md.

## 8. Auto-triggers

- Если пользователь просит проанализировать/разобрать видео — используй скил `/video <путь>`.

## 9. Reference Docs

- `docs/verify.md` — verification workflow
- `docs/git-flow.md` — git conventions
- `docs/python-rules.md` — Python (uv, beartype, strict types)
- `docs/deploy-vps.md` — VPS deployment guide
- `tools/ui-ux/GUIDE.md` — UI/UX design system & search
- `tools/data-prep/` — data preprocessing pipeline
- `tools/video/` — video analysis (frames + transcription, requires ffmpeg)
