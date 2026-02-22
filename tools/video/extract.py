#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
# ///
"""Extract info from videos: metadata+subtitles for URLs, frames+audio for local files.

Usage:
    uv run tools/video/extract.py https://youtube.com/watch?v=xxx
    uv run tools/video/extract.py video.mp4
    uv run tools/video/extract.py video.mp4 --interval 10 --max-frames 30
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import requests


# ── Helpers ──────────────────────────────────────────────────────────


def is_url(path: str) -> bool:
    return path.startswith("http://") or path.startswith("https://")


def format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}h{m:02d}m{s:02d}s"
    return f"{m:02d}m{s:02d}s"


def load_env(env_path: Path) -> dict[str, str]:
    result = {}
    if not env_path.exists():
        return result
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        result[k.strip()] = v.strip().strip('"').strip("'")
    return result


def get_api_config() -> tuple[str, str, str]:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    base_url = os.environ.get("WHISPER_API_BASE", "")
    model = os.environ.get("WHISPER_MODEL", "")

    if not key:
        for env_path in [
            Path.cwd() / ".env",
            Path(__file__).resolve().parent.parent.parent / ".env",
        ]:
            env = load_env(env_path)
            if env.get("OPENROUTER_API_KEY"):
                key = key or env["OPENROUTER_API_KEY"]
                base_url = base_url or env.get("WHISPER_API_BASE", "")
                model = model or env.get("WHISPER_MODEL", "")
                break

    base_url = base_url or "https://openrouter.ai/api"
    model = model or "openai/whisper-large-v3"
    return key, base_url, model


# ── URL mode: metadata + subtitles (no download) ────────────────────


def fetch_url_info(url: str, out_dir: str) -> None:
    """Get video metadata and subtitles via yt-dlp without downloading."""
    os.makedirs(out_dir, exist_ok=True)

    # 1. Metadata
    print("--- Fetching metadata ---")
    r = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-playlist", url],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"yt-dlp error: {r.stderr[:500]}", file=sys.stderr)
        sys.exit(1)

    info = json.loads(r.stdout)

    meta = {
        "title": info.get("title", ""),
        "uploader": info.get("uploader", ""),
        "duration": info.get("duration", 0),
        "duration_str": format_time(info.get("duration", 0)),
        "upload_date": info.get("upload_date", ""),
        "view_count": info.get("view_count", 0),
        "description": info.get("description", ""),
        "url": url,
        "thumbnail": info.get("thumbnail", ""),
        "chapters": info.get("chapters") or [],
        "tags": info.get("tags") or [],
    }

    meta_path = os.path.join(out_dir, "metadata.json")
    Path(meta_path).write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Title: {meta['title']}")
    print(f"Duration: {meta['duration_str']}")
    print(f"Uploader: {meta['uploader']}")
    print(f"Metadata saved: {meta_path}")

    # 2. Subtitles
    print("\n--- Fetching subtitles ---")
    sub_dir = os.path.join(out_dir, "subs")
    os.makedirs(sub_dir, exist_ok=True)

    subprocess.run(
        [
            "yt-dlp",
            "--write-subs", "--write-auto-subs",
            "--sub-lang", "ru,en",
            "--sub-format", "vtt",
            "--skip-download",
            "--no-playlist",
            "-o", os.path.join(sub_dir, "%(id)s.%(ext)s"),
            url,
        ],
        capture_output=True, text=True,
    )

    # Find and convert subtitles to plain text
    subs_text = ""
    for vtt_file in sorted(Path(sub_dir).glob("*.vtt")):
        raw = vtt_file.read_text(encoding="utf-8", errors="replace")
        lines = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("WEBVTT") or line.startswith("Kind:"):
                continue
            if line.startswith("Language:") or line.startswith("NOTE"):
                continue
            if "-->" in line:
                continue
            if line.isdigit():
                continue
            # Strip VTT tags like <c>, </c>, <00:00:01.000>
            import re
            clean = re.sub(r"<[^>]+>", "", line)
            if clean and clean not in lines[-1:]:
                lines.append(clean)
        subs_text = "\n".join(lines)
        break  # Use first subtitle file found

    if subs_text:
        subs_path = os.path.join(out_dir, "subtitles.txt")
        Path(subs_path).write_text(subs_text, encoding="utf-8")
        print(f"Subtitles saved: {subs_path} ({len(subs_text)} chars)")
    else:
        print("No subtitles available")

    # 3. Download thumbnail
    thumb_url = meta.get("thumbnail", "")
    thumb_path = None
    if thumb_url:
        print("\n--- Downloading thumbnail ---")
        try:
            resp = requests.get(thumb_url, timeout=15)
            if resp.status_code == 200:
                ext = ".jpg"
                if "png" in resp.headers.get("content-type", ""):
                    ext = ".png"
                thumb_path = os.path.join(out_dir, f"thumbnail{ext}")
                Path(thumb_path).write_bytes(resp.content)
                print(f"Thumbnail saved: {thumb_path}")
        except requests.RequestException:
            print("Thumbnail download failed")

    # 4. Summary
    summary = {
        "mode": "url",
        "url": url,
        "output_dir": os.path.abspath(out_dir),
        "metadata_file": meta_path,
        "subtitles_file": os.path.join(out_dir, "subtitles.txt") if subs_text else None,
        "thumbnail_file": thumb_path,
        "has_subtitles": bool(subs_text),
        "title": meta["title"],
        "duration": meta["duration_str"],
    }
    summary_path = os.path.join(out_dir, "summary.json")
    Path(summary_path).write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nDone! Summary: {summary_path}")


# ── Local file mode: frames + transcription ──────────────────────────


def check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def get_duration(video: str) -> float:
    r = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video,
        ],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip())


def extract_frames(
    video: str, out_dir: str, interval: int = 5, max_frames: int = 20
) -> list[dict]:
    frames_dir = os.path.join(out_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    try:
        duration = get_duration(video)
    except (ValueError, subprocess.CalledProcessError):
        duration = 300.0

    if duration / interval > max_frames:
        interval = max(1, int(duration / max_frames))

    subprocess.run(
        [
            "ffmpeg", "-i", video,
            "-vf", f"fps=1/{interval}",
            "-q:v", "2", "-y",
            os.path.join(frames_dir, "frame_%04d.jpg"),
        ],
        capture_output=True,
    )

    results = []
    for i, f in enumerate(sorted(Path(frames_dir).glob("frame_*.jpg"))):
        ts = i * interval
        new_name = f"frame_{format_time(ts)}.jpg"
        new_path = f.parent / new_name
        f.rename(new_path)
        results.append({
            "path": str(new_path),
            "timestamp": format_time(ts),
            "seconds": ts,
        })
    return results


def extract_audio(video: str, out_dir: str) -> str | None:
    audio_path = os.path.join(out_dir, "audio.mp3")
    r = subprocess.run(
        [
            "ffmpeg", "-i", video,
            "-vn", "-acodec", "libmp3lame", "-q:a", "4",
            "-y", audio_path,
        ],
        capture_output=True, text=True,
    )
    if (
        r.returncode != 0
        or not os.path.exists(audio_path)
        or os.path.getsize(audio_path) < 1000
    ):
        return None
    return audio_path


def transcribe(
    audio_path: str, api_key: str, base_url: str, model: str
) -> str:
    url = f"{base_url.rstrip('/')}/v1/audio/transcriptions"

    size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    if size_mb > 24:
        print(
            f"Warning: audio {size_mb:.0f}MB (limit ~25MB). May fail.",
            file=sys.stderr,
        )

    try:
        with open(audio_path, "rb") as f:
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": ("audio.mp3", f, "audio/mpeg")},
                data={"model": model},
                timeout=300,
            )

        if resp.status_code == 200:
            data = resp.json()
            return data.get("text", str(data))

        print(
            f"Transcription error {resp.status_code}: {resp.text[:500]}",
            file=sys.stderr,
        )
        return ""
    except requests.RequestException as e:
        print(f"Transcription failed: {e}", file=sys.stderr)
        return ""


def process_local(args: argparse.Namespace) -> None:
    """Process local video file: extract frames + transcribe."""
    if not check_ffmpeg():
        print("Error: ffmpeg not found. Install: winget install ffmpeg", file=sys.stderr)
        sys.exit(1)

    video = os.path.abspath(args.video)
    if not os.path.exists(video):
        print(f"Error: not found: {video}", file=sys.stderr)
        sys.exit(1)

    name = Path(video).stem
    out = args.output or os.path.join("video_output", name)
    os.makedirs(out, exist_ok=True)

    print(f"Video: {video}")
    print(f"Output: {out}")

    # Frames
    print("\n--- Extracting frames ---")
    frames = extract_frames(video, out, args.interval, args.max_frames)
    print(f"Extracted: {len(frames)} frames")

    # Audio + Transcription
    transcript = ""
    transcript_path = None

    if not args.no_audio:
        api_key, base_url, model = get_api_config()
        if api_key:
            print("\n--- Extracting audio ---")
            audio = extract_audio(video, out)
            if audio:
                size_kb = os.path.getsize(audio) // 1024
                print(f"Audio: {audio} ({size_kb}KB)")
                print(f"\n--- Transcribing ({model}) ---")
                transcript = transcribe(audio, api_key, base_url, model)
                if transcript:
                    transcript_path = os.path.join(out, "transcript.txt")
                    Path(transcript_path).write_text(transcript, encoding="utf-8")
                    print(f"Transcript saved: {transcript_path}")
                else:
                    print("Transcription: failed or empty")
            else:
                print("No audio track found")
        else:
            print("\nSkipped transcription: no API key in .env")

    # Summary
    summary = {
        "mode": "local",
        "video": video,
        "output_dir": os.path.abspath(out),
        "frames": frames,
        "frames_count": len(frames),
        "transcript_file": transcript_path,
        "has_transcript": bool(transcript),
    }
    summary_path = os.path.join(out, "summary.json")
    Path(summary_path).write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nDone! Summary: {summary_path}")


# ── Main ─────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract info from video (URL or local file)"
    )
    parser.add_argument("video", help="Video file path or URL")
    parser.add_argument(
        "--interval", type=int, default=5,
        help="Seconds between frames, local only (default: 5)",
    )
    parser.add_argument(
        "--max-frames", type=int, default=20,
        help="Max frames to extract, local only (default: 20)",
    )
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument(
        "--no-audio", action="store_true", help="Skip transcription (local only)"
    )
    args = parser.parse_args()

    if is_url(args.video):
        name = "video_url"
        out = args.output or os.path.join("video_output", name)
        fetch_url_info(args.video, out)
    else:
        process_local(args)


if __name__ == "__main__":
    main()
