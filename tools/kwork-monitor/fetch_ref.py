"""Fetch Behance reference images."""
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

        url = "https://www.behance.net/gallery/245082865/Emberlen"
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # Scroll and screenshot sections
        for i in range(4):
            await page.screenshot(path=str(OUT / f"ref_{i}.png"))
            print(f"ref_{i}.png saved", flush=True)
            await page.evaluate("window.scrollBy(0, 900)")
            await asyncio.sleep(1)

        await browser.close()
        print("Done!", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
