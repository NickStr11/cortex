"""Content Pipeline: DEV_CONTEXT → Article → Telegram

Usage:
    uv run python tools/pipeline/main.py
    uv run python tools/pipeline/main.py --dry-run   # print article, don't send

Requires:
    GOOGLE_API_KEY
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID
"""
from __future__ import annotations

import io
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Windows console fix
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx
from beartype import beartype
from google import genai

ROOT = Path(__file__).parent.parent.parent
DEV_CONTEXT = ROOT / "DEV_CONTEXT.md"

MODEL = "gemini-3-flash-preview"

WRITING_STYLE = """Ты пишешь build-in-public посты для Telegram-канала про AI-разработку.

Цель: человек прочитал — и забрал что-то полезное. Не дневник, а пост с мясом.

Структура:
1. Что делали (2-3 предложения, контекст задачи)
2. Полезное для читателя — САМОЕ ВАЖНОЕ:
   - Конкретные инструменты, библиотеки, сервисы (с названиями)
   - Команды, конфиги, сниппеты которые реально работают
   - Грабли на которые наступили и как обошли
   - Ссылки если релевантны
3. Вывод/инсайт (1-2 предложения, что вынес)

Стиль:
- Разговорный, от первого лица
- Без воды, без мотивашек, без "ты молодец"
- Мат допустим если уместен
- Конкретика > абстракции

Длина: 200-500 слов.

Форматирование (Telegram MarkdownV2):
- Жирный: *текст*
- Код inline: `команда`
- Блок кода: ```язык\\nкод```
- Списки через дефис
- Никаких заголовков с ###

Anti-slop правила (ОБЯЗАТЕЛЬНО):
- Миксуй длину предложений: короткие (3-5 слов) с длинными (25+). Никогда 3+ подряд одной длины
- Никогда не группируй ровно по 3 (примера, пункта, прилагательных). Два или четыре
- Запрещённые слова: ключевой, фундаментальный, трансформативный, экосистема (в переносном), ландшафт (в переносном), путешествие (в переносном), инновационный, бесшовный, комплексный, динамичный, надёжный
- Вместо "служит как", "является свидетельством", "играет важную роль" — пиши прямо что делает
- Не начинай с "В современном мире", "В эпоху AI", "В контексте"
- Не заканчивай предложения причастными оборотами типа "подчёркивая важность..."
- Не хеджируй: "некоторые считают", "эксперты утверждают" — назови конкретно кто
- Займи позицию. "Это не работает потому что..." вместо "с одной стороны X, с другой Y"
- Добавляй текстуру: оборванная мысль, самокоррекция, casual вставка в серьёзном тексте
- Используй сокращения: "не" вместо "не является", живой язык вместо канцелярита

НЕ писать:
- "Таким образом...", "В заключение...", "Подводя итоги...", "Стоит отметить..."
- "Не просто X, а Y", "Не только X, но и Y"
- Общие фразы без конкретики ("настроил штуку", "поработал над проектом")
- Формальный язык, канцелярит
- Длинные нумерованные списки
- Абзацы с одинаковой структурой (тезис → пример → вывод) — ломай паттерн"""


@beartype
def extract_last_session(dev_context: str) -> str:
    """Extract the most recent ### session from История изменений."""
    match = re.search(r"## История изменений\n(.+?)(?=\n## |\Z)", dev_context, re.DOTALL)
    if not match:
        raise ValueError("История изменений section not found in DEV_CONTEXT.md")

    history = match.group(1)
    sections = re.split(r"\n(?=### )", history)
    session_sections = [s.strip() for s in sections if s.strip().startswith("###")]

    if not session_sections:
        raise ValueError("No session entries found in История изменений")

    return session_sections[0]  # First = most recent


@beartype
def generate_article(session_log: str) -> str:
    """Generate Telegram post from session log using Gemini API."""
    client = genai.Client()

    response = client.models.generate_content(
        model=MODEL,
        contents=f"{WRITING_STYLE}\n\nНапиши пост для Telegram-канала на основе этого лога сессии разработки.\n\n{session_log}",
    )

    return response.text  # type: ignore[return-value]


@beartype
def send_file_to_telegram(filepath: Path, caption: str, token: str, chat_id: str) -> int:
    """Send file to Telegram. Returns message_id."""
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with open(filepath, "rb") as f:
        response = httpx.post(
            url,
            data={"chat_id": chat_id, "caption": caption},
            files={"document": (filepath.name, f)},
            timeout=30,
        )
    response.raise_for_status()
    result: dict[str, object] = response.json()
    message = result["result"]  # type: ignore[index]
    return int(message["message_id"])  # type: ignore[index]


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    if not os.environ.get("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY required", file=sys.stderr)
        sys.exit(1)

    if not dry_run:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required", file=sys.stderr)
            sys.exit(1)
    else:
        token, chat_id = "", ""

    # Read and parse
    text = DEV_CONTEXT.read_text(encoding="utf-8")
    last_session = extract_last_session(text)

    title_line = last_session.splitlines()[0]
    print(f"Session: {title_line}")

    # Generate
    print(f"Generating via {MODEL}...")
    article = generate_article(last_session)

    # Save as .md (always, even in dry-run)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    md_path = ROOT / "data" / "posts" / f"cortex_post_{date_str}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(article, encoding="utf-8")

    print(f"\n{'='*50}\n{article}\n{'='*50}\n")
    print(f"Length: {len(article)} chars")
    print(f"Saved: {md_path}")

    if dry_run:
        print("Dry run — not sending to Telegram")
        return

    caption = f"Build log — {date_str}"
    msg_id = send_file_to_telegram(md_path, caption, token, chat_id)
    print(f"Sent to Telegram: message_id={msg_id}")


if __name__ == "__main__":
    main()
