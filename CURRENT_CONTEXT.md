<!-- L0: Текущий фокус, активные проекты, ближайшие шаги -->
# Current Context

## Фокус
- **VoiceType** — voice-to-text (D:\code\2026\3\voice-type). v1 РАБОТАЕТ. 3 режима: fast/local/full. Ctrl+Shift+Space. Автозагрузка Windows. Codex пофиксил: streaming убран, race condition, логирование.
- **PharmOrder** — production на VPS (194.87.140.204:8000). TZ=Europe/Moscow.
- **PharmOrder-Local** — аварийный fallback. Работает на мамином ноуте (Python 3.14). Починен батник + JS баги.
- **MANA tea (Ozon)** — аудит магазина кента. Куки сохранены (C:\Users\User\.ozon-seller\storage_state.json). Отчёт + конкурентный анализ + HTML-презентация на рабочем столе.
- **TG Digest** — на VM, timer 03:00 UTC. Telethon сессия рабочая.
- **Kwork Automation** — production pipeline (D:\code\2026\3\kwork).
- **Funding Scanner** — dashboard на VM (34.159.55.61:8080).
- **MCP Stack** — Context7, Codex CLI 5.3, Exa, Playwright, Context Mode
- **Diary система** — обкатана. L0 заголовки внедрены.

## Что сделано (session 009, 2026-03-27)
- Repo cleanup: -4749 строк, удалены мёртвые тулы/хуки/workflows, GitHub синхронизирован
- Subagents playbook восстановлен, триггер в CLAUDE.md
- MANA tea: полный аудит Ozon Seller, конкурентный анализ, HTML-презентация
- TG: 11 голосовых транскрибировано, фидбек Adam'у подготовлен
- PharmOrder-Local: починен для маминого ноута (python-multipart, JS баги)
- VoiceType: Codex аудит + фиксы (streaming, race, логирование), автозагрузка
- Cog: внедрены L0 заголовки (15 файлов), SSOT правило, archive/index.md
- Heartbeat workflow удалён (дубль TG digest)

## Ближайшие шаги
- [ ] **VoiceType: OpenAI gpt-4o-mini-transcribe** — тест как альтернатива Chirp 3. Если чистый текст — убить LLM cleanup
- [ ] **VoiceType: silence trim + auto mode** — low-hanging fruit для ускорения
- [ ] **VoiceType: LLM timeout фикс** — фейковый timeout через ThreadPoolExecutor, нужен subprocess
- [ ] **Subagents playbook experiment** — срез 2026-04-01, оценить эффект
- [ ] **Обкатать /reflect** — следующий прогон после 5+ diary записей (уже 9-я запись)
- [ ] **MANA tea: дизайн карточек** — макеты для Ozon (Дянь Хун, Шу Пуэр)
- [ ] **Funding: EdgeX verifier** — сравнить fundingRate vs forecastFundingRate
- [ ] **Voice Assistant (Jarvis)** — VoiceType + intent detection + tool use + TTS

## Ссылки
- VoiceType: `D:\code\2026\3\voice-type` (.planning/ внутри)
- PharmOrder-Local: `~/Desktop/PharmOrder-Local/`
- MANA tea отчёты: `~/Desktop/mana-tea-*.md`, `~/Desktop/mana-tea-report.html`
- Ozon Seller куки: `C:\Users\User\.ozon-seller\storage_state.json`
- Субагент playbook: `memory/subagents-playbook.md`
- Archive index: `archive/index.md`
- Funding: `memory/funding-arb.md`
