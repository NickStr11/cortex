"""Generate Kwork covers via Nano Banana 2 Pro (gemini-3-pro-image-preview)."""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

# Load .env
ENV_PATH = Path(__file__).parent.parent.parent / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

COVERS_DIR = Path(__file__).parent / "covers"
COVERS_DIR.mkdir(exist_ok=True)

STYLE = (
    "Style reference: Google Antigravity website (antigravity.google). Key visual traits: "
    "clean white (#FFFFFF) background, scattered small colorful particles/confetti dots "
    "(pink, blue, purple, green, yellow — like floating in zero gravity), "
    "large elegant sans-serif typography (Google Sans or similar), "
    "generous white space, minimal and airy feel, "
    "subtle pastel gradient accents, premium tech product aesthetic. "
    "4:3 aspect ratio."
)

PROMPTS = [
    # Cover 0: Telegram Bot
    (
        f"Design a freelance service cover image. {STYLE} "
        "Center: large elegant dark text 'Telegram-бот на Python' with 'бот' in blue (#4285F4). "
        "Scattered around the text — small colorful confetti particles floating in space "
        "(pink, blue, purple, green dots like in the Google Antigravity reference). "
        "Below the main text: small gray subtitle 'aiogram · PostgreSQL · Docker · API'. "
        "Clean, minimal, premium. White background with subtle particle decoration."
    ),
    # Cover 1: Web Scraping / Parsing
    (
        f"Design a freelance service cover image. {STYLE} "
        "Center: large elegant dark text 'Парсинг любого сайта' with 'Парсинг' in green (#0F9D58). "
        "Scattered around — small colorful confetti particles floating in space "
        "(like in the Google Antigravity hero section). "
        "Below: small gray subtitle 'Scrapy · Playwright · CSV · Excel · JSON'. "
        "Clean, minimal, premium. White background with subtle particle decoration."
    ),
    # Cover 2: AI Chatbot
    (
        f"Design a freelance service cover image. {STYLE} "
        "Center: large elegant dark text 'AI чат-бот для бизнеса' with 'AI' in purple (#9334E6). "
        "Scattered around — small colorful confetti particles floating like zero gravity "
        "(like the Google Antigravity site). "
        "Below: small gray subtitle 'RAG · Claude · GPT · Telegram · Web Widget'. "
        "Clean, minimal, premium. White background with subtle particle decoration."
    ),
]

NAMES = ["cover_ai_0.png", "cover_ai_1.png", "cover_ai_2.png"]

# Behance Emberlen reference images
REF_DIR = Path(__file__).parent / "covers" / "ref"


def load_refs() -> list[Image.Image]:
    """Load reference images from Behance screenshots."""
    refs = []
    for name in ["ag_0.png", "ag_1.png"]:  # Google Antigravity hero + dark section
        path = REF_DIR / name
        if path.exists():
            refs.append(Image.open(path))
            print(f"  Loaded ref: {name}", flush=True)
    return refs


def generate() -> None:
    refs = load_refs()

    for i, (prompt, name) in enumerate(zip(PROMPTS, NAMES)):
        print(f"[{i+1}/3] Generating {name}...", flush=True)
        try:
            # Build content: references first, then prompt
            content: list = []
            for ref in refs:
                content.append(ref)
            content.append(
                "Here are reference images showing the design style I want. "
                "Study the typography, layout, color usage, negative space, and pill-tag elements. "
                "Now generate a new image in this exact style:\n\n" + prompt
            )

            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=content,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            saved = False
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    out_path = COVERS_DIR / name
                    out_path.write_bytes(part.inline_data.data)
                    size_kb = out_path.stat().st_size / 1024
                    print(f"  Saved: {out_path} ({size_kb:.0f} KB)", flush=True)
                    saved = True
                    break
                elif part.text:
                    print(f"  Text: {part.text[:100]}", flush=True)

            if not saved:
                print(f"  No image in response!", flush=True)

        except Exception as e:
            print(f"  Error: {e}", flush=True)


if __name__ == "__main__":
    generate()
    print("\nDone!", flush=True)
