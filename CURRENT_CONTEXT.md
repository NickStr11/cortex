<!-- L0: Текущий фокус, активные проекты, ближайшие шаги -->
# Current Context

## Фокус
- **PharmOrder** — production на VPS (194.87.140.204:8000). Hardened: swap 1GB, MemoryMax=450M, Steam Sniper убран. Sync retry fix на мамином ноуте.
- **VoiceType / Cypher** — voice-to-text + голосовой ассистент (D:\code\2026\3\voice-type). whisper.cpp Vulkan GPU, server mode. В автозагрузке.
- **Klink** — продуктовые видео-шоты с Лёшей @olmogoodwin. Kling 3.0 / Veo 3.1 / Seedance 2.0.
- **TG Digest** — на VM, timer 03:00 UTC.
- **Funding Scanner** — dashboard на VM (34.159.55.61:8080).
- **Steam Sniper** — убран с VPS, код в `tools/steam-sniper/` + бэкап `runtime/steam-sniper-vps-backup/`. Ждёт другой VPS.
- **MCP Stack** — Context7, Codex CLI, Exa, Playwright, Context Mode, Browser Use
- **Diary система** — 15 записей.

## Что сделано (session 016, 2026-04-16)

### Steam Sniper — новый VPS заказан
- **Timeweb Cloud**, Москва, Ubuntu 24.04
- 1 vCPU / 1 GB RAM / 15 GB NVMe — **530 ₽/мес** (с публичным IPv4)
- Ждём IP → деплой из runtime/steam-sniper-vps-backup/ + tools/steam-sniper/

### VoiceType диагностика
- Хоткей Ctrl+Shift+Space иногда перестаёт работать (Win32 GetMessageW daemon thread умирает)
- Фикс: restart.bat. Потенциально нужен watchdog.

### Claude Code 4.7
- Вышел 16.04.2026. +13% кодинг, 3x production engineering, визия 3.75MP
- Апдейт: `winget upgrade Anthropic.ClaudeCode`

### Предыдущая сессия (015, 2026-04-15)
- PharmOrder VPS hardened (swap, MemoryMax, Steam Sniper убран)
- Sync retry fix на мамином ноуте
- DJI Mic Mini настроен, Ollama убран из автозагрузки

## Ближайшие шаги

### 1. PharmOrder — мониторинг
- [x] Dedup выгрузок: server.py на VPS — MD5 hash корзины, 2 мин окно (2026-04-15). Бэкап: server.py.bak
- [ ] Проверить через 2-3 дня: нет ли OOM, проблем с sync

### 2. Steam Sniper — деплой на новый VPS
- [x] Заказать VPS (Timeweb Cloud, 1GB RAM, Москва, 530 ₽/мес) — 2026-04-16
- [ ] Получить IP, SSH доступ
- [ ] Задеплоить из runtime/steam-sniper-vps-backup/ + tools/steam-sniper/
- [ ] Мерж Codex изменений (D:\code\2026\3\steam-sniper → tools/steam-sniper)

### 3. Прочие задачи
- [ ] Klink: Seedance 2.0 — выбрать платформу (Jimeng vs Dreamina)
- [ ] Cypher: Browser Use интеграция — L3 path
- [ ] /reflect — 15 diary записей, пора
- [ ] Funding: EdgeX verifier
- [ ] Keenetic Hopper — WireGuard VPN
- [ ] USB-микрофон для стационара (Fifine K669B или аналог)
- [ ] VoiceType: watchdog для хоткей-листенера (daemon thread умирает)

## Ссылки
- PharmOrder Dashboard: http://194.87.140.204:8000
- PharmOrder код (VPS): `/opt/pharmorder/src/`
- Sync standalone (мама): `E:\новый склит смнк\sklit_syncV3\sync_standalone.py`
- Steam Sniper бэкап: `runtime/steam-sniper-vps-backup/`
- Steam Sniper код: `tools/steam-sniper/` + `D:\code\2026\3\steam-sniper`
- Codex брифинг: `~/Desktop/PHARMORDER_CODEX_BRIEFING.md`
- VoiceType / Cypher: `D:\code\2026\3\voice-type`
- Субагент playbook: `memory/subagents-playbook.md`
- Funding: `memory/funding-arb.md`
- PharmOrder fixes pending: `memory/project_pharmorder-fixes.md`
