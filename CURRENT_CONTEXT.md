<!-- L0: Текущий фокус, активные проекты, ближайшие шаги -->
# Current Context

## Фокус
- **Steam Sniper v2.3** — price alerts развёрнуто: Chrome extension v1.2 с inline 🔴/🟢 формой, backend-алерты (Codex закончил всё по брифу). На проде http://72.56.37.150/. Ждём Лёху чтобы end-to-end проверил TG-уведомления.
- **21.04 UX-фикс по аудио-фидбеку Лёхи** — в item_detail.js секция "Telegram alerts" раньше скрывалась если предмета нет в Fav/Wishlist; Лёха думал что "таргет не работает". Теперь при пустом state показывается CTA + две кнопки "В Избранное / В Хотелки" (используют глобальный `.list-toggle` handler). После клика `events.on('lists:changed')` в item_detail перерисовывает модалку с полями 🔴/🟢. SW bump v4→v5, `item_detail.js`+`theme.js` добавлены в STATIC_ASSETS. Zip extension + LESHA-INSTRUCTIONS.md лежат в `runtime/release/`.
- **cortex-vm — мертва с 19.04 00:00 UTC** (OOM kernel прибил funding-uvicorn). Snapshot pipeline стоит >30ч. User попросил Codex разобраться. Если нет — ресет `gcloud compute instances reset cortex-vm`.
- **PharmOrder** — бриф для работы готов (`PHARMORDER_EXPORT_FIX_BRIEFING.md`). Симптом «касса пишет не выгрузила, а на VPS есть» → неидемпотентный /api/export. Патч через UUID request_id (server + index.html + cashbox + sync_standalone).
- **apteka-bot** — фикс escape_markdown применён на VPS. Команда «История» снова возвращает список карточек.
- **VoiceType / Cypher** — работает на новом USB-микрофоне Fifine. Autostart + watchdog: `scripts/voicetype.vbs` в Startup, каждые 30с проверяет через WMI что `pythonw -m voice_type.main` жив, иначе поднимает. 15с delay после логона чтоб USB успел подняться. Двойной pythonw.exe (родитель+дочерний whisper-server) — норма, не баг.
- **Klink** — отложено.
- **Funding Scanner** — dashboard на VM (34.159.55.61:8080), сейчас недоступен из-за OOM VM.
- **Diary система** — 19 записей в `memory/diary/` (репо, единый источник правды). pre-compact.py, /diary, /reflect все пишут/читают туда. MEMORY.md + feedback/project/user/reference — в `C:\Users\User\.claude\projects\D--code-2026-2-cortex\memory\` (per-user, не в git).
- **Защитная сетка работает с 22.04.** `pre-commit` hook + `scripts/ops.sh test` реально прогоняют 116 тестов (104 steam-sniper + 12 metrics) за ~2с. До сегодня ссылались на удалённые `tools/heartbeat` — была false-green.

## Steam Sniper — статус после session 019

### Фаза 1 — Price alerts (КОDEX, всё готово и задеплоено)
- ✅ БД: `target_below_rub`/`target_above_rub` в `user_lists` с ALTER TABLE при старте (db.py:96-117)
- ✅ API: `PATCH /api/lists/target` (server.py:1481), `GET /api/lists` с `current_price_rub`/`alert_*_triggered` (1512+)
- ✅ UI модалки: секция «Telegram alerts» с 🔴/🟢 полями (item_detail.js:248+)
- ✅ Triggering: `_check_list_alerts()` в `_refresh_prices` (server.py:596, 1087)
- ✅ TG-уведомления: через Bot API из env `TELEGRAM_BOT_TOKEN`+`LESHA_TG_CHAT_ID` (оба установлены на VPS с 17.04)
- ✅ Hero-карточка «Алерты»: учёт fav/wish (stats.js:16-39)
- ✅ Деплой `deploy_quick.py` прошёл, сервис `steam-sniper-dashboard` active, ошибок в логе нет

### Фаза 2 — Chrome extension v1.2 (сделано этой сессией)
- ✅ `content.js` — inline-форма с 🔴/🟢 после Favorite/Wishlist, валидация, Enter/Esc
- ✅ `background.js` — `addToList` + `setTargets`, partial-success handling
- ✅ `styles.css` — форма, `bottom: 96px` чтобы не перекрывать виджет поддержки lis-skins
- ✅ `manifest.json` v1.2

### Фаза 3 — TG-бот принимает команды от Лёхи
- ⏳ НЕ УТОЧНЕНО с юзером. Когда Лёха сказал «чтобы в теге весь функционал был» — имел в виду уведомления (готово) или команды `/addwish`, `/target`? Ждёт решения.

### Фаза 4 — Карточки «один-в-один» с lis-skins
- ⏳ НЕ НАЧИНАЛ. Ждёт что Лёха end-to-end проверит алерты.

## Ближайшие шаги

### 1. От Ники
- [ ] Reload Chrome extension → тест на `lis-skins.com` (кнопка «Add to Sniper» → Favorite → форма → Добавить → карточка появляется в dashboard с таргетами)
- [ ] Передать обновлённую папку `tools/steam-sniper/extension/` Лёхе (zip или инструкции загрузить распакованное)
- [ ] Попросить Лёху поставить test-цель на дешёвый предмет, дождаться 5-мин цикла `_refresh_prices` — убедиться что TG приходит
- [ ] Если Codex не починит cortex-vm — `gcloud compute instances reset cortex-vm --zone=europe-west3-b`, потом проверить что funding-scanner, steam-sniper-snapshot cron, tg-digest стартанули
- [ ] Передать `PHARMORDER_EXPORT_FIX_BRIEFING.md` Клоду на рабочем компе (Desktop)

### 2. Steam Sniper на потом
- [ ] Web push для алертов (Лёхе TG через VPN неудобно)
- [ ] Cortex-vm закроется в мае → перенос snapshot pipeline на новый VPS Timeweb
- [ ] Дизайн-редизайн карточек под lis-skins (Фаза 4)

### 3. Прочие задачи
- [ ] PharmOrder мониторинг (OOM, sync — неделю смотрим)
- [ ] Klink: Seedance 2.0 — выбрать платформу (Jimeng vs Dreamina)
- [ ] Cypher: Browser Use интеграция — L3 path
- [ ] `/reflect` — накопилось 016-020 для обработки (после merge 21.04 команда наконец видит актуальные diary)
- [ ] Funding: EdgeX verifier
- [ ] Keenetic Hopper — WireGuard VPN
- [ ] VoiceType: если watchdog-pattern окажется мало (падает чаще раза в день) — копать controller.py daemon thread, возможно SetForegroundWindow loop

## Ссылки

### Steam Sniper
- Dashboard: http://72.56.37.150/
- Код: `D:\code\2026\2\cortex\tools\steam-sniper\`
- Extension: `D:\code\2026\2\cortex\tools\steam-sniper\extension\` (v1.2)
- Брифинги Codex: `C:\Users\User\Desktop\STEAM_SNIPER_CODEX_ITEM_DETAIL_EXPAND.md`, `STEAM_SNIPER_CODEX_ALERTS.md`
- Snapshot builder на VM: `~/sync_steam_sniper_snapshot.sh`, лог `~/sync_steam_sniper_snapshot.log`
- Cron на VM: `0 */4 * * *`
- Quick deploy: `cd tools/steam-sniper && uv run python deploy_quick.py` (60 сек)

### PharmOrder
- Бриф фикса экспорта: `C:\Users\User\Desktop\PHARMORDER_EXPORT_FIX_BRIEFING.md`
- Dashboard: http://194.87.140.204:8000
- Код (VPS): `/opt/pharmorder/src/`, `/opt/apteka-bot/src/bot/`
- Sync standalone (мама): `E:\новый склит смнк\sklit_syncV3\sync_standalone.py`
- Локальная копия VPS: `C:\tmp\vps_pharmorder\`

### Gemini custom instructions
- Три блока переписаны в диалоге session 019 (стиль / фарма / учёба). Лимит Saved Info ~1500 chars на блок.

### Инфра
- cortex-vm: `gcloud compute ssh cortex-vm --zone=europe-west3-b` — **сейчас мертва из-за OOM 19.04**
- VPS Steam Sniper: `ssh -i ~/.ssh/vps_key root@72.56.37.150`
- VPS PharmOrder: 194.87.140.204 (paramiko из Python, creds в `runtime/vps-creds.env`)
- VoiceType / Cypher: `D:\code\2026\3\voice-type`
- Субагент playbook: `memory/subagents-playbook.md`
