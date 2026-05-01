<!-- L0: Concentrated lookup-журнал production-инцидентов и фиксов. -->
# Learned the Hard Way

> Концентрированный lookup. Каждая запись: **симптом → причина → фикс** с конкретной командой или изменением. Расширенные истории — в `~/.claude/projects/.../memory/diary/`. Высокоуровневые правила-привычки — в `feedback_*.md` и `CLAUDE.md` Conventions.
>
> Это **не** замена `/reflect`-цикла. Это **дополнение**: когда приходит симптом «уже видел это», лезу сюда первым делом. Если симптома нет — это не панацея.
>
> Формат заточен под `grep`. Не редактируй описание стиля — нарушится lookup-привычка.

---

## 1. Hooks & защитная сетка

### Pre-commit hook false-green месяц
**Симптом:** все коммиты «проходят» тесты, но реально тесты не запускаются.
**Причина:** `scripts/ops.sh` и `.git/hooks/pre-commit` ссылались на удалённые `tools/heartbeat`, `tools/pipeline`, `tools/scaffold`. Цикл `for d in tools/heartbeat ...` ломается на отсутствующей директории, exit code 0, hook молчит.
**Фикс:**
```bash
# scripts/ops.sh
TOOLS_WITH_TESTS="tools/steam-sniper tools/metrics"
# .git/hooks/pre-commit:11
for d in tools/steam-sniper tools/metrics; do
# verify
bash scripts/ops.sh test  # должно показать 116 passed (104 + 12)
```
**Урок:** при удалении тула — `grep -r <tool-name>` по всему репо. Чистить hooks/scripts/commands/docs. Ужесточил в `CLAUDE.md` Conventions.
**Источник:** diary 016 (удаление), diary 021 (поимка через external audit).

### `pytest: program not found` при `ops.sh test`
**Симптом:** на новом клоне `bash scripts/ops.sh test` падает с `program not found: pytest`.
**Причина:** `pytest` сидел в `[project.optional-dependencies].dev` тула, `uv sync --quiet` без `--extra dev` его не ставит.
**Фикс:** перенести `pytest` в **основные** dependencies. Steam-sniper — внутренний тул, dev/prod разделение не нужно.
**Источник:** diary 021.

### `scripts/.claude/` появляется как untracked артефакт
**Симптом:** в `git status` появляется `scripts/.claude/settings.local.json` и agent-memory.
**Причина:** запуск Claude Code из subdir `scripts/` создаёт там свой `.claude/`.
**Фикс:**
```
# .gitignore
scripts/.claude/
```
И запускать `claude` только из root репо.
**Источник:** diary 020.

### Playwright MCP дампит скрины и кеш в cwd
**Симптом:** в `scripts/` появились 26 PNG + папка `.playwright-mcp/` с mp3, page snapshots, console logs.
**Причина:** Playwright MCP пишет в текущую рабочую директорию которой запущен Claude.
**Фикс:**
```
# .gitignore
scripts/*.png
.playwright-mcp/
```
Зафиксировать в `feedback_playwright-cwd.md`.
**Источник:** diary 020.

---

## 2. Memory & контекст

### Diary расщеплён на две папки
**Симптом:** `/reflect` не видит сессии 009-019.
**Причина:** старые 001-005 в `.claude/projects/.../memory/diary/`, новые 009-019 в `memory/diary/` репо. `pre-compact.py` писал в одну, ручной `/diary` — в другую.
**Фикс:** перенести всё в **per-user shared folder** `~/.claude/projects/D--code-2026-2-cortex/memory/diary/`. Обновить `pre-compact.py`:
```python
USER_PROJECT_DIR = Path.home() / ".claude" / "projects" / "D--code-2026-2-cortex"
DIARY_DIR = USER_PROJECT_DIR / "memory" / "diary"
```
И `/diary`, `/reflect`, `/handoff` команды — пути обновить.
**Урок:** diary должен жить в одном месте, иначе двойной источник правды = драм.
**Источник:** diary 020.

### `eval/SKILL.md` ссылается на стейл путь `memory/MEMORY.md`
**Симптом:** scan-skills.py показывает broken ref.
**Причина:** после миграции MEMORY.md в per-user folder, старые ссылки в скиллах остались.
**Фикс:** заменить на абсолютный per-user путь:
```
~/.claude/projects/D--code-2026-2-cortex/memory/MEMORY.md
```
**Источник:** diary 030 (сегодня), scan-skills broken refs.

### MEMORY.md обрезается после 200 строк
**Симптом:** правила из конца файла не применяются.
**Причина:** Claude Code загружает в system prompt только первые ~200 строк MEMORY.md.
**Фикс:** держать индекс ≤ 200 строк. Содержание выносить в feedback/project/personal/reference-файлы. Каждая строка ≤ 150 символов.
**Источник:** Claude Code docs + experimental verification.

---

## 3. Codex parallel work

### Дубль кода — переоткрыл фичу которую Codex уже сделал
**Симптом:** написал `item_detail.js`, после мерджа выяснилось что Codex запушил **идентичный** код раньше.
**Причина:** не проверил `git fetch && git log origin/codex-branch` перед началом. Сидел на codex-ветке не зная.
**Фикс:**
```bash
git status                        # какая ветка
git fetch origin
git log origin/<codex-branch> -10 # что Codex уже сделал
```
ДО написания кода. Если 7/7 пунктов брифа уже в коде — задача закрыта.
**Источник:** diary 017, 019.

### 502 на проде после `deploy_quick.py`
**Симптом:** `fastapi.exceptions.FastAPIError: Invalid args for response field! ... JSONResponse | dict is a valid Pydantic field type`.
**Причина:** Codex параллельно поставил `-> JSONResponse | dict` в `PATCH /api/lists/target`. FastAPI не может сгенерить `response_model` из Union с `dict`.
**Фикс:**
```python
@app.patch("/api/lists/target", response_model=None)
```
**Урок:** перед `deploy_quick.py` если Codex активен — `git pull` + локальный `pytest`.
**Источник:** diary 018.

---

## 4. Subagents (галлюцинации и верификация)

### Researcher выдумал stars и порог tool calls для Hermes
**Симптом:** subagent сказал «Hermes Agent — 22k stars, v0.9.0 апрель 2026: 64k».
**Реальность:** `gh api repos/NousResearch/hermes-agent` → **126,511 stars**. Версии и пороги тоже выдуманы.
**Фикс:**
- Researcher → Sonnet (Haiku мажет на числах)
- В `.claude/agents/researcher.md`: правило «любое число — обязательная верификация через `gh api` / `curl -I` / `Read`. Иначе пиши "не проверено"»
- Confidence-маркеры на каждом факте: `[✅ verified: <tool>]` / `[⚠️ unverified]` / `[🟡 inferred]`
- Запрет сравнительных таблиц без верификации каждой ячейки
**Источник:** diary 030, lesson 2026-04-30.

### Researcher: «auth не нужен» — реально нужен
**Симптом:** subagent сказал «авторизация не требуется для `api.lis-skins.com/v1/market/search`».
**Реальность:** `curl ...` → `{"error":"missing_api_key"}`.
**Фикс:** перед использованием выводов subagent на критичный путь — верифицировать прямым `curl` / `Read`.
**Источник:** diary 017, lesson 2026-03-11.

### `subagent-type: researcher` — нашёл API, не проверил содержимое БД
**Симптом:** subagent сказал «API endpoints не реализованы». Реально были в `server.py`.
**Причина:** субагент описал поверхностное наблюдение, не открыл файл.
**Фикс:** в координаторе после ответа subagent — `grep` по конкретному имени.
**Источник:** lesson 2026-03-11.

---

## 5. VoiceType / Cypher

### Autostart не поднимался после логона
**Симптом:** `Error querying device -1` при старте, VoiceType умер.
**Причина:** USB-микрофон DJI / Fifine K669B не успевал проиниться до запуска `pythonw`.
**Фикс:**
1. `voice_type/main.py:51-67` — retry-loop 30 попыток × 1 сек вокруг `check_microphone_access()`
2. `scripts/voicetype.vbs` — `WScript.Sleep 10000` перед стартом pythonw
3. Watchdog-цикл в VBS: каждые 30с `WMI: SELECT ... WHERE CommandLine LIKE '%voice_type.main%'`. Если воркер мертв — поднять.
**Источник:** diary 017, 020.

### Paste длинных сообщений в Claude Code 4.7 дробил аудио
**Симптом:** одно голосовое разделялось на N сообщений.
**Причина:** Gemini cleanup-промпт говорил «add blank lines between logical blocks» → `\n\n` в тексте → `paste.py` делил по `\n` и жал Shift+Enter → Claude Code 4.7 интерпретировал как submit.
**Фикс:**
1. `voice_type/llm.py` промпт: `"single paragraph, no blank lines"`
2. `voice_type/paste.py` — убрать split+Shift+Enter, делать **один** paste целиком
3. Нормализация: `re.sub(r'\n\s*\n+', '\n', text)` — защита если Gemini проигнорит
**Источник:** diary 017.

### `pythonw.exe` × 2 — не дубль, а norm
**Симптом:** в Task Manager два процесса `pythonw.exe`.
**Причина:** `.venv\Scripts\pythonw.exe` это launcher-shim uv venv на Windows, всегда спавнит base Python (`Python312\pythonw.exe`) как child. Один логический процесс, два OS-процесса.
**Фикс:** не паниковать. Добавить audit-hook через `sys.addaudithook` если хочется проверить кто кого спавнит. WMI: `Get-Process pythonw | Format-List CommandLine` покажет разные cmdlines у parent и child.
**Источник:** diary 019.

---

## 6. PharmOrder

### «Касса пишет не выгрузила, а на VPS есть»
**Симптом:** клиент жалуется что заказ не ушёл, но в БД на VPS он есть.
**Причина:** неидемпотентный `POST /api/export`. Ответ теряется после записи pending — клиент ретраит, на VPS дубль.
**Фикс:** UUID `request_id` через клиент-сервер flow:
1. `server.py` — кэш по `request_id` (deduplication 24h TTL)
2. `index.html` — генерация UUID + retries + `AbortController(timeout=20s)`
3. `cashbox_app.py` + `relay_server.py` — batch_id дедуп
4. `sync_standalone.py` — локальный `zayava_written.json` dedup
**Источник:** diary 019, project_pharmorder-fixes.md.

### `escape_markdown` сломал импорт
**Симптом:** apteka-bot падает на `ImportError`.
**Причина:** Python `replace` зацепил «хвост» import-строки: `from telegram.helpers import escape_markdown, KeyboardButton, ...` стал `from telegram.helpers import escape_markdown` (потерял остальное).
**Фикс:**
1. Скачать файл локально
2. Нормализовать line endings (CRLF → LF — иначе re-replace мажет)
3. Точечный Edit-tool, не sed
4. Залить обратно через paramiko, рестартнуть сервис
**Урок:** для multi-line фикса на удалённом сервере — скачать локально, редактировать tools, залить обратно. Не `sed -i` на проде.
**Источник:** diary 019.

### `parse_mode="Markdown"` — exception на первой итерации
**Симптом:** бот шлёт «Необработанные: 15 шт.» без списка.
**Причина:** в `order.products` (название препарата) попадал символ из `* _ [ ] ( ) \``. Telegram находил незакрытый entity, exception прерывал цикл.
**Фикс:**
```python
from telegram.helpers import escape_markdown
text = escape_markdown(str(order.products), version=1)
```
`version=2` — для MarkdownV2 (другие правила escaping).
**Источник:** diary 019.

---

## 7. Steam Sniper

### `Object of type Decimal is not JSON serializable`
**Симптом:** endpoint возвращает пустые листинги.
**Причина:** ijson decoder возвращает `Decimal` для чисел в JSON. `json.dumps()` не сериализует.
**Фикс:** в `_slim_listing()`:
```python
def to_jsonable(v):
    if isinstance(v, Decimal):
        return float(v)
    return v
```
Применять ко всем числовым полям при сборке response.
**Источник:** diary 017 (Codex bug 651e149).

### Snapshot pipeline на cortex-vm не успевал — JSON 818 МБ
**Симптом:** «первый разбор lis-skins до 30 сек» висит минутами.
**Причина:** оценил `api_csgo_full.json` в 30-80 МБ. Реально — **818 МБ**. Warm-loop на 1 vCPU не успевал.
**Фикс:** `curl -I https://...` ДО архитектурной оценки. Меряй прежде чем решать. Решение:
1. `listings_snapshot.py` — build/read API для SQLite
2. `scripts/build_listings_snapshot.py` — CLI обёртка
3. `scripts/sync_listings.ps1` — PowerShell билд+scp
4. cron на cortex-vm: `0 */4 * * *`
**Замер:** build 1 866 205 листингов за 38 сек; cold-click на VPS — 356 мс (было минутами).
**Источник:** diary 017.

### Кейсы попадали в скины (`AK-47 | Case Hardened`)
**Симптом:** в табе «Кейсы» появляются ножи и винтовки.
**Причина:** в `category.py` проверка `"Case" in clean` шла **до** weapon-lookup.
**Фикс:** перенести порядок проверок: weapon → state → case. Ограничить case-match на base-часть до `|`.
**Источник:** diary 018.

### Картинки скинов 404 (`AK-47 | Case Hardened`)
**Симптом:** в `cases.js` картинки не грузятся.
**Причина:** строилось как `STEAM_IMG_BASE + item.url` где `url` — lis-skins href.
**Фикс:** заменить на `item.image` (как в `catalog.js`).
**Источник:** diary 018.

### Картинки ножей с Doppler phase — 404
**Симптом:** 486 ножей без фото из 3519.
**Причина:** ByMykel хранит Doppler как один ключ на нож, lis-skins продаёт каждую фазу отдельным предметом.
**Фикс:** `_get_item_image` — третий fallback регексом:
```python
DOPPLER_RE = r"\s+(phase\s+\d|ruby|sapphire|black\s+pearl|emerald)$"
```
Strip suffix перед lookup. **486 → 0 ножей без фото.**
**Источник:** diary 018.

### Chromium кэширует JS без revalidation
**Симптом:** обновил `cases.js`, но в браузере старая версия даже после deploy.
**Причина:** browser heuristic freshness — кэширует JS как «свежий» без `Cache-Control`.
**Фикс:** middleware в `server.py`:
```python
@app.middleware("http")
async def no_cache(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response
```
Браузер делает conditional GET с ETag.
**Источник:** diary 018.

### Service Worker не обновляется на мобильном (нет hard-refresh)
**Симптом:** на iPhone у юзера старая версия после deploy.
**Причина:** SW кэширует static, версия не bumped.
**Фикс:**
```js
const CACHE_NAME = "sniper-v5";  // bump при каждом обновлении static
const STATIC_ASSETS = ["item_detail.js", "theme.js", ...];
```
Плюс cache-busting через `?v=20260423-bN` в URL ассетов.
**Источник:** diary 020, 024.

### vps_key SSH `Permission denied`
**Симптом:** `ssh -i ~/.ssh/vps_key root@72.56.37.150` → `Permission denied (publickey)`.
**Причина:** `vps_key` от **PharmOrder** VPS (194.87.140.204), не Steam Sniper VPS.
**Фикс:** для Steam Sniper генерить отдельный `~/.ssh/id_ed25519_steamsniper` или использовать пароль.
**Источник:** diary 020.

---

## 8. Cortex-vm / GCP

### VM зависла после OOM
**Симптом:** SSH timeout, HTTP не отвечает, статус `RUNNING`.
**Причина:** kernel OOM прибил `uvicorn` (1.7 GB), система ушла в swap-thrash.
**Фикс:**
```bash
gcloud compute instances get-serial-port-output cortex-vm --zone=europe-west3-b --port=1 | tail -50
# увидишь: "Out of memory: Killed process 747 (uvicorn)"

gcloud compute instances reset cortex-vm --zone=europe-west3-b
# ждать 1-2 минуты, потом ssh
```
Профилактика: `MemoryMax=1500M` в systemd unit, `OOMScoreAdjust=500`.
**Источник:** diary 019.

### Snapshot cron на VM → VPS — старый IP в `deploy.py`
**Симптом:** `print` инструкция ссылается на 194.87.140.204 (PharmOrder), а snapshot уезжает на 72.56.37.150 (Steam Sniper).
**Причина:** copy-paste из старого `deploy.py` PharmOrder.
**Фикс:** перепроверить hardcoded IP в **каждом** новом `deploy.py` под другой проект.
**Источник:** diary 016.

---

## 9. PowerShell / Windows

### `$_` ломается через bash one-liner
**Симптом:** `powershell -Command "Where-Object { $_.FriendlyName -match ... }"` → `extglob.FriendlyName`.
**Причина:** bash интерпретирует `$_` как переменную и подставляет её значение (часто пустое).
**Фикс:**
1. Простая команда без `$_` — норм через bash.
2. Pipeline с `$_` → `.ps1` файл, звать `powershell -File script.ps1`.
3. UTF-8 в .ps1: `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` в начале.
4. Без `-SilentlyContinue` в diagnostic-скриптах — глотает ошибки.
**Источник:** diary 023.

### Кириллица ломает `print` через cp1251
**Симптом:** `UnicodeEncodeError: 'charmap' codec can't encode character '→'`.
**Причина:** Windows console default cp1251, не UTF-8. Любой `→`, эмодзи, кириллица в нестандартных условиях ломают.
**Фикс:** в начале каждого Python-скрипта который пишет в stdout:
```python
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
```
Альтернативно — `PYTHONIOENCODING=utf-8` в env.
**Источник:** diary 016 (deploy.py), 030 (session-search.py).

### Windows path → forward slashes для SFTP
**Симптом:** `_ensure_remote_dir` в `deploy.py` инфинит-луп.
**Причина:** `Path(remote_path).parent` на Windows возвращает backslashes (`\`). SFTP к Linux серверу не понимает.
**Фикс:**
```python
parent = remote_path.rsplit("/", 1)[0]
```
Не `Path(...).parent` для **remote** путей.
**Источник:** diary 016.

### MSI uninstall exit 1603
**Симптом:** `msiexec /x ... /quiet` падает с 1603.
**Причина:** silent uninstall MSI требует elevation.
**Фикс:**
```powershell
Start-Process -Verb RunAs -Wait msiexec.exe -ArgumentList "/x {GUID} /quiet"
```
UAC один раз, потом silent.
**Источник:** diary 023.

### `Clear-RecycleBin -DriveLetter C -Force` не работает
**Симптом:** команда тихо проходит, корзина не очищается.
**Причина:** `-SilentlyContinue` глотает реальные ошибки. Нужен elevation для системной корзины.
**Фикс:** убрать `-SilentlyContinue` чтобы видеть ошибки. Использовать `Start-Process -Verb RunAs powershell -ArgumentList "-Command Clear-RecycleBin -Force"`.
**Источник:** diary 023.

---

## 10. Worktrees

### `huashu-design` skill пропал из worktree
**Симптом:** в одном чате skill не триггерится.
**Причина:** `.claude/skills/huashu-design/` физически отсутствовал в `bold-yonath` worktree. Check-скрипт наврал из-за пропущенного `/` при конкатенации путей.
**Фикс:**
1. Пересинхронить во все 5 копий: `git clone github.com/sashbol/huashu-design ~/.claude/skills/huashu-design`
2. `scripts/fetch_huashu_bgm.sh` — отдельно скачать BGM-ассеты
3. `.gitignore` += `.claude/skills/huashu-design/` (внешний репо, не коммитить)
4. **Урок:** check-скрипт проверки наличия — внимательно со слешами в конкатенации. Один пропущенный `/` = ложный negative.
**Источник:** diary 022.

### Edit в worktree не отражается на main repo
**Симптом:** запустил скрипт через `CLAUDE_PROJECT_DIR` — увидел старую версию.
**Причина:** скрипт смотрит **main** репо `D:\code\2026\2\cortex\.claude\skills/...`, я Edit'ил **worktree** копию.
**Фикс:** при патчах `.claude/skills/` или `.claude/agents/` — Edit нужно в **обоих** местах:
- worktree (текущая сессия)
- main репо (для всех будущих сессий)
Или объединить через `git merge` после.
**Источник:** diary 030.

### Diary номер race на `max+1`
**Симптом:** два чата одновременно посчитают `max(numbers)+1` и запишут в один файл — перезапись.
**Причина:** `find_next_number()` без атомарности.
**Mitigation:** в worktree-эпохе спасало git diff после; после миграции в per-user folder — race остался теоретически, но в практике редкий (минуты между записями).
**Фикс на будущее:** lock-file / `O_EXCL` create или `microsecond_suffix`.
**Источник:** diary 020.

---

## 11. PDF & Editorial

### Edge headless: `break-inside: avoid` на больших блоках = пустые страницы
**Симптом:** в PDF куски пустых страниц перед `.steps` или `.glossary`.
**Причина:** браузер видит «не помещается на текущую страницу» → переносит весь блок на новую → пустота на текущей.
**Фикс:**
```css
@media print {
  .steps > li { break-inside: auto; padding-bottom: 14px; }
  .glossary { break-inside: auto; }
  /* break-inside: avoid — только на КОРОТКИХ блоках: .callout, .recommendation */
}
```
**Источник:** diary 025 (editorial-doc-ru SKILL.md).

### Reportlab не рендерит эмодзи 🔴/🟢/★
**Симптом:** в PDF на месте эмодзи квадратики.
**Причина:** Arial / Arial-Bold не имеют этих glyphs.
**Фикс:** заменить на цветной кружок через Paragraph XML:
```html
<font color='#dc2626'>●</font>  <!-- red -->
<font color='#16a34a'>●</font>  <!-- green -->
```
Или использовать Edge headless + HTML вместо reportlab — `→`, эмодзи рендерятся.
**Источник:** diary 020 (Лёшин zip + PDF).

### Edge `--print-to-pdf`: error message в stdout, но PDF создан
**Симптом:** в логе `ERROR:chrome\browser\task_manager...`. Кажется что упало.
**Причина:** Edge sends task-manager warnings на любой headless запуск. Это **не** ошибка PDF gen.
**Фикс:** не паниковать. Проверять реальный успех: `ls -la output.pdf` или grep `bytes written to file`.
**Источник:** diary 030 (PDF для Артура).

---

## 12. АО ЕСП / СКЛИТ

### ЛК ЕСП висит в demo-режиме
**Симптом:** зарегистрировался через УКЭП, но в кабинете «Demo Company», касса «Demo Model».
**Причина:** регистрировался в **Brave**. Brave даёт демо-режим навсегда.
**Фикс:**
1. **Яндекс.Браузер** (winget install Yandex.Browser)
2. CryptoPro CSP **R3+** (R2 недостаточно для интеграции с Я.Браузером)
3. Расширение CryptoPro Extension из **Opera Addons** (Я.Браузер совместим)
**Урок:** для подтверждения ЕСП — только Я.Браузер + свежая CSP. Гайд `docs/ao-esp-workplace-setup.md`.
**Источник:** diary 023.

### Chrome Web Store недоступен в РФ
**Симптом:** `https://chromewebstore.google.com/detail/...` показывает «Этот продукт недоступен».
**Причина:** Google ограничил доступ для РФ IP с 2024.
**Фикс:**
1. Скачать `.crx` напрямую с сайта вендора (CryptoPro отдаёт отдельным файлом)
2. `brave://extensions/` → Developer mode ON → drag `.crx` на страницу
**Источник:** diary 023.

### `certmgr -inst -cont` для всех контейнеров пакетно
**Симптом:** на Рутокене 6 контейнеров, нужно установить сертификаты в Personal Store.
**Причина:** ручная установка через UI — медленно.
**Фикс:** PowerShell скрипт (`install-certs.ps1`):
```powershell
$containers = csptest -keyset -enum_cont 2>&1 | Select-String "FQCN"
foreach ($c in $containers) {
    certmgr -inst -cont "\\.\Aktiv Rutoken Lite\$($c.Matches[0].Value)"
}
```
PIN на Lite сохранён → 4 сертификата в Personal Store без интерактива.
**Источник:** diary 023.

---

## 13. Web automation

### NotebookLM: Windows console ломает rich
**Симптом:** при запуске tg-monitor через PowerShell — кракозябры в выводе.
**Причина:** rich library использует Unicode characters, cp1251 не справляется.
**Фикс:** запуск с `PYTHONIOENCODING=utf-8`:
```bash
PYTHONIOENCODING=utf-8 uv run python tools/tg-monitor/daily.py
```
Или в `.env`:
```
PYTHONIOENCODING=utf-8
```
**Источник:** MEMORY.md pattern.

### Playwright MCP первый раз подтянул не тот voice
**Симптом:** max-transcriber вернул транскрипт другого голосового.
**Причина:** агент сначала схватил какое-то голосовое про поездку домой, не то что просили.
**Фикс:** в брифе агента — **явная ссылка на конкретное голосовое** (timestamp/длина):
> «длинное голосовое 17:13 про UI, длительность 0:55»
Не «последнее голосовое».
**Источник:** diary 018.

---

## 14. Deploy

### `deploy.py` льёт 648 МБ snapshot — 15 минут
**Симптом:** простой UI-фикс деплоится 15 минут.
**Причина:** `deploy.py` всегда копирует **всё** включая `data/listings_snapshot.db`.
**Фикс:** `deploy_quick.py` — отдельный скрипт. Только 7 файлов (server.py, db.py, lists.js, stats.js, watchlist.js, item_detail.js, theme.js) + `systemctl restart`. **60 секунд** vs 15 минут.
**Источник:** diary 018.

### Systemd service active, но логи показывают ошибку — сервис всё равно работает?
**Симптом:** `systemctl status steam-sniper-dashboard` → `active (running)`, но `journalctl -u steam-sniper-dashboard` показывает traceback.
**Причина:** systemd видит «процесс жив» = active. Не значит «приложение работает корректно».
**Фикс:**
```bash
# Real check:
curl -s http://localhost:8000/api/lists | head -c 100
# Если 502 или HTML вместо JSON — приложение упало внутри.
```
**Источник:** diary 018.

### Browser Console freshness vs prod
**Симптом:** через Playwright — старый `cases.js` несмотря на новый deploy.
**Причина:** Playwright reuses Chromium profile с cached static.
**Фикс:** для real verify через Playwright — `--bypass-csp --disable-cache` flags. Или curl API напрямую без браузера.
**Источник:** diary 018.

---

## 15. Делегирование агентам (Codex / Jules)

### Jules делает PR без описания — ревью невозможен
**Симптом:** PR от Jules с тем что заявлено в issue, но **без** объяснения почему именно так.
**Фикс:** в Issue для Jules — явно прописать «PR description должен содержать: что изменено, почему именно так, какие альтернативы рассматривал».
**Источник:** diary tg-pharma deployment.

### Codex взял задачу но забыл security audit
**Симптом:** код работает, но в нём GH_TOKEN в открытом виде.
**Фикс:** в брифе Codex — секция **Security Constraints**:
> «Никаких credentials в коде. Все секреты — через env. Перед PR — `grep -r "ghp_\|sk-\|password" tools/<scope>/`»
**Источник:** обобщённый паттерн.

### Codex CLI MCP молчит после `reasoningEffort: xhigh`
**Симптом:** MCP-call висит 5+ минут без output.
**Причина:** xhigh реально 5-10 минут на сложной задаче. Это **norm**, не баг.
**Фикс:** не отменять. Подождать. Параллельно делать другую задачу.
**Источник:** practical experience.

---

## Использование

```bash
# Поиск по симптому
grep -i "OOM\|cortex-vm" docs/learned-the-hard-way.md

# Через session-search (включает diary + memory + reflections)
python scripts/session-search.py "PowerShell"

# Если симптом новый и не найден — записать сюда после фикса.
# Формат: ### Заголовок / Симптом / Причина / Фикс с командой / Источник.
```

## Чем отличается от других артефактов

| Где | Что | Когда писать |
|-----|-----|--------------|
| `diary/NNN.md` | История сессии целиком (что делали, решения, проблемы) | Конец каждой сессии |
| `feedback_*.md` | Высокоуровневое правило поведения юзера/агента | Когда юзер скорректировал |
| `learned-the-hard-way.md` (этот) | Lookup recipe: симптом → фикс с командой | Когда поймал production-баг и зафиксил |
| `CLAUDE.md` Conventions | Инвариантные правила проекта | Через `/reflect` после паттерна 2-3+ раз |
| `incidents.md` | Post-mortem серьёзных инцидентов | Через `/incident` после крупного бага |

`learned-the-hard-way.md` ≠ `incidents.md`. Incidents — пост-морпем (что произошло, root cause analysis). Здесь — **расходный справочник**: симптом → команда фикса.

---

> Inspired by Артуром (AGmind, DGX Spark) — у него §8 в CLAUDE.md, 47 правил с командами. У меня формата не было — собрал в отдельный файл.
