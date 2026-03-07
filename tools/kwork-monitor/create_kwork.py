"""Create kworks on Kwork via Playwright with proxy.

Proven approach:
- Title: contenteditable div #editor-title → keyboard.type()
- Category: jQuery trigger on selects with Chosen.js
- Type/Вид/Платформа: labels in #kwork-save-attributes → Playwright click
- Cover: input[name="first-kwork-photo[]"] → set_input_files()
- Продолжить: DIV.js-next-step-btn → Playwright get_by_text().click()
- Description/Instruction: trumbowyg innerHTML + textarea value
- Price/Duration: jQuery trigger on selects
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright, Page

# Load .env
ENV_PATH = Path(__file__).parent.parent.parent / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

PROXY = {
    "server": "http://45.135.29.96:8000",
    "username": "oeozTg",
    "password": "A0Vn3M",
}

KWORK_LOGIN = os.environ.get("KWORK_LOGIN", "")
KWORK_PASSWORD = os.environ.get("KWORK_PASSWORD", "")

PARENT_CAT_VALUE = "11"  # Разработка и IT
SUB_CAT_VALUE = "41"  # Скрипты, боты и mini apps

COVER_DIR = Path(__file__).parent / "covers"

KWORKS = [
    {
        "title": "Разработаю Telegram-бота на Python под ваши задачи",
        "type_radio": "Чат-боты",
        "vid_radio": "Написание и доработка",
        "languages": ["Python"],
        "platforms": ["Telegram"],
        "description": (
            "Разработаю Telegram-бота любой сложности на Python (aiogram).\n\n"
            "Что могу сделать:\n"
            "-- Бот с меню, кнопками, инлайн-клавиатурой\n"
            "-- Интеграция с базой данных (SQLite, PostgreSQL)\n"
            "-- Прием платежей (ЮKassa, Робокасса)\n"
            "-- Подключение к внешним API (CRM, Google Sheets, 1С)\n"
            "-- Парсинг и автопостинг в каналы\n"
            "-- Бот-помощник с AI (ChatGPT, Claude, Gemini)\n"
            "-- Уведомления, рассылки, автоответчики\n\n"
            "Что вы получите:\n"
            "-- Чистый, документированный код\n"
            "-- Инструкцию по запуску и настройке\n"
            "-- Деплой на ваш сервер (VPS)\n"
            "-- 7 дней бесплатной поддержки после сдачи\n\n"
            "Стек: Python 3.12, aiogram 3, SQLite/PostgreSQL, Docker\n\n"
            "Перед заказом напишите в личку -- обсудим ТЗ и сроки."
        ),
        "instruction": (
            "Чтобы начать работу, мне потребуется:\n"
            "1. Описание функционала бота (что должен делать)\n"
            "2. Примеры похожих ботов (если есть)\n"
            "3. Доступы к API/сервисам для интеграции (если нужны)\n"
            "4. Токен бота от @BotFather (или создам сам)"
        ),
        "price": "5000",
        "days": "5",
        "cover_color": (30, 60, 114),
    },
    {
        "title": "Спаршу данные с любого сайта в удобном формате",
        "type_radio": "Парсеры",
        "vid_radio": "Написание и доработка",
        "languages": ["Python"],
        "platforms": ["Сайт"],
        "description": (
            "Соберу данные с любого сайта: каталоги, цены, контакты, отзывы, товары.\n\n"
            "Что парсю:\n"
            "-- Интернет-магазины (товары, цены, характеристики, фото)\n"
            "-- Справочники и каталоги (2GIS, Яндекс.Карты, Avito)\n"
            "-- Сайты с JavaScript-рендерингом (SPA, React, Vue)\n"
            "-- Сайты с защитой от парсинга (Cloudflare, капчи)\n"
            "-- Соцсети (посты, комментарии, профили)\n\n"
            "Что вы получите:\n"
            "-- Данные в удобном формате: CSV, Excel, JSON или БД\n"
            "-- Скрипт для регулярного обновления (по запросу)\n"
            "-- Документацию и инструкцию\n\n"
            "Стек: Python, Scrapy, Playwright, BeautifulSoup\n\n"
            "Объемы: от 100 до 1 000 000+ записей.\n"
            "Перед заказом напишите -- оценю сложность бесплатно."
        ),
        "instruction": (
            "Чтобы начать работу, мне потребуется:\n"
            "1. Ссылка на сайт для парсинга\n"
            "2. Какие именно данные нужны (поля)\n"
            "3. Желаемый формат результата (CSV, Excel, JSON)\n"
            "4. Примерный объем данных"
        ),
        "price": "3000",
        "days": "3",
        "cover_color": (20, 100, 60),
    },
    {
        "title": "Создам AI чат-бота с базой знаний для бизнеса",
        "type_radio": "ИИ-боты",
        "vid_radio": "Написание и доработка",
        "languages": ["Python"],
        "platforms": ["Telegram", "Сайт"],
        "description": (
            "Сделаю умного чат-бота, который отвечает клиентам на основе ваших документов.\n\n"
            "Как это работает:\n"
            "-- Загружаете свои документы (FAQ, инструкции, каталог, прайс)\n"
            "-- Бот изучает материалы и отвечает на вопросы клиентов\n"
            "-- Не выдумывает -- только на основе ваших данных\n"
            "-- Если не знает ответ -- переводит на оператора\n\n"
            "Где работает:\n"
            "-- Telegram-бот\n"
            "-- Виджет на сайте\n"
            "-- WhatsApp (через API)\n\n"
            "Что под капотом:\n"
            "-- RAG -- поиск по базе знаний + генерация ответа\n"
            "-- Модели: Claude API, GPT-4, Gemini -- выбираем под бюджет\n"
            "-- Векторная база: ChromaDB или Pinecone\n\n"
            "Что вы получите:\n"
            "-- Работающий бот с вашей базой знаний\n"
            "-- Админ-панель для обновления документов\n"
            "-- Деплой на сервер + 14 дней поддержки\n\n"
            "Напишите -- покажу демо и оценю объем работ."
        ),
        "instruction": (
            "Чтобы начать работу, мне потребуется:\n"
            "1. Документы для базы знаний (FAQ, инструкции, прайс -- любой формат)\n"
            "2. Где должен работать бот (Telegram, сайт, WhatsApp)\n"
            "3. Примеры вопросов, на которые бот должен отвечать\n"
            "4. Предпочтения по AI-модели и бюджету на API"
        ),
        "price": "10000",
        "days": "7",
        "cover_color": (80, 30, 100),
    },
]


def generate_cover(title: str, color: tuple, index: int) -> Path:
    """Generate cover image 660x440."""
    COVER_DIR.mkdir(exist_ok=True)
    path = COVER_DIR / f"cover_{index}.png"

    img = Image.new("RGB", (660, 440), color)
    draw = ImageDraw.Draw(img)

    # Gradient
    for y in range(440):
        a = y / 440
        r = int(color[0] * (1 - a * 0.5))
        g = int(color[1] * (1 - a * 0.5))
        b = int(color[2] * (1 - a * 0.3))
        draw.line([(0, y), (659, y)], fill=(r, g, b))

    try:
        font = ImageFont.truetype("arial.ttf", 28)
        small_font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
        small_font = font

    # Word wrap
    words = title.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > 580:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    lh = 38
    y_start = (440 - len(lines) * lh) // 2
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (660 - (bbox[2] - bbox[0])) // 2
        draw.text((x, y_start + i * lh), line, fill=(255, 255, 255), font=font)

    tagline = "Python  |  AI  |  Automation"
    bbox = draw.textbbox((0, 0), tagline, font=small_font)
    x = (660 - (bbox[2] - bbox[0])) // 2
    draw.text((x, 400), tagline, fill=(200, 200, 200), font=small_font)

    # Add subtle pattern to increase file size > 30KB
    import random
    random.seed(index)
    for _ in range(2000):
        rx, ry = random.randint(0, 659), random.randint(0, 439)
        rc = tuple(max(0, min(255, c + random.randint(-15, 15))) for c in img.getpixel((rx, ry)))
        draw.point((rx, ry), fill=rc)

    # Save as PNG (ensure > 30KB)
    img.save(path, "PNG")
    size_kb = path.stat().st_size / 1024
    if size_kb < 30:
        # Fallback: save as high-quality JPEG
        path = path.with_suffix(".jpg")
        img.save(path, "JPEG", quality=95)
        size_kb = path.stat().st_size / 1024
    print(f"  Cover size: {size_kb:.0f} KB", flush=True)
    return path


async def login(page: Page) -> None:
    print(">> Logging in...", flush=True)
    await page.goto("https://kwork.ru/login", wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(3)
    await page.wait_for_selector('input[type="password"]', timeout=15000)
    await page.get_by_placeholder("почта").or_(page.get_by_placeholder("логин")).first.fill(KWORK_LOGIN)
    await page.get_by_placeholder("Пароль").first.fill(KWORK_PASSWORD)
    await page.get_by_role("button", name="Войти").first.click()
    await asyncio.sleep(6)
    print(f">> Logged in: {page.url}", flush=True)


async def click_next_step(page: Page, step: str) -> None:
    """Click the first visible 'Продолжить' div button."""
    btns = page.get_by_text("Продолжить", exact=True)
    count = await btns.count()
    for i in range(count):
        if await btns.nth(i).is_visible():
            await btns.nth(i).scroll_into_view_if_needed()
            await btns.nth(i).click()
            print(f"  [{step}] Clicked Продолжить [{i}]", flush=True)
            await asyncio.sleep(3)
            return
    print(f"  [{step}] No visible Продолжить found!", flush=True)


async def create_one_kwork(page: Page, kw: dict, index: int) -> bool:
    num = index + 1
    print(f"\n{'='*60}", flush=True)
    print(f">> [{num}/3] {kw['title'][:55]}", flush=True)

    await page.goto("https://kwork.ru/new", wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(4)

    attrs = page.locator("#kwork-save-attributes")

    # ═══════════════════════════════════════
    # STEP 1: Title + Category + Type + Cover
    # ═══════════════════════════════════════
    print(f"  [STEP 1]", flush=True)

    # Title
    await page.locator("#editor-title").click()
    await page.keyboard.type(kw["title"], delay=15)
    await asyncio.sleep(0.5)
    await page.evaluate("""(t) => {
        const ta = document.querySelector('textarea[name="title"]');
        if (ta) { ta.value = t; ta.dispatchEvent(new Event('input', {bubbles:true})); }
    }""", kw["title"])
    print(f"  Title OK ({len(kw['title'])} chars)", flush=True)

    # Parent category
    await page.evaluate("""() => {
        const sels = document.querySelectorAll('select');
        for (const s of sels) {
            for (const o of s.options) {
                if (o.value === '11') { jQuery(s).val('11').trigger('chosen:updated').trigger('change'); return; }
            }
        }
    }""")
    await asyncio.sleep(3)

    # Subcategory
    await page.evaluate("""() => {
        jQuery('select[name="category_id"]').val('41').trigger('chosen:updated').trigger('change');
    }""")
    await asyncio.sleep(2)
    print(f"  Category OK", flush=True)

    # Type radio
    await attrs.get_by_text(kw["type_radio"], exact=True).click()
    await asyncio.sleep(1)
    print(f"  Type: {kw['type_radio']}", flush=True)

    # Вид radio
    try:
        await attrs.get_by_text(kw["vid_radio"], exact=True).click()
        print(f"  Вид: {kw['vid_radio']}", flush=True)
    except Exception:
        print(f"  Вид: not found (may not exist for this type)", flush=True)
    await asyncio.sleep(0.5)

    # Язык разработки checkboxes (REQUIRED)
    for lang in kw.get("languages", ["Python"]):
        try:
            await attrs.get_by_text(lang, exact=True).click()
            print(f"  Язык: {lang}", flush=True)
        except Exception:
            print(f"  Язык {lang}: not found", flush=True)
    await asyncio.sleep(0.5)

    # Платформа checkboxes
    for plat in kw.get("platforms", []):
        try:
            await attrs.get_by_text(plat, exact=True).click()
            print(f"  Платформа: {plat}", flush=True)
        except Exception:
            print(f"  Платформа {plat}: not found", flush=True)
    await asyncio.sleep(0.5)

    # Cover image
    cover_path = generate_cover(kw["title"], kw["cover_color"], index)
    cover_input = page.locator('input[name="first-kwork-photo[]"]')
    if await cover_input.count() > 0:
        await cover_input.set_input_files(str(cover_path))
        await asyncio.sleep(3)
        print(f"  Cover: uploaded", flush=True)
    else:
        print(f"  Cover: input not found", flush=True)

    await page.screenshot(path=f"kwork_s1_{index}.png")

    # Click Продолжить for step 1
    await click_next_step(page, "step1")

    # Verify step 2 expanded
    step2_ok = await page.evaluate("""() => {
        const el = document.querySelector('#step1-description');
        return el && el.offsetParent !== null;
    }""")
    if not step2_ok:
        print(f"  !! Step 2 did NOT expand", flush=True)
        # Check errors
        errors = await page.evaluate("""() => {
            const errs = [];
            document.querySelectorAll('[class*="error"]').forEach(e => {
                if (e.offsetParent !== null && e.textContent.trim() && !e.classList.contains('hidden'))
                    errs.push(e.textContent.trim().substring(0, 80));
            });
            return errs.slice(0, 5);
        }""")
        if errors:
            print(f"  Errors: {errors}", flush=True)
        await page.screenshot(path=f"kwork_err_{index}.png")
        return False

    # ═══════════════════════════════════════
    # STEP 2: Description + Instruction
    # ═══════════════════════════════════════
    print(f"  [STEP 2]", flush=True)
    await asyncio.sleep(1)

    desc_html = kw["description"].replace("\n", "<br>")
    await page.evaluate("""(args) => {
        const ta = document.querySelector('#step1-description');
        const box = ta?.closest('.trumbowyg-box');
        const ed = box?.querySelector('.trumbowyg-editor');
        if (ed) {
            ed.innerHTML = args.html;
            ed.dispatchEvent(new Event('input', {bubbles:true}));
            ed.dispatchEvent(new Event('blur', {bubbles:true}));
        }
        if (ta) {
            ta.value = args.html;
            ta.dispatchEvent(new Event('input', {bubbles:true}));
            if (window.jQuery) jQuery(ta).val(args.html).trigger('tbwchange').trigger('change');
        }
    }""", {"html": desc_html})
    print(f"  Description OK", flush=True)

    instr_html = kw["instruction"].replace("\n", "<br>")
    await page.evaluate("""(args) => {
        const ta = document.querySelector('#step1-instruction');
        const box = ta?.closest('.trumbowyg-box');
        const ed = box?.querySelector('.trumbowyg-editor');
        if (ed) {
            ed.innerHTML = args.html;
            ed.dispatchEvent(new Event('input', {bubbles:true}));
            ed.dispatchEvent(new Event('blur', {bubbles:true}));
        }
        if (ta) {
            ta.value = args.html;
            ta.dispatchEvent(new Event('input', {bubbles:true}));
            if (window.jQuery) jQuery(ta).val(args.html).trigger('tbwchange').trigger('change');
        }
    }""", {"html": instr_html})
    print(f"  Instruction OK", flush=True)

    await page.screenshot(path=f"kwork_s2_{index}.png")
    await click_next_step(page, "step2")

    # ═══════════════════════════════════════
    # STEP 3: Price + Duration
    # ═══════════════════════════════════════
    print(f"  [STEP 3]", flush=True)
    await asyncio.sleep(1)

    await page.evaluate("""(p) => {
        jQuery('select[name="min_volume_price"]').val(p).trigger('chosen:updated').trigger('change');
    }""", kw["price"])
    print(f"  Price: {kw['price']}", flush=True)

    await page.evaluate("""(d) => {
        jQuery('select[name="work_time"]').val(d).trigger('chosen:updated').trigger('change');
    }""", kw["days"])
    print(f"  Days: {kw['days']}", flush=True)

    await page.screenshot(path=f"kwork_s3_{index}.png")

    # After step 3, try "Продолжить" or skip to "Готово"
    btns = page.get_by_text("Продолжить", exact=True)
    found_visible = False
    for i in range(await btns.count()):
        if await btns.nth(i).is_visible():
            await btns.nth(i).scroll_into_view_if_needed()
            await btns.nth(i).click()
            print(f"  [step3] Clicked Продолжить [{i}]", flush=True)
            found_visible = True
            await asyncio.sleep(2)
            break
    if not found_visible:
        print(f"  [step3] No Продолжить, looking for Готово", flush=True)

    # ═══════════════════════════════════════
    # FINAL: Click "Готово" to publish
    # ═══════════════════════════════════════
    print(f"  [PUBLISH]", flush=True)
    await asyncio.sleep(2)

    # Find and click "Готово" button
    gotovo = page.get_by_text("Готово", exact=True)
    gotovo_count = await gotovo.count()
    print(f"  'Готово' buttons: {gotovo_count}", flush=True)

    clicked = False
    for i in range(gotovo_count):
        if await gotovo.nth(i).is_visible():
            await gotovo.nth(i).scroll_into_view_if_needed()
            await gotovo.nth(i).click()
            print(f"  Clicked 'Готово' [{i}]", flush=True)
            clicked = True
            break

    if not clicked:
        # Fallback: try .js-save-kwork
        save_btn = page.locator('.js-save-kwork')
        if await save_btn.count() > 0 and await save_btn.first.is_visible():
            await save_btn.first.click()
            print(f"  Clicked .js-save-kwork (fallback)", flush=True)
        else:
            print(f"  No publish button found!", flush=True)

    await asyncio.sleep(5)
    await page.screenshot(path=f"kwork_done_{index}.png")
    print(f"  URL: {page.url}", flush=True)
    return True


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, proxy=PROXY)
        ctx = await browser.new_context(viewport={"width": 1280, "height": 900}, locale="ru-RU")
        page = await ctx.new_page()

        await login(page)

        for i, kw in enumerate(KWORKS):
            try:
                await create_one_kwork(page, kw, i)
            except Exception as e:
                print(f"!! Error kwork {i+1}: {e}", flush=True)
                import traceback
                traceback.print_exc()
                await page.screenshot(path=f"kwork_error_{i}.png")

        await browser.close()
        print("\n>> All done!", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
