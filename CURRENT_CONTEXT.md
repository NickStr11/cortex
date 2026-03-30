<!-- L0: Текущий фокус, активные проекты, ближайшие шаги -->
# Current Context

## Фокус
- **VoiceType / Cypher** — voice-to-text + голосовой ассистент (D:\code\2026\3\voice-type). whisper.cpp Vulkan GPU ~850ms. Cypher: prefix gate, AppResolver, RapidFuzz, Gemini planner (L2). 133 теста. Codex активно пилит.
- **Browser Use** — установлен (pip, v0.12.5), работает через Gemini 2.5 Flash. Заменяет Playwright MCP для сложных браузерных задач. Тест на Гемотесте — успех с первой попытки.
- **Анализы крови** — корзина собрана в Гемотесте (Славянск-на-Кубани), 18 анализов, 11 380 ₽. Сдать в пятницу 3 апреля.
- **PharmOrder** — production на VPS (194.87.140.204:8000). Стабилен.
- **TG Digest** — на VM, timer 03:00 UTC.
- **Kwork Automation** — production pipeline (D:\code\2026\3\kwork).
- **Funding Scanner** — dashboard на VM (34.159.55.61:8080).
- **MCP Stack** — Context7, Codex CLI, Exa, Playwright, Context Mode, Browser Use
- **Diary система** — 11 записей.

## Что сделано (session 011, 2026-03-30)
- **Cypher v2 updates (Codex)** — safe system targets (панель управления, загрузки, параметры), TelegramWebExecutor search/read, расширен planner vocabulary. 133 теста.
- **Browser Use** — установлен, протестирован с Gemini Flash. Работает кратно лучше Playwright MCP для форм/корзин/навигации.
- **Анализы крови** — выбрана панель 18 показателей, Codex ревьюнул (убрал натяжки), корзина собрана в Гемотесте.
- **Malwarebytes скан** — чисто (PUP uTorrent + RiskWare zapret/Ammyy, стилеров нет).
- **Петличка DJI Mic Mini** — выбрана, найдена на Ozon за 4 443 ₽.
- **Новые memory-правила** — browser-use > playwright, 1 фейл → менять инструмент, не предлагать отдых.

## Ближайшие шаги
- [ ] **Анализы крови** — сдать в пятницу 3 апреля, натощак до 10:00
- [ ] **Петличка DJI Mic Mini** — заказать на Ozon (распродажа заканчивается)
- [ ] **Cypher: Browser Use интеграция** — L3 path для сложных браузерных задач через browser-use
- [ ] **Cypher: протестировать новые фичи живьём** — system targets, telegram search/read
- [ ] **OpenClaw** — попробовать установить, оценить для сложных multi-step задач
- [ ] **Subagents playbook experiment** — срез 2026-04-01
- [ ] **Обкатать /reflect** — 11 diary записей, пора
- [ ] **whisper.cpp: soak test** — 100+ запросов для стабильности Vulkan
- [ ] **Funding: EdgeX verifier** — сравнить fundingRate vs forecastFundingRate
- [ ] **Keenetic Hopper** — настроить WireGuard VPN + policy routing + DoH

## Ссылки
- VoiceType / Cypher: `D:\code\2026\3\voice-type` (.planning/ внутри)
- Browser Use тест: `C:\tmp\browser_use_test.py`
- Анализы rationale: `~/Desktop/blood_tests_rationale.md`
- Задача для Codex (Гемотест): `~/Desktop/gemotest_task_for_codex.md`
- whisper.cpp build: `D:\code\2026\3\whisper-cpp-build`
- whisper.cpp бинарники + модель: `D:\code\2026\3\voice-type\runtime\whisper-cpp\`
- PharmOrder-Local: `~/Desktop/PharmOrder-Local/`
- Субагент playbook: `memory/subagents-playbook.md`
- Funding: `memory/funding-arb.md`
