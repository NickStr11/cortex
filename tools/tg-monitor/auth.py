"""Telethon auth.

QR (recommended):  python auth.py --qr
Phone code:        python auth.py +79XXXXXXXXX
  then:            python auth.py +79XXXXXXXXX <CODE> [2FA_PASSWORD]

Env vars: TG_API_ID, TG_API_HASH (required).
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from telethon import TelegramClient  # type: ignore[import-untyped]

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "tg-groups"


def _get_client() -> TelegramClient:
    api_id = int(os.environ.get("TG_API_ID", "0"))
    api_hash = os.environ.get("TG_API_HASH", "")

    if not api_id or not api_hash:
        print("Error: TG_API_ID and TG_API_HASH required")
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    session_name = os.environ.get("TG_SESSION_NAME", "cortex_userbot")
    session_path = str(DATA_DIR / session_name)
    return TelegramClient(session_path, api_id, api_hash)


async def qr_auth() -> None:
    """QR code auth — scan from Telegram mobile."""
    try:
        import qrcode
    except ImportError:
        print("pip install qrcode[pil]")
        sys.exit(1)

    client = _get_client()
    await client.connect()

    qr_login = await client.qr_login()

    # Save QR as image
    img = qrcode.make(qr_login.url)
    qr_path = DATA_DIR / "qr_login.png"
    img.save(str(qr_path))
    print(f"QR saved: {qr_path.resolve()}")
    print(f"URL: {qr_login.url}")
    print()
    print(">>> Open qr_login.png and scan with Telegram mobile:")
    print(">>>   Settings -> Devices -> Link Desktop Device")
    print()
    print("Waiting 120 seconds for scan...")

    # Auto-open the image
    if sys.platform == "win32":
        os.startfile(str(qr_path.resolve()))  # type: ignore[attr-defined]

    try:
        await asyncio.wait_for(qr_login.wait(), timeout=120)
    except asyncio.TimeoutError:
        print("Timeout — no scan detected. Try again.")
        await client.disconnect()
        return

    me = await client.get_me()
    print(f"OK! Authorized as: {me.first_name} (id={me.id}, phone={me.phone})")  # type: ignore[union-attr]
    await client.disconnect()
    print("Session saved!")


async def request_code(phone: str) -> None:
    """Step 1: send code request to Telegram."""
    client = _get_client()
    await client.connect()

    result = await client.send_code_request(phone)
    print(f"Code sent! Type: {type(result.type).__name__}")
    print(f"Phone code hash: {result.phone_code_hash}")
    print(f"\nNow run: python auth.py {phone} <CODE>")

    await client.disconnect()


async def sign_in(phone: str, code: str, password: str | None = None) -> None:
    """Step 2: sign in with the code."""
    client = _get_client()
    await client.connect()

    try:
        await client.sign_in(phone=phone, code=code)
    except Exception as e:
        if "Two-steps verification" in str(e) or "SessionPasswordNeeded" in type(e).__name__:
            if not password:
                print("2FA enabled! Run: python auth.py +79... <CODE> <PASSWORD>")
                await client.disconnect()
                sys.exit(1)
            await client.sign_in(password=password)
        else:
            raise

    me = await client.get_me()
    print(f"OK! Authorized as: {me.first_name} (id={me.id})")  # type: ignore[union-attr]
    await client.disconnect()
    print("Session saved!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  QR:     python auth.py --qr")
        print("  Step 1: python auth.py +79XXXXXXXXX")
        print("  Step 2: python auth.py +79XXXXXXXXX <CODE> [PASSWORD]")
        sys.exit(1)

    if sys.argv[1] == "--qr":
        asyncio.run(qr_auth())
    elif len(sys.argv) >= 3:
        code = sys.argv[2]
        pwd = sys.argv[3] if len(sys.argv) >= 4 else None
        asyncio.run(sign_in(sys.argv[1], code, pwd))
    else:
        asyncio.run(request_code(sys.argv[1]))
