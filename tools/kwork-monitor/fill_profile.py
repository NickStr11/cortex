"""Fill Kwork profile via Playwright with proxy."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright

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

# ── Profile content ──
SPECIALTY = "Python-разработчик: боты, парсинг, AI"

ABOUT_HTML = """<div>Python-разработчик. Делаю ботов, парсеры и AI-интеграции, которые реально работают в продакшне.</div>
<div><br></div>
<div><b>Что делаю:</b></div>
<div>— Telegram-боты (aiogram): от простых до сложных с БД, платежами, интеграциями</div>
<div>— Парсинг и скрейпинг (Scrapy, Playwright): сбор данных с любых сайтов, обход защит</div>
<div>— AI-интеграции: чат-боты с базой знаний (RAG), Claude API, Gemini API, GPT</div>
<div>— Автоматизация бизнес-процессов: CRM, синхронизация баз, уведомления</div>
<div>— Backend: FastAPI, PostgreSQL, SQLite</div>
<div><br></div>
<div><b>Реализованные проекты:</b></div>
<div>— Система автоматизации аптеки: сканирование товаров, синхронизация с учётной системой, уведомления в Telegram</div>
<div>— AI-дайджест Telegram-каналов: MapReduce пайплайн, автоанализ 1000+ сообщений в день</div>
<div>— Мониторинг фриланс-площадок: автопоиск проектов + AI-оценка релевантности + алерты</div>
<div><br></div>
<div>Работаю быстро, на связи в Telegram. Перед началом — чёткое ТЗ и сроки.</div>"""


async def login(page) -> None:
    """Login to Kwork."""
    print(">> Opening Kwork login page...", flush=True)
    await page.goto("https://kwork.ru/login", wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(3)

    await page.wait_for_selector('input[type="password"]', timeout=15000)
    await page.get_by_placeholder("почта").or_(page.get_by_placeholder("логин")).first.fill(KWORK_LOGIN)
    await page.get_by_placeholder("Пароль").first.fill(KWORK_PASSWORD)
    await page.get_by_role("button", name="Войти").first.click()
    await asyncio.sleep(6)
    print(f">> Logged in: {page.url}", flush=True)


async def go_to_profile_tab(page) -> None:
    """Navigate to settings and click Profile tab."""
    await page.goto("https://kwork.ru/settings", wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(3)

    # Click Profile tab via JS (SPA)
    result = await page.evaluate("""() => {
        const all = document.querySelectorAll('*');
        for (const el of all) {
            if (el.textContent.trim() === 'Профиль' && el.children.length === 0 && el.offsetParent !== null) {
                const rect = el.getBoundingClientRect();
                if (rect.top > 100 && rect.top < 300) {
                    el.click();
                    return 'clicked at y=' + rect.top;
                }
            }
        }
        return 'not found';
    }""")
    print(f">> Profile tab: {result}", flush=True)
    await asyncio.sleep(4)


async def fill_profile(page) -> None:
    """Fill all profile fields using trumbowyg WYSIWYG editors."""

    # The textareas are trumbowyg editors. We need to set HTML content via JS.
    # textarea[name=fname] = name
    # textarea[name=profession] = specialty
    # textarea[name=details] = about me

    # 1. Set specialty
    print(">> Setting specialty...", flush=True)
    await page.evaluate(f"""(text) => {{
        const ta = document.querySelector('textarea[name="profession"]');
        if (!ta) return 'profession not found';
        // Find the trumbowyg editor div
        const editor = ta.closest('.trumbowyg-box')?.querySelector('.trumbowyg-editor');
        if (editor) {{
            editor.innerHTML = '<div>' + text + '</div>';
            // Trigger input event so Vue picks it up
            editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
            editor.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
        // Also set the textarea directly
        ta.value = '<div>' + text + '</div>';
        ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
        return 'done';
    }}""", SPECIALTY)

    # 2. Set about me (details)
    print(">> Setting about me...", flush=True)
    await page.evaluate(f"""(html) => {{
        const ta = document.querySelector('textarea[name="details"]');
        if (!ta) return 'details not found';
        const editor = ta.closest('.trumbowyg-box')?.querySelector('.trumbowyg-editor');
        if (editor) {{
            editor.innerHTML = html;
            editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
            editor.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
        ta.value = html;
        ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
        return 'done';
    }}""", ABOUT_HTML)

    await asyncio.sleep(2)
    await page.screenshot(path="kwork_profile_filled.png")
    print(">> Fields filled, screenshot saved", flush=True)


async def save_profile(page) -> None:
    """Click save and verify."""
    print(">> Saving...", flush=True)

    # Scroll to save button and click
    save_result = await page.evaluate("""() => {
        const buttons = document.querySelectorAll('button');
        for (const btn of buttons) {
            if (btn.textContent.trim() === 'Сохранить' && btn.offsetParent !== null) {
                btn.scrollIntoView();
                btn.click();
                return 'clicked';
            }
        }
        return 'not found';
    }""")
    print(f">> Save button: {save_result}", flush=True)

    await asyncio.sleep(5)
    await page.screenshot(path="kwork_profile_saved.png")


async def check_public_profile(page) -> None:
    """Visit public profile page."""
    print(">> Checking public profile...", flush=True)
    await page.goto("https://kwork.ru/user/nsv11061992", wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(5)
    await page.screenshot(path="kwork_public_profile.png")
    print(">> Public profile screenshot saved", flush=True)


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, proxy=PROXY)
        context = await browser.new_context(viewport={"width": 1280, "height": 900}, locale="ru-RU")
        page = await context.new_page()

        await login(page)
        await go_to_profile_tab(page)
        await fill_profile(page)
        await save_profile(page)
        await check_public_profile(page)

        await browser.close()
        print(">> All done!", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
