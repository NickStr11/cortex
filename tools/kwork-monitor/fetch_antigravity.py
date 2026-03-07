"""Fetch Google Antigravity reference screenshots."""
from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

OUT = Path(__file__).parent / "covers" / "ref"


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})

        await page.goto("https://antigravity.google/", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        for i in range(6):
            await page.screenshot(path=str(OUT / f"ag_{i}.png"))
            print(f"ag_{i}.png saved", flush=True)
            await page.evaluate("window.scrollBy(0, 900)")
            await asyncio.sleep(2)

        await browser.close()
        print("Done!", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
