"""Build and persist Steam Sniper image cache from ByMykel CSGO API."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

BYMYKEL_ALL_URL = (
    "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/all.json"
)
USER_AGENT = "SteamSniper/1.0 (+image-cache)"
CACHE_PATH = Path(__file__).parent / "data" / "image_cache.json"


def fetch_bymykel_all(timeout: int = 60) -> Any:
    """Download the full ByMykel dataset."""
    req = urllib.request.Request(
        BYMYKEL_ALL_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_image_cache(payload: dict | list) -> dict[str, str]:
    """Extract {base item name -> image url} mapping from ByMykel payload."""
    if isinstance(payload, dict):
        items = payload.values()
    elif isinstance(payload, list):
        items = payload
    else:
        raise TypeError(f"Unsupported payload type: {type(payload).__name__}")

    cache: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        image = str(item.get("image") or "").strip()
        if name and image:
            cache.setdefault(name.lower(), image)

    return cache


def load_image_cache(path: Path = CACHE_PATH) -> dict[str, str]:
    """Load existing cache from disk."""
    if not path.exists():
        return {}

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}

    return {
        str(name).strip().lower(): str(image).strip()
        for name, image in raw.items()
        if str(name).strip() and str(image).strip()
    }


def save_image_cache(cache: dict[str, str], path: Path = CACHE_PATH) -> None:
    """Persist cache to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(cache, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def ensure_image_cache(path: Path = CACHE_PATH, *, refresh: bool = False) -> dict[str, str]:
    """Return a non-empty cache, downloading it when needed."""
    if not refresh:
        existing = load_image_cache(path)
        if existing:
            return existing

    payload = fetch_bymykel_all()
    cache = build_image_cache(payload)
    if not cache:
        raise RuntimeError("ByMykel payload produced an empty image cache")
    save_image_cache(cache, path)
    return cache


def main() -> int:
    refresh = "--refresh" in sys.argv
    cache = ensure_image_cache(refresh=refresh)
    print(f"image cache ready: {len(cache)} items -> {CACHE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
