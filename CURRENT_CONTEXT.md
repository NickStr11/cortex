<!-- L0: Текущий фокус, активные проекты, ближайшие шаги -->
# Current Context

## Фокус
- **Steam Sniper v2.1** — Item Detail Page в production. Cold-click ~350ms из SQLite snapshot. Snapshot собирается на cortex-vm каждые 4 часа cron'ом, льётся на VPS 72.56.37.150 по scp. Dashboard: http://72.56.37.150/
- **PharmOrder** — production на VPS (194.87.140.204:8000). Hardened: swap 1GB, MemoryMax=450M. Sync retry fix на мамином ноуте.
- **VoiceType / Cypher** — voice-to-text + голосовой ассистент (D:\code\2026\3\voice-type). В автозагрузке. Сегодня два фикса: retry на мик при autostart, paste без split'а для Claude Code 4.7.
- **Klink** — продуктовые видео-шоты с Лёшей @olmogoodwin. Kling 3.0 / Veo 3.1 / Seedance 2.0.
- **TG Digest** — на VM, timer 03:00 UTC.
- **Funding Scanner** — dashboard на VM (34.159.55.61:8080).
- **MCP Stack** — Context7, Codex CLI, Exa, Playwright, Context Mode, Browser Use
- **Diary система** — 17 записей (8 в репо `memory/diary/` + 5-9 в auto-memory).

## Что сделано (session 017, 2026-04-17)

### VoiceType — два фикса
- **Autostart retry:** в `main.py:51-67` 30 попыток × 1 сек на `check_microphone_access()`. USB-мик DJI теперь успевает проиниться.
- **VBS sleep:** в `voicetype.vbs` добавлен `WScript.Sleep 10000` перед pythonw.
- **Paste для Claude Code 4.7:** в `llm.py:28` Gemini-промпт требует single paragraph без blank lines. В `paste.py` убрал split+Shift+Enter, делаю один paste целиком + нормализация `\n{2,}` → `\n`. Больше не дробит длинное аудио на несколько сообщений.

### Steam Sniper Phase 11 — Item Detail Page
Лёха голосовым 15.04 попросил детальную карточку (клик по скину → все листинги с ценой/float/stickers/inspect). Сделали совместно с Codex:
- **Codex (c4dcd7b):** модуль item_detail, модалка, streaming fetch через ijson, image_cache, fix битых имён в favorites.
- **Я (651e149):** фикс Decimal bug — без него endpoint возвращал пустые листинги.
- **Я (3b9b824):** async endpoint + polling + warm-cache loop + больше UI полей (StatTrak/Souvenir бейджи, wear-tier pills, sticker-wear %).
- **Codex (d56f081):** переписал на SQLite snapshot — убрал всю async/pending/warm логику. Cold-click 350 мс вместо минут. Это финальная реализация.

**Cortex-vm cron pipeline:** snapshot собирается на VM каждые 4 часа, льётся на VPS. `~/sync_steam_sniper_snapshot.sh` + cron `0 */4 * * *`. Первый прогон: 1.87M листингов, 648 МБ, 38 сек.

**До мая работаем на cortex-vm**, потом (когда VM закроется) купим новый VPS (2 vCPU / 2+ GB RAM, ~1000-1400 ₽/мес у Timeweb) и перенесём pipeline туда.

### Прочее
- Рабочий стол почищен: `Chrome CDP.lnk` → `runtime/shortcuts/` (gitignored), остальное удалено кроме Yoga-Isometric и практик.

## Ближайшие шаги

### 1. Steam Sniper — мониторинг
- [ ] Проверить через 1-2 дня что cron на cortex-vm стабильно отрабатывает (лог `~/sync_steam_sniper_snapshot.log` на VM)
- [ ] Подписаться Лёха на dashboard: http://72.56.37.150/ (показать ему item detail)

### 2. Cortex-vm → новый VPS (в мае)
- [ ] Купить VPS у Timeweb: 2 vCPU / 2-4 GB RAM / 20-30 GB (~1000-1400 ₽/мес)
- [ ] Перенести pipeline: тот же `sync_steam_sniper_snapshot.sh` + cron на новый VPS
- [ ] Выключить старый VPS-снайпер или объединить с новым

### 3. PharmOrder — мониторинг
- [ ] Dedup выгрузок: server.py на VPS (MD5 hash корзины, 2 мин окно) — уже вкатан 2026-04-15
- [ ] Проверить через неделю: нет ли OOM, проблем с sync

### 4. Прочие задачи
- [ ] Klink: Seedance 2.0 — выбрать платформу (Jimeng vs Dreamina)
- [ ] Cypher: Browser Use интеграция — L3 path
- [ ] `/reflect` — накопилось 17 diary, пора
- [ ] Funding: EdgeX verifier
- [ ] Keenetic Hopper — WireGuard VPN
- [ ] USB-микрофон для стационара (Fifine K669B или аналог)
- [ ] VoiceType: watchdog для хоткей-листенера (daemon thread умирает)
- [ ] Steam Sniper: pagination "показать ещё 20" на item detail (не срочно)

## Ссылки
- Steam Sniper Dashboard: http://72.56.37.150/
- Steam Sniper код: `tools/steam-sniper/` (в cortex)
- Snapshot builder на VM: `~/sync_steam_sniper_snapshot.sh`, лог `~/sync_steam_sniper_snapshot.log`
- Cron на VM: `0 */4 * * *`
- PharmOrder Dashboard: http://194.87.140.204:8000
- PharmOrder код (VPS): `/opt/pharmorder/src/`
- Sync standalone (мама): `E:\новый склит смнк\sklit_syncV3\sync_standalone.py`
- VoiceType / Cypher: `D:\code\2026\3\voice-type`
- Codex брифинг (item detail): `C:\Users\User\Desktop\STEAM_SNIPER_CODEX_BRIEFING.md`
- Codex брифинг (perf): `C:\Users\User\Desktop\STEAM_SNIPER_PERFORMANCE_BRIEFING.md`
- Субагент playbook: `memory/subagents-playbook.md`
- Funding: `memory/funding-arb.md`
