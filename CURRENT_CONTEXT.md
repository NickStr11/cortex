<!-- L0: Текущий фокус, активные проекты, ближайшие шаги -->
# Current Context

## Фокус
- **VoiceType / Cypher** — voice-to-text + голосовой ассистент (D:\code\2026\3\voice-type). whisper.cpp Vulkan GPU на AMD RX 7800 XT, ~850ms. Cypher: prefix gate, AppResolver (401 app), RapidFuzz. Codex активно пилит.
- **PharmOrder** — production на VPS (194.87.140.204:8000). TZ=Europe/Moscow. Шрифт починен.
- **PharmOrder-Local** — аварийный fallback на мамином ноуте.
- **TG Digest** — на VM, timer 03:00 UTC. Telethon сессия рабочая.
- **Kwork Automation** — production pipeline (D:\code\2026\3\kwork).
- **Funding Scanner** — dashboard на VM (34.159.55.61:8080).
- **MCP Stack** — Context7, Codex CLI (починен), Exa (дефолтный поиск), Playwright, Context Mode
- **Diary система** — обкатана. L0 заголовки внедрены. 10 записей.

## Что сделано (session 010, 2026-03-29)
- **whisper.cpp Vulkan GPU** — заменили faster-whisper CPU (~4с) на whisper.cpp Vulkan (~850ms). Свежая сборка v1.8.4 (MinGW + GGML_NO_BACKTRACE). Быстрее SuperWhisper.
- **Cypher** — голосовой ассистент поверх VoiceType. Prefix gate, regex, AppResolver + RapidFuzz (401 app). Codex написал модуль.
- **Codex CLI MCP** — починен (недостающий @openai/codex-win32-x64)
- **Alt+М** — keybinding для вставки скриншотов на русской раскладке
- **Ollama удалена** — -3.1GB (модели не нужны)
- **Code quality** — 96 тестов, pyright 0, ruff 0. Тесты переписаны, timeout fallback, uuid paths.
- **PharmOrder** — шрифт fallback починен (Fira Code → Courier New → monospace)

## Ближайшие шаги
- [ ] **Cypher v2: Planner** — маршрутизатор команд (capability / browser_agent / reject)
- [ ] **Cypher v2: Domain Executors** — Telegram (saved messages URL), Steam (steam://), Яндекс Музыка
- [ ] **Cypher v2: Browser Use** — fallback для сложных multi-step веб-задач
- [ ] **whisper.cpp: MSVC build** — для open-source релиза (GitHub Actions, без MinGW DLLs)
- [ ] **whisper.cpp: soak test** — 100+ запросов для проверки стабильности Vulkan
- [ ] **VoiceType: GitHub релиз** — README, .env.example с OpenRouter, инструкция по установке
- [ ] **Subagents playbook experiment** — срез 2026-04-01, оценить эффект
- [ ] **Обкатать /reflect** — следующий прогон (уже 10 diary записей)
- [ ] **Funding: EdgeX verifier** — сравнить fundingRate vs forecastFundingRate

## Ссылки
- VoiceType / Cypher: `D:\code\2026\3\voice-type` (.planning/ внутри)
- whisper.cpp build: `D:\code\2026\3\whisper-cpp-build`
- whisper.cpp бинарники + модель: `D:\code\2026\3\voice-type\runtime\whisper-cpp\`
- PharmOrder-Local: `~/Desktop/PharmOrder-Local/`
- Субагент playbook: `memory/subagents-playbook.md`
- Funding: `memory/funding-arb.md`
