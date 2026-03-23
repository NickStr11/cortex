# Current Context

## Фокус
- **VoiceType** — voice-to-text прилка (D:\code\2026\3\voice-type). v1 РАБОТАЕТ. 3 режима: fast/local/full. Autostart. Ctrl+Shift+Space.
- **PharmOrder** — production на VPS (194.87.140.204:8000). Стабилен.
- **TG Digest** — на VM, timer 03:00 UTC. ⚠ Telethon сессия протухла — ПОЧИНИТЬ
- **Kwork Automation** — production pipeline (D:\code\2026\3\kwork).
- **Funding Scanner** — dashboard на VM (34.159.55.61:8080).
- **Ollama** — установлен, qwen2.5:1.5b, AMD RX 7800 XT 16GB
- **MCP Stack** — Context7, Codex CLI 5.3, Exa, Playwright, Context Mode
- **Diary система** — обкатана. /reflect работает.

## Что сделано (session 007, 2026-03-23 вечер)
- VoiceType: Phase 1+2 через GSD, 7 планов, ~45 тестов, всё работает
- Фиксы: Win32 RegisterHotKey, Vertex AI, Chirp 3, Shift+Enter, chunking >60s
- 3 режима очистки: fast (regex+абзацы) / local (Ollama) / full (Gemini)
- Ollama установлен, qwen2.5:1.5b скачан
- Autostart + restart.bat на рабочем столе
- GCP infra: service account, Speech + Vertex AI APIs, ключ
- Чайный бизнес: 8 голосовых транскрибированы, анализ + PDF на рабочем столе
- /reflect первый прогон, fast_clean улучшен

## Ближайшие шаги
- [ ] **Telethon на VM — починить сессию** (дайджест может быть сломан!)
- [ ] **VoiceType: обкатка** — покатать пару дней, собрать баги
- [ ] **VoiceType: попробовать qwen2.5:3b** — 1.5b слабая для очистки
- [ ] **VoiceType: streaming STT** — future idea, -1-2с латентности
- [ ] **Funding: EdgeX verifier** — сравнить fundingRate vs forecastFundingRate
- [ ] **Funding: добавить BingX** — расширить coverage
- [ ] **Обкатать /reflect** — следующий прогон после 5+ diary записей
- [ ] **PharmOrder: tg-pharma live smoke**

## Ссылки
- VoiceType: `D:\code\2026\3\voice-type` (.planning/ внутри)
- Чайный анализ: `~/Desktop/tea-business-analysis-v2.pdf`
- Codex отчёт: `~/Desktop/adam-kadmoon-detailed-report-2026-03-23.md`
- Funding: `memory/funding-arb.md`
- Субагент playbook: `memory/subagents-playbook.md`
