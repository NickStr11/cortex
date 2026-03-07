"""Find the Kwork title field DOM structure."""
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

PROXY = {"server": "http://45.135.29.96:8000", "username": "oeozTg", "password": "A0Vn3M"}


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, proxy=PROXY)
        page = await browser.new_page(viewport={"width": 1280, "height": 900}, locale="ru-RU")

        # Login
        await page.goto("https://kwork.ru/login", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        await page.wait_for_selector('input[type="password"]', timeout=15000)
        await page.get_by_placeholder("почта").or_(page.get_by_placeholder("логин")).first.fill(
            os.environ.get("KWORK_LOGIN", "")
        )
        await page.get_by_placeholder("Пароль").first.fill(os.environ.get("KWORK_PASSWORD", ""))
        await page.get_by_role("button", name="Войти").first.click()
        await asyncio.sleep(6)
        print(f">> Logged in: {page.url}", flush=True)

        # Go to /new
        await page.goto("https://kwork.ru/new", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)

        # ── Find every interactive element near "Название" ──
        result = await page.evaluate("""() => {
            const info = [];

            // 1. List ALL textareas with details
            const allTas = document.querySelectorAll('textarea');
            info.push('TEXTAREAS (' + allTas.length + '):');
            allTas.forEach((ta, i) => {
                info.push('  [' + i + '] name=' + ta.name +
                    ' id=' + ta.id +
                    ' visible=' + (ta.offsetParent !== null) +
                    ' placeholder="' + (ta.placeholder || '').substring(0, 40) + '"' +
                    ' rows=' + ta.rows +
                    ' class="' + (ta.className || '').substring(0, 80) + '"' +
                    ' value="' + (ta.value || '').substring(0, 30) + '"');
            });

            // 2. List ALL contenteditable elements
            const ceEls = document.querySelectorAll('[contenteditable="true"]');
            info.push('\\nCONTENTEDITABLE (' + ceEls.length + '):');
            ceEls.forEach((el, i) => {
                info.push('  [' + i + '] tag=' + el.tagName +
                    ' id=' + el.id +
                    ' visible=' + (el.offsetParent !== null) +
                    ' class="' + (el.className || '').substring(0, 80) + '"' +
                    ' text="' + (el.textContent || '').substring(0, 40) + '"');
            });

            // 3. Find the form structure - step 1
            const step1 = document.querySelector('.step-1, #step-1, [class*="step1"], [class*="step-1"]');
            if (step1) {
                info.push('\\nSTEP1 container: ' + step1.tagName + ' class=' + step1.className?.substring(0, 100));
                // Get its inner interactive elements
                const innerEls = step1.querySelectorAll('textarea, input[type="text"], [contenteditable]');
                innerEls.forEach((el, i) => {
                    info.push('  inner[' + i + ']: ' + el.tagName +
                        ' name=' + el.name +
                        ' id=' + el.id +
                        ' visible=' + (el.offsetParent !== null));
                });
            } else {
                info.push('\\nNo step-1 container found');
            }

            // 4. Find "Название" text and get surrounding HTML
            const allEls = document.querySelectorAll('td, th, label, div, span, p');
            for (const el of allEls) {
                const text = el.textContent?.trim();
                if (text === 'Название' && el.offsetParent !== null) {
                    info.push('\\nНАЗВАНИЕ FOUND: ' + el.tagName + ' class="' + el.className + '"');
                    // Get the row/parent container
                    const row = el.closest('tr') || el.closest('.form-group') || el.closest('[class*="row"]') || el.parentElement;
                    if (row) {
                        info.push('Row container: ' + row.tagName + ' class="' + (row.className || '').substring(0, 100) + '"');
                        info.push('Row HTML (first 600 chars):');
                        info.push(row.innerHTML.substring(0, 600));
                    }
                    break;
                }
            }

            // 5. Check for the character counter "70 символов"
            const all2 = document.querySelectorAll('*');
            for (const el of all2) {
                if (el.textContent?.includes('70 символов') && el.children.length === 0 && el.offsetParent !== null) {
                    info.push('\\nCHAR COUNTER FOUND: ' + el.tagName + ' class="' + el.className + '"');
                    const parent = el.parentElement;
                    info.push('Counter parent: ' + parent.tagName + ' class="' + (parent.className || '').substring(0, 100) + '"');
                    // Previous sibling
                    const prev = el.previousElementSibling;
                    if (prev) {
                        info.push('Previous sibling: ' + prev.tagName + ' id=' + prev.id + ' class="' + (prev.className || '').substring(0, 100) + '"');
                        info.push('Prev outerHTML: ' + prev.outerHTML.substring(0, 300));
                    }
                    break;
                }
            }

            return info;
        }""")

        for line in result:
            print(line, flush=True)

        # ── Try clicking on the title area and typing ──
        print("\n=== CLICK + TYPE TEST ===", flush=True)

        # Try to click on the area where the title should be (near "Напишу портрет")
        try:
            # Method 1: get_by_placeholder
            ph = page.get_by_placeholder("Напишу портрет")
            count = await ph.count()
            print(f"get_by_placeholder('Напишу портрет'): {count}", flush=True)
            if count > 0:
                await ph.first.click()
                await page.keyboard.type("Test title ABC", delay=50)
                await asyncio.sleep(1)
                await page.screenshot(path="kwork_title_test.png")
                print("Typed via placeholder!", flush=True)
        except Exception as e:
            print(f"Placeholder method failed: {e}", flush=True)

        # Method 2: get_by_role
        try:
            tb = page.get_by_role("textbox").first
            print(f"First textbox found", flush=True)
        except Exception as e:
            print(f"Role method failed: {e}", flush=True)

        # Method 3: get_by_label
        try:
            lb = page.get_by_label("Название")
            count = await lb.count()
            print(f"get_by_label('Название'): {count}", flush=True)
        except Exception as e:
            print(f"Label method failed: {e}", flush=True)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
