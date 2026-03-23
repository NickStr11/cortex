# Current Context

## Фокус
- **VoiceType** — voice-to-text десктоп прилка (D:\code\2026\3\voice-type). v1 РАБОТАЕТ. Ctrl+Shift+Space → говори → текст в окне.
- **PharmOrder** — production на VPS (194.87.140.204:8000). Стабилен.
- **TG Digest** — NotebookLM deep research + raw TG chat, задеплоен на VM, timer 03:00 UTC
- **Kwork Automation** — production pipeline (D:\code\2026\3\kwork). Полный цикл.
- **Funding Scanner** — dashboard на VM (34.159.55.61:8080).
- **MCP Stack** — Context7, Codex CLI 5.3, Exa, Playwright, Context Mode
- **Skills** — 15 local + 40 GSD + Superpowers plugin
- **OpenClaw** — второй ноут (nsv11), @cipherV2bot
- **Diary система** — обкатана. /reflect работает, первый прогон сделан.
- **Superwhisper** — установлен как референс, VoiceType его заменяет

## Что сделано (session 006, 2026-03-23)
- /reflect первый прогон: anti-pattern "создал — не проверил" → правило в CLAUDE.md
- VoiceType создан через GSD (2 фазы, 7 планов, ~45 тестов)
- Phase 1: scaffold, config, audio, hotkey, window capture
- Phase 2: STT (Chirp 2), LLM (Gemini 2.5 Flash), paste (pywin32), tray icon
- Фиксы: pynput → Win32 RegisterHotKey, API key → Vertex AI, multi-lang → single ru-RU
- GCP infra: service account, Speech + Vertex AI APIs, ключ
- Ресёрч agency-agents + mem0 для кента

## Ближайшие шаги
- [ ] **VoiceType: обкатка** — покатать пару дней, собрать баги
- [ ] **VoiceType: asyncio Ctrl+C fix** — cosmetic RuntimeError при выходе
- [ ] **VoiceType: LLM-режимы** — chat/formal/code (v2, когда обкатают основу)
- [ ] **Funding: EdgeX verifier** — сравнить fundingRate vs forecastFundingRate
- [ ] **Funding: добавить BingX** — расширить coverage бирж
- [ ] **Обкатать /reflect** — следующий прогон после 5+ diary записей
- [ ] **PharmOrder: tg-pharma live smoke**
- [ ] **OpenClaw WSL2 миграция** — когда native Windows gateway начнёт сыпаться

## Ссылки
- VoiceType: `D:\code\2026\3\voice-type` (GSD .planning/ внутри)
- Старые записи: `archive/dev-context-*.md`
- Funding арбитраж: `memory/funding-arb.md`
- Субагент playbook: `memory/subagents-playbook.md`
