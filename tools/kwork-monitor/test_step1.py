"""Test: fill step 1 and click Продолжить with Playwright native click."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

ENV_PATH = Path(__file__).parent.parent.parent / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

PROXY = {"server": "http://45.135.29.96:8000", "username": "oeozTg", "password": "A0Vn3M"}


async def main() -> None:
    # Generate test cover
    cover_path = Path(__file__).parent / "covers" / "test_cover.png"
    cover_path.parent.mkdir(exist_ok=True)
    img = Image.new("RGB", (660, 440), (30, 60, 114))
    draw = ImageDraw.Draw(img)
    draw.text((200, 200), "Telegram Bot Dev", fill=(255, 255, 255))
    img.save(cover_path)

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

        await page.goto("https://kwork.ru/new", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)

        # ── 1. Title ──
        title_div = page.locator("#editor-title")
        await title_div.click()
        await page.keyboard.type("Разработаю Telegram-бота на Python под ваши задачи", delay=15)
        await asyncio.sleep(1)
        print(f"Title: {await title_div.inner_text()}", flush=True)

        # ── 2. Parent category ──
        await page.evaluate("""() => {
            const selects = document.querySelectorAll('select');
            for (const sel of selects) {
                for (const opt of sel.options) {
                    if (opt.value === '11') {
                        jQuery(sel).val('11').trigger('chosen:updated').trigger('change');
                        return;
                    }
                }
            }
        }""")
        await asyncio.sleep(3)

        # ── 3. Subcategory ──
        await page.evaluate("""() => {
            const sel = document.querySelector('select[name="category_id"]');
            jQuery(sel).val('41').trigger('chosen:updated').trigger('change');
        }""")
        await asyncio.sleep(2)

        # ── 4. Type "Чат-боты" — scope to #kwork-save-attributes ──
        attrs = page.locator("#kwork-save-attributes")
        await attrs.get_by_text("Чат-боты", exact=True).click()
        await asyncio.sleep(1)
        print("Type: clicked Чат-боты", flush=True)

        # ── 5. Check what new fields appeared ──
        new_fields = await page.evaluate("""() => {
            const visible = [];
            const container = document.querySelector('#kwork-save-attributes');
            if (!container) return ['no #kwork-save-attributes'];
            container.querySelectorAll('label').forEach(el => {
                if (el.offsetParent !== null && el.textContent.trim()) {
                    visible.push(el.textContent.trim());
                }
            });
            return visible;
        }""")
        print(f"Visible labels in attributes: {new_fields}", flush=True)

        # ── 6. Select Вид — scope to form ──
        try:
            await attrs.get_by_text("Написание и доработка", exact=True).click()
            print("Вид: clicked", flush=True)
        except Exception as e:
            print(f"Вид error: {e}", flush=True)
        await asyncio.sleep(1)

        # ── 7. Select Platform — scope to form ──
        try:
            await attrs.get_by_text("Telegram", exact=True).click()
            print("Platform Telegram: clicked", flush=True)
        except Exception as e:
            print(f"Platform error: {e}", flush=True)
        await asyncio.sleep(1)

        # ── 8. Upload cover ──
        print("Looking for file inputs...", flush=True)
        file_inputs = page.locator('input[type="file"]')
        count = await file_inputs.count()
        print(f"Found {count} file inputs", flush=True)
        for i in range(count):
            fi = file_inputs.nth(i)
            name = await fi.get_attribute("name") or ""
            accept = await fi.get_attribute("accept") or ""
            cls = await fi.get_attribute("class") or ""
            print(f"  [{i}] name='{name}' accept='{accept}' class='{cls}'", flush=True)

        # Try uploading to the first one that accepts images
        for i in range(count):
            fi = file_inputs.nth(i)
            accept = await fi.get_attribute("accept") or ""
            if "image" in accept or not accept:
                await fi.set_input_files(str(cover_path))
                print(f"  Uploaded to input [{i}]", flush=True)
                await asyncio.sleep(3)
                break

        await page.screenshot(path="kwork_test_before_continue.png")

        # ── 9. Click Продолжить with Playwright native click ──
        print("\n=== CLICKING ПРОДОЛЖИТЬ ===", flush=True)

        # Method A: Playwright text search
        cont_btn = page.get_by_text("Продолжить", exact=True)
        cont_count = await cont_btn.count()
        print(f"get_by_text('Продолжить'): found {cont_count}", flush=True)

        if cont_count > 0:
            for i in range(cont_count):
                vis = await cont_btn.nth(i).is_visible()
                tag = await cont_btn.nth(i).evaluate("el => el.tagName")
                cls = await cont_btn.nth(i).evaluate("el => el.className?.substring(0, 60)")
                print(f"  [{i}] visible={vis} tag={tag} class={cls}", flush=True)

            # Click the first visible one
            for i in range(cont_count):
                if await cont_btn.nth(i).is_visible():
                    print(f"  Clicking [{i}]...", flush=True)
                    await cont_btn.nth(i).scroll_into_view_if_needed()
                    await cont_btn.nth(i).click()
                    await asyncio.sleep(4)
                    break

        # Check if step 2 expanded
        step2_check = await page.evaluate("""() => {
            const el = document.querySelector('#step1-description');
            if (el && el.offsetParent !== null) return 'step2 VISIBLE';
            // Check for any error messages
            const errors = [];
            document.querySelectorAll('[class*="error"]').forEach(e => {
                if (e.offsetParent !== null && e.textContent.trim() && !e.classList.contains('hidden')) {
                    errors.push(e.textContent.trim().substring(0, 80));
                }
            });
            if (errors.length) return 'ERRORS: ' + errors.join(' | ');
            return 'step2 NOT visible, no errors';
        }""")
        print(f"After click: {step2_check}", flush=True)

        await page.screenshot(path="kwork_test_after_continue.png")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
