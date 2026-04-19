<!-- L0: Текущий фокус, активные проекты, ближайшие шаги -->
# Current Context

## Фокус
- **Steam Sniper v2.2** — крупный батч правок по фидбеку Лёхи (17.04 голос+текст). На проде http://72.56.37.150/. Сейчас Codex параллельно пилит алерт-механизм (STEAM_SNIPER_CODEX_ALERTS.md).
- **PharmOrder** — production на VPS (194.87.140.204:8000). Hardened (swap 1GB, MemoryMax=450M). Sync retry fix на мамином ноуте.
- **VoiceType / Cypher** — voice-to-text + голосовой ассистент (D:\code\2026\3\voice-type). В автозагрузке. 017 сессии: autostart retry + paste без split'а для Claude Code 4.7.
- **Klink** — продуктовые видео-шоты с Лёшей @olmogoodwin. Kling 3.0 / Veo 3.1 / Seedance 2.0.
- **Funding Scanner** — dashboard на VM (34.159.55.61:8080).
- **Diary система** — 18 записей в `memory/diary/`.

## Steam Sniper — что сделано в session 018

### UI-батч из фидбека Лёхи (всё на проде)
- **Wishlist ★/♥ кнопки** 22×22 → 34×34 с заливкой при active (красный/жёлтый), hover-scale, z-index:2
- **Light theme** — toggle ☾/☀ в header, `[data-theme="light"]` CSS-vars override, inline bootstrap без FOUC, ослабленные тени (α=0.18 vs 0.4)
- **StatTrak/Souvenir/Normal фильтр** в каталоге (dropdown рядом с sort)
- **Картинки ножей Doppler** — 486 → 0 без фото. Fallback strip: state prefix → wear → Doppler phase/gem (regex)
- **Кейсы** — фикс 2 багов: скины `AK-47 | Case Hardened` попадали в кейсы (фикс в `category.py`: weapon lookup перед Case-check + ограничение на base до `|`); картинки через `item.url` → заменил на `item.image`
- **Cache-Control: no-cache, must-revalidate** для `/static/*` и `/` — браузер делает revalidation через ETag
- **Model-filter для ножей** — в `_MODEL_CATEGORIES` и `MODEL_FILTER_CATEGORIES` добавил `knife`. 21 модель (Bayonet/Karambit/M9/Butterfly…)
- **StatTrak для music_kit** — уже работало, проверил
- **Hero-карточки** Портфель/Дельта/Позиции → **Избранное/Хотелки/Алерты**. Алерт-карточка считает `buyReady`/`sellReady` из watchlist, меняет рамку (красная/зелёная/оранжевая)
- **UI polish** — скрыты нативные number-spinners, кастомная SVG-стрелка у `.detail-filter select`
- **Русификация каталога** — CAT_LABELS, sort options, поиск

### Брифинги для Codex (параллельная работа)
- `C:\Users\User\Desktop\STEAM_SNIPER_CODEX_ITEM_DETAIL_EXPAND.md` (426 строк) — wear-tabs, keychains, Steam price, rarity label, name_ru, интерактивный float, кнопка «lis-skins», русификация. **Часть уже сделана Codex'ом**, остались: русский title + английский, крупнее картинка (200×200), ярче «Тайное»
- `C:\Users\User\Desktop\STEAM_SNIPER_CODEX_ALERTS.md` (~150 строк) — target_below/above в favorites/wishlist + TG-notifications + web push opt. **Codex уже начал**: `PATCH /api/lists/target`, расширил `stats.js`, добавил `db.py` в deploy_quick FILES

### Инфра
- `deploy_quick.py` написан — upload 7 (потом Codex расширил до 13) файлов + restart dashboard, 60 сек vs 15 мин `deploy.py`
- Зомби uvicorn прибит (висел 4+ ч с Playwright-теста)

## Ближайшие шаги

### 1. Ждём Codex
- [ ] Закончит алерт-фичу: `list_items` миграция, UI 🔴/🟢 инпуты в модалке, триггер в `_refresh_prices`, TG-integration
- [ ] Оставшиеся пункты item detail: `name_ru`, крупнее картинка, ярче «Тайное»

### 2. От Ники (нужно сделать)
- [ ] Положить `LESHA_TG_CHAT_ID=...` в `/opt/steam-sniper/.env` на VPS (без этого Codex не сможет закончить TG-integration)
- [ ] Проверить что cron на cortex-vm стабильно отрабатывает snapshot: `gcloud compute ssh cortex-vm --zone=europe-west3-b --command="tail -50 ~/sync_steam_sniper_snapshot.log"`

### 3. Steam Sniper — на потом
- [ ] Web push для алертов (Лёхе TG через VPN неудобно — просил альтернативу)
- [ ] Когда cortex-vm закроется в мае → перенос snapshot pipeline на новый VPS Timeweb (2 vCPU / 2+ GB RAM, ~1000-1400 ₽/мес)
- [ ] Дизайн-редизайн через Claude Design? Ника хотел попробовать. **Сейчас не трогать** — Codex в активе. После закрытия алерт-PR — ок

### 4. Прочие задачи
- [ ] PharmOrder мониторинг (OOM, sync — неделю смотрим)
- [ ] Klink: Seedance 2.0 — выбрать платформу (Jimeng vs Dreamina)
- [ ] Cypher: Browser Use интеграция — L3 path
- [ ] `/reflect` — накопилось 18 diary, пора
- [ ] Funding: EdgeX verifier
- [ ] Keenetic Hopper — WireGuard VPN
- [ ] USB-микрофон для стационара (Fifine K669B)
- [ ] VoiceType: watchdog для хоткей-листенера (daemon thread умирает)

## Ссылки

### Steam Sniper
- Dashboard: http://72.56.37.150/
- Код: `D:\code\2026\2\cortex\tools\steam-sniper\`
- Brief 1 (item detail expand): `C:\Users\User\Desktop\STEAM_SNIPER_CODEX_ITEM_DETAIL_EXPAND.md`
- Brief 2 (alerts): `C:\Users\User\Desktop\STEAM_SNIPER_CODEX_ALERTS.md`
- Старые брифинги: `STEAM_SNIPER_CODEX_BRIEFING.md`, `STEAM_SNIPER_PERFORMANCE_BRIEFING.md`
- Snapshot builder на VM: `~/sync_steam_sniper_snapshot.sh`, лог `~/sync_steam_sniper_snapshot.log`
- Cron на VM: `0 */4 * * *`
- Quick deploy: `cd tools/steam-sniper && uv run python deploy_quick.py` (60 сек)

### PharmOrder
- Dashboard: http://194.87.140.204:8000
- Код (VPS): `/opt/pharmorder/src/`
- Sync standalone (мама): `E:\новый склит смнк\sklit_syncV3\sync_standalone.py`

### Инфра
- cortex-vm: `gcloud compute ssh cortex-vm --zone=europe-west3-b` (закроется в мае)
- VPS Steam Sniper: `ssh -i ~/.ssh/vps_key root@72.56.37.150`
- VPS PharmOrder: 194.87.140.204 (paramiko из Python)
- VoiceType / Cypher: `D:\code\2026\3\voice-type`
- Субагент playbook: `memory/subagents-playbook.md`
