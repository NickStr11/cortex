"""Transcribe audio messages from Max (web.max.ru) chat.

Usage:
    python transcribe.py <chat_url> [--contact "Name"] [--last N] [--diarize]

Examples:
    python transcribe.py https://web.max.ru/61245315 --contact "Леша"
    python transcribe.py https://web.max.ru/61245315 --last 5
    python transcribe.py https://web.max.ru/61245315 --diarize   # speaker labels

Requires:
    - Chrome running with CDP on port 9222 (logged into Max)
    - whisper-cli.exe + model in voice-type runtime
    - ffmpeg in PATH
    - For --diarize: `pip install whisperx` + HF_TOKEN env (accept license at
      huggingface.co/pyannote/speaker-diarization-3.1)

Flow:
    1. Connects to existing Chrome tab via CDP (no new windows)
    2. Navigates to chat in that tab
    3. Clicks play on each audio to extract CDN URLs
    4. Downloads (Referer: web.max.ru), converts via ffmpeg
    5. Transcribes via whisper-cli GPU (fast path) or WhisperX (--diarize, multi-speaker)
    6. Saves runtime/max_audio/transcriptions.md
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright, Browser, Page

WHISPER_CLI = Path(r"D:\code\2026\3\voice-type\runtime\whisper-cpp\whisper-cli.exe")
WHISPER_MODEL = Path(r"D:\code\2026\3\voice-type\runtime\whisper-cpp\model\ggml-large-v3-turbo.bin")
OUTPUT_DIR = Path(r"D:\code\2026\2\cortex\runtime\max_audio")
CDP_URL = "http://localhost:9222"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    ),
    "Referer": "https://web.max.ru/",
}


def _check_cdp() -> bool:
    """Check if Chrome CDP is reachable."""
    try:
        with urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=2):
            return True
    except Exception:
        return False


def _connect(pw) -> Browser:
    """Connect to existing Chrome via CDP. Dies fast if not available."""
    if not _check_cdp():
        print("ERROR: Chrome CDP not running on port 9222.")
        print("Start Chrome with: --remote-debugging-port=9222")
        sys.exit(1)
    return pw.chromium.connect_over_cdp(CDP_URL)


def _navigate(browser: Browser, chat_url: str) -> Page:
    """Navigate to chat in existing tab — no new windows."""
    ctx = browser.contexts[0]
    # Reuse first tab if it exists, otherwise the context creates one
    pages = ctx.pages
    page = pages[0] if pages else ctx.new_page()

    page.goto(chat_url, wait_until="domcontentloaded", timeout=30000)

    # Wait for chat to render
    for _ in range(30):
        if page.query_selector(".attachAudio") or page.query_selector(".bubble"):
            break
        page.wait_for_timeout(500)
    else:
        # Give it one more second even if no audio found (might be text-only chat)
        page.wait_for_timeout(1000)

    # Check auth
    content = page.content()[:1000]
    if "QR-код" in content or "Войдите" in content:
        print("ERROR: Not logged into Max. Scan QR code in Chrome first.")
        sys.exit(1)

    return page


def _extract_audio(page: Page, last_n: int | None) -> list[dict]:
    """Extract audio metadata + URLs by clicking play on each message."""
    # Wait for audio elements to settle
    page.wait_for_timeout(1500)

    # Get metadata
    metadata = page.evaluate("""() => {
        const audios = document.querySelectorAll('.attachAudio');
        return [...audios].map((el, i) => {
            const bw = el.closest('.bordersWrapper') || el.parentElement?.parentElement;
            const cls = bw?.className || '';
            const side = cls.includes('--right') ? 'me' : cls.includes('--left') ? 'them' : '?';
            const meta = el.querySelector('.meta');
            const dur = meta?.textContent?.trim() || '';
            return {i, side, dur};
        });
    }""")

    total = len(metadata)
    if last_n and last_n < total:
        metadata = metadata[-last_n:]
        print(f"Found {total} audio, taking last {last_n}")
    else:
        print(f"Found {total} audio messages")

    if not metadata:
        return []

    # Extract URLs: click play on each, grab <audio> src, pause
    start_idx = metadata[0]["i"]
    urls = page.evaluate("""async ([startIdx, count]) => {
        const audios = document.querySelectorAll('.attachAudio');
        const urls = [];
        for (let i = startIdx; i < startIdx + count && i < audios.length; i++) {
            const btn = audios[i].querySelector('.button');
            if (!btn) { urls.push(''); continue; }
            btn.click();
            await new Promise(r => setTimeout(r, 500));
            const audioEl = document.querySelector('audio');
            urls.push(audioEl?.src || '');
            if (audioEl) audioEl.pause();
            await new Promise(r => setTimeout(r, 150));
        }
        return urls;
    }""", [start_idx, len(metadata)])

    for meta, url in zip(metadata, urls):
        meta["url"] = url

    return metadata


def _download(url: str, path: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            path.write_bytes(resp.read())
        return True
    except Exception as e:
        print(f"  Download failed: {e}")
        return False


def _transcribe_diarize(audio_path: Path) -> str:
    """Multi-speaker transcription via WhisperX. Returns text with [SPEAKER_XX] labels."""
    try:
        import whisperx  # type: ignore
    except ImportError:
        return "[whisperx not installed — pip install whisperx]"

    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        return "[HF_TOKEN missing — set env var, accept pyannote license on HF]"

    wav_path = audio_path.with_suffix(".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(audio_path), "-ar", "16000", "-ac", "1", "-f", "wav", str(wav_path)],
        capture_output=True, timeout=60,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if not wav_path.exists():
        return "[ffmpeg failed]"

    try:
        device = "cuda"
        model = whisperx.load_model("large-v3", device=device, compute_type="float16")
        audio = whisperx.load_audio(str(wav_path))
        result = model.transcribe(audio, batch_size=16)

        align_model, meta = whisperx.load_align_model(language_code=result["language"], device=device)
        result = whisperx.align(result["segments"], align_model, meta, audio, device, return_char_alignments=False)

        diarize = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
        diarize_segments = diarize(audio)
        result = whisperx.assign_word_speakers(diarize_segments, result)

        lines = []
        current_speaker = None
        buf: list[str] = []
        for seg in result.get("segments", []):
            spk = seg.get("speaker", "SPK?")
            text = seg.get("text", "").strip()
            if spk != current_speaker:
                if buf:
                    lines.append(f"[{current_speaker}] {' '.join(buf)}")
                current_speaker = spk
                buf = [text]
            else:
                buf.append(text)
        if buf:
            lines.append(f"[{current_speaker}] {' '.join(buf)}")
        return "\n".join(lines) or "[empty]"
    except Exception as e:
        return f"[whisperx error: {e}]"
    finally:
        wav_path.unlink(missing_ok=True)


def _transcribe(audio_path: Path) -> str:
    wav_path = audio_path.with_suffix(".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(audio_path), "-ar", "16000", "-ac", "1", "-f", "wav", str(wav_path)],
        capture_output=True, timeout=60,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if not wav_path.exists():
        return "[ffmpeg failed]"

    out_base = str(wav_path).replace(".wav", "")
    cmd = [
        str(WHISPER_CLI), "-m", str(WHISPER_MODEL),
        "-f", str(wav_path), "-l", "auto", "--no-timestamps",
        "-t", "4", "-bo", "1", "-bs", "1", "-oj", "-of", out_base, "-dev", "0",
    ]
    subprocess.run(
        cmd, capture_output=True, timeout=120,
        env={**os.environ, "GGML_NO_BACKTRACE": "1"},
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )

    json_path = Path(f"{out_base}.json")
    text = ""
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        text = " ".join(s.get("text", "").strip() for s in data.get("transcription", [])).strip()
        json_path.unlink(missing_ok=True)
    wav_path.unlink(missing_ok=True)
    return text or "[empty]"


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe Max audio messages")
    parser.add_argument("chat_url", help="e.g. https://web.max.ru/61245315")
    parser.add_argument("--contact", default="", help="Contact name for output header")
    parser.add_argument("--last", type=int, default=None, help="Only process last N audio messages")
    parser.add_argument("--diarize", action="store_true", help="Speaker diarization via WhisperX (slower, multi-speaker)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"Chat: {args.chat_url}")

    with sync_playwright() as pw:
        browser = _connect(pw)
        page = _navigate(browser, args.chat_url)
        messages = _extract_audio(page, args.last)
        # Don't close the tab — user's browser stays as-is

    if not messages:
        print("No audio messages found.")
        return

    results = []
    for msg in messages:
        label = f"#{msg['i']:02d} [{msg['side']}] {msg['dur']}"
        url = msg.get("url", "")
        if not url:
            print(f"{label} — no URL, skip")
            results.append({"label": label, "text": "[no url]"})
            continue

        audio_path = OUTPUT_DIR / f"msg_{msg['i']:02d}.mp3"
        print(f"{label} ", end="", flush=True)

        if not _download(url, audio_path):
            results.append({"label": label, "text": "[download failed]"})
            continue

        kb = audio_path.stat().st_size // 1024
        print(f"[{kb}KB] ", end="", flush=True)

        text = _transcribe_diarize(audio_path) if args.diarize else _transcribe(audio_path)
        print(f"{text[:70]}{'...' if len(text) > 70 else ''}")
        results.append({"label": label, "text": text})
        audio_path.unlink(missing_ok=True)

    # Write output
    contact = args.contact or args.chat_url.rstrip("/").split("/")[-1]
    out_file = OUTPUT_DIR / "transcriptions.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(f"# Транскрипция аудио — {contact}\n\n")
        f.write(f"Сообщений: {len(results)}\n\n---\n\n")
        for r in results:
            f.write(f"### {r['label']}\n{r['text']}\n\n")

    print(f"\nDone: {len(results)} -> {out_file}")


if __name__ == "__main__":
    main()
