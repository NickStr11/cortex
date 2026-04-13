<!-- L0: Текущий фокус, активные проекты, ближайшие шаги -->
# Current Context

## Фокус
- **Steam Sniper v2.0** — ВЫПОЛНЕНО. Production на VPS (194.87.140.204:8100). Каталог 24к предметов, категории, избранное/хотелки, кейсы, PWA, Chrome extension. Codex сделал архитектурный фикс RUB + live rate calibration через extension.
- **VoiceType / Cypher** — voice-to-text + голосовой ассистент (D:\code\2026\3\voice-type). whisper.cpp Vulkan GPU, server mode. Cypher: AppResolver + RapidFuzz + Gemini planner. 135 тестов.
- **PharmOrder** — production на VPS (194.87.140.204:8000). Стабилен.
- **Klink** — продуктовые видео-шоты с Лёшей @olmogoodwin. Kling 3.0 / Veo 3.1 / Seedance 2.0.
- **TG Digest** — на VM, timer 03:00 UTC.
- **Funding Scanner** — dashboard на VM (34.159.55.61:8080).
- **MCP Stack** — Context7, Codex CLI, Exa, Playwright, Context Mode, Browser Use
- **Diary система** — 14 записей.

## Что сделано (session 016, 2026-04-13 вечер)

### Steam Sniper v2.0 — полный GSD milestone
- **6 фаз выполнены** (5-10): Dashboard Split → Catalog + Category Parser → Dual Lists → UI → Cases + PWA → Chrome Extension
- **22 требования**, 8 планов, ~35 коммитов
- **Деплой на VPS** — всё работает, оба systemd сервиса active
- **Пост-деплой фиксы**: картинки (ByMykel API 15003 записей), цены (multiplier 1.0314), русский поиск (80+ терминов словарь), SW cache bust

### Codex коллаборация (D:\code\2026\3\steam-sniper)
- **Архитектурный фикс**: RUB как first-class data. price_rub фиксируется при collect, не пересчитывается
- **Live rate calibration**: Chrome extension → POST /api/internal/rate-samples → дашборд калибрует rate по реальной цене lis-skins
- **98 тестов**, задеплоено на VPS

### Seedance 2.0 ресёрч
- Jimeng $10/мес (китайский), Dreamina $18-84/мес, Atlas Cloud API $0.022/сек

## Ближайшие шаги

### 1. Steam Sniper — мерж Codex изменений
- [ ] Перенести изменения из D:\code\2026\3\steam-sniper в tools/steam-sniper
- [ ] Лёша загружает Chrome extension (unpacked reload) → rate калибруется автоматически
- [ ] Проверить live: rate_source=sample:extension в /api/debug

### 2. Steam Sniper — оставшиеся улучшения
- [ ] Русский поиск: full EN→RU маппинг (24к предметов через Steam API, одноразовый batch)
- [ ] Service Worker: переключить static на stale-while-revalidate
- [ ] HTTPS: DuckDNS + certbot на VPS (для PWA на iPhone)

### 3. Прочие задачи
- [ ] Klink: Seedance 2.0 — выбрать платформу (Jimeng vs Dreamina)
- [ ] Cypher: Browser Use интеграция — L3 path
- [ ] Обкатать /reflect — 14 diary записей, пора
- [ ] Funding: EdgeX verifier
- [ ] Keenetic Hopper — WireGuard VPN

## Ссылки
- Steam Sniper Dashboard: http://194.87.140.204:8100
- Steam Sniper код (основной): `tools/steam-sniper/`
- Steam Sniper код (Codex): `D:\code\2026\3\steam-sniper`
- Steam Sniper .planning/: `tools/steam-sniper/.planning/`
- CODEX_TASK.md: `tools/steam-sniper/CODEX_TASK.md`
- VoiceType / Cypher: `D:\code\2026\3\voice-type`
- PharmOrder-Local: `~/Desktop/PharmOrder-Local/`
- Субагент playbook: `memory/subagents-playbook.md`
- Funding: `memory/funding-arb.md`
