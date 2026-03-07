"""Check Kwork public profile - full page screenshot."""
from __future__ import annotations
import asyncio, os
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
        page = await browser.new_page(viewport={"width": 1280, "height": 1200}, locale="ru-RU")
        await page.goto("https://kwork.ru/user/nsv11061992", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)
        await page.screenshot(path="kwork_public_full.png", full_page=True)
        print(">> Saved kwork_public_full.png", flush=True)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
