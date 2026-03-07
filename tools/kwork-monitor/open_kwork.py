"""Open Kwork creation page in browser and wait."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

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

        # Go to kwork creation
        await page.goto("https://kwork.ru/new", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        print(">> Ready — kwork creation page open. Browser will stay open.", flush=True)
        print(">> Press Ctrl+C to close.", flush=True)

        # Keep browser open
        try:
            while True:
                await asyncio.sleep(60)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
