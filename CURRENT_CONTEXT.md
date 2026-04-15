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

## Что сделано (session 015, 2026-04-15)

### PharmOrder VPS hardening
- **OOM диагностика**: 8 OOM-kills за 3 дня. Steam Sniper (240MB) + PharmOrder рост до 500MB + 0 swap
- **Steam Sniper удалён** с VPS (dashboard + bot + /opt/steam-sniper/)
- **Swap 1GB** добавлен (/swapfile, fstab)
- **MemoryMax=450M** в pharmorder.service
- **sklit_cache.db.bak** удалён (110MB)
- **VPS креды** в runtime/vps-creds.env (gitignored)

### Sync client retry fix
- mtime баг пофикшен в sync_standalone.py (мамин ноут): прайсы + история + Созвездие
- Файл на съёмном диске E:\новый склит смнк\sklit_syncV3\

### Codex коллаборация
- Брифинг ~/Desktop/PHARMORDER_CODEX_BRIEFING.md
- Codex подтвердил диагнозы, нашёл 2й mtime баг, предложил streaming upload

### DJI Mic Mini
- Подключён, спарен, протестирован. Стандартный микрофон выставлен default (+30 дБ boost)
- Ollama убран из автозагрузки, VoiceType оставлен

## Ближайшие шаги

### 1. PharmOrder — мониторинг
- [ ] Проверить через 2-3 дня: нет ли OOM, дублей выгрузок, проблем с sync
- [ ] Если дубли повторятся → dedup на VPS (inflight с lease/timeout)

### 2. Steam Sniper — новый VPS
- [ ] Найти/купить отдельный VPS для Steam Sniper
- [ ] Задеплоить из runtime/steam-sniper-vps-backup/ + tools/steam-sniper/
- [ ] Мерж Codex изменений (D:\code\2026\3\steam-sniper → tools/steam-sniper)

### 3. Прочие задачи
- [ ] Klink: Seedance 2.0 — выбрать платформу (Jimeng vs Dreamina)
- [ ] Cypher: Browser Use интеграция — L3 path
- [ ] /reflect — 15 diary записей, пора
- [ ] Funding: EdgeX verifier
- [ ] Keenetic Hopper — WireGuard VPN
- [ ] USB-микрофон для стационара (Fifine K669B или аналог)

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
