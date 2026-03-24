# Current Context

## Фокус
- **VoiceType** — voice-to-text (D:\code\2026\3\voice-type). v1 РАБОТАЕТ. 3 режима: fast/local/full. Ctrl+Shift+Space. Fast mode смягчён (не режет осмысленные слова).
- **PharmOrder** — production на VPS (194.87.140.204:8000). TZ=Europe/Moscow. apteka.ru orders убраны.
- **PharmOrder-Local** — аварийный fallback на рабочем столе. Скопировать на мамин ноут.
- **TG Digest** — на VM, timer 03:00 UTC. Telethon сессия рабочая (cortex_userbot.session)
- **Kwork Automation** — production pipeline (D:\code\2026\3\kwork).
- **Funding Scanner** — dashboard на VM (34.159.55.61:8080).
- **Ollama** — установлен, qwen2.5:1.5b, AMD RX 7800 XT 16GB
- **MCP Stack** — Context7, Codex CLI 5.3, Exa, Playwright, Context Mode
- **Diary система** — обкатана. /reflect работает.

## Что сделано (session 008, 2026-03-24 вечер)
- PharmOrder Local Fallback: полная папка на рабочем столе, батник, sync, базы 150MB
- apteka.ru orders удалены (VPS + локалка): ~1000 строк кода
- Таймзона: UTC→MSK на VPS и локалке, 62 записи пересчитаны
- VoiceType streaming STT: реализован, протестирован — Chirp 3 не realtime, откат на batch
- VoiceType fast mode: смягчён filler removal (убрал ну/вот/слушай/смотри/значит/блин)

## Ближайшие шаги
- [ ] **VoiceType: Groq Whisper** — STT <1с вместо 3с. Главный кандидат на ускорение full mode
- [ ] **PharmOrder-Local → мамин ноут** — скопировать папку
- [ ] **VoiceType: обкатка** — fast mode после смягчения, собрать баги
- [ ] **VoiceType: попробовать qwen2.5:3b** — 1.5b слабая для local mode
- [ ] **Funding: EdgeX verifier** — сравнить fundingRate vs forecastFundingRate
- [ ] **Обкатать /reflect** — следующий прогон после 5+ diary записей
- [ ] **Voice Assistant (Jarvis)** — VoiceType + intent detection + tool use + TTS
- [ ] **PharmOrder: tg-pharma live smoke**

## Ссылки
- VoiceType: `D:\code\2026\3\voice-type` (.planning/ внутри)
- PharmOrder-Local: `~/Desktop/PharmOrder-Local/`
- Чайный анализ: `~/Desktop/tea-business-analysis-v2.pdf`
- Funding: `memory/funding-arb.md`
- Субагент playbook: `memory/subagents-playbook.md`
