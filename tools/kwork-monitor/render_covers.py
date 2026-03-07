"""Render HTML covers to PNG via Playwright."""
from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

COVERS_DIR = Path(__file__).parent / "covers"


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 660, "height": 440})

        for i in range(3):
            html_path = COVERS_DIR / f"cover_{i}.html"
            png_path = COVERS_DIR / f"cover_{i}.png"

            await page.goto(f"file:///{html_path.as_posix()}", wait_until="load")
            await asyncio.sleep(0.5)
            await page.screenshot(path=str(png_path), type="png")

            size_kb = png_path.stat().st_size / 1024
            print(f"cover_{i}.png — {size_kb:.0f} KB", flush=True)

        await browser.close()
        print("Done!", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
