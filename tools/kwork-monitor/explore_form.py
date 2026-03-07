"""Explore Kwork creation form DOM structure."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

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


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, proxy=PROXY)
        context = await browser.new_context(viewport={"width": 1280, "height": 900}, locale="ru-RU")
        page = await context.new_page()

        await login(page)

        # Go to kwork creation page
        await page.goto("https://kwork.ru/new", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # ── Dump ALL form elements ──
        print("\n=== FORM ELEMENTS ===", flush=True)
        form_info = await page.evaluate("""() => {
            const results = [];

            // All inputs
            document.querySelectorAll('input').forEach(el => {
                if (el.offsetParent !== null || el.type === 'hidden') {
                    results.push({
                        tag: 'input',
                        type: el.type,
                        name: el.name,
                        id: el.id,
                        placeholder: el.placeholder?.substring(0, 50),
                        value: el.value?.substring(0, 50),
                        visible: el.offsetParent !== null,
                        classes: el.className?.substring(0, 80)
                    });
                }
            });

            // All textareas
            document.querySelectorAll('textarea').forEach(el => {
                results.push({
                    tag: 'textarea',
                    name: el.name,
                    id: el.id,
                    placeholder: el.placeholder?.substring(0, 50),
                    value: el.value?.substring(0, 50),
                    visible: el.offsetParent !== null,
                    rows: el.rows,
                    classes: el.className?.substring(0, 80)
                });
            });

            // All selects
            document.querySelectorAll('select').forEach(el => {
                const opts = Array.from(el.options).map(o => o.text + '=' + o.value);
                results.push({
                    tag: 'select',
                    name: el.name,
                    id: el.id,
                    visible: el.offsetParent !== null,
                    options: opts.join(' | '),
                    classes: el.className?.substring(0, 80)
                });
            });

            // All buttons
            document.querySelectorAll('button').forEach(el => {
                if (el.offsetParent !== null) {
                    results.push({
                        tag: 'button',
                        type: el.type,
                        text: el.textContent.trim().substring(0, 50),
                        classes: el.className?.substring(0, 80)
                    });
                }
            });

            return results;
        }""")

        for item in form_info:
            print(f"  {item}", flush=True)

        # ── Check Vue instance ──
        print("\n=== VUE CHECK ===", flush=True)
        vue_info = await page.evaluate("""() => {
            // Check if Vue is present
            const app = document.querySelector('#app') || document.querySelector('[data-v-app]');
            if (app && app.__vue_app__) return 'Vue 3 app found';
            if (app && app.__vue__) return 'Vue 2 app found';

            // Check for Vue components
            const vueEls = document.querySelectorAll('[data-v-]');
            if (vueEls.length > 0) return 'Vue components found: ' + vueEls.length;

            return 'No Vue detected. Checking other frameworks...';
        }""")
        print(f"  {vue_info}", flush=True)

        # ── Try to find the title textarea and fill it via Playwright ──
        print("\n=== TITLE FILL TEST ===", flush=True)

        # Try different approaches to fill the title
        # Approach 1: by placeholder
        try:
            title_el = page.get_by_placeholder("Напишу портрет")
            count = await title_el.count()
            print(f"  By placeholder 'Напишу портрет': found {count}", flush=True)
            if count > 0:
                await title_el.first.fill("Тестовое название кворка")
                await asyncio.sleep(1)
                val = await title_el.first.input_value()
                print(f"  After fill: '{val}'", flush=True)
        except Exception as e:
            print(f"  Placeholder approach failed: {e}", flush=True)

        # Approach 2: by textarea name
        try:
            ta = page.locator('textarea[name="description"]')
            count = await ta.count()
            print(f"  By name='description': found {count}", flush=True)
            if count > 0:
                # Check which one is visible
                for i in range(count):
                    vis = await ta.nth(i).is_visible()
                    print(f"    [{i}] visible={vis}", flush=True)
        except Exception as e:
            print(f"  Name approach failed: {e}", flush=True)

        # Approach 3: contenteditable div
        try:
            ce = page.locator('[contenteditable="true"]')
            count = await ce.count()
            print(f"  contenteditable divs: found {count}", flush=True)
            for i in range(min(count, 5)):
                vis = await ce.nth(i).is_visible()
                text = await ce.nth(i).inner_text()
                print(f"    [{i}] visible={vis} text='{text[:50]}'", flush=True)
        except Exception as e:
            print(f"  contenteditable approach failed: {e}", flush=True)

        # ── Check the rubric (category) selects ──
        print("\n=== CATEGORY SELECTS ===", flush=True)
        cat_info = await page.evaluate("""() => {
            const selects = document.querySelectorAll('select');
            const results = [];
            selects.forEach((sel, i) => {
                const opts = Array.from(sel.options).map(o => ({
                    text: o.text,
                    value: o.value,
                    selected: o.selected
                }));
                results.push({
                    index: i,
                    name: sel.name,
                    id: sel.id,
                    visible: sel.offsetParent !== null,
                    style_display: getComputedStyle(sel).display,
                    parent_classes: sel.parentElement?.className?.substring(0, 100),
                    options_count: opts.length,
                    options: opts.slice(0, 15)
                });
            });
            return results;
        }""")
        for item in cat_info:
            print(f"\n  Select #{item['index']}:", flush=True)
            print(f"    name={item['name']}, id={item['id']}", flush=True)
            print(f"    visible={item['visible']}, display={item['style_display']}", flush=True)
            print(f"    parent_classes={item['parent_classes']}", flush=True)
            print(f"    options ({item['options_count']}):", flush=True)
            for opt in item['options']:
                print(f"      '{opt['text']}' = {opt['value']} {'[SELECTED]' if opt['selected'] else ''}", flush=True)

        # ── Check for custom dropdown components ──
        print("\n=== CUSTOM DROPDOWNS ===", flush=True)
        custom = await page.evaluate("""() => {
            const results = [];
            // Look for common custom select patterns
            document.querySelectorAll('.select-wrapper, .custom-select, .v-select, [class*="select"], [class*="dropdown"]').forEach(el => {
                if (el.offsetParent !== null) {
                    results.push({
                        tag: el.tagName,
                        classes: el.className?.substring(0, 100),
                        text: el.textContent?.trim().substring(0, 100),
                        rect: el.getBoundingClientRect()
                    });
                }
            });
            return results.slice(0, 20);
        }""")
        for item in custom:
            print(f"  {item['tag']} .{item['classes'][:60]}: '{item['text'][:50]}'", flush=True)

        await page.screenshot(path="kwork_explore.png")
        print("\n>> Saved kwork_explore.png", flush=True)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
