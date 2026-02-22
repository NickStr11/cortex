---
name: video
description: Analyze video by URL (metadata+subtitles) or local file (frames+transcription). Use when user asks to analyze, summarize, or review a video.
argument-hint: <path-or-url>
allowed-tools: Bash(uv run *), Read, Glob
---

Пользователь хочет проанализировать видео. Аргумент: путь к файлу или URL.

## Шаги

1. Запусти скрипт:
```bash
uv run tools/video/extract.py $ARGUMENTS
```

2. Прочитай `summary.json` из папки `video_output/`.

3. **Если URL** (mode: "url"):
   - Прочитай `metadata.json` — заголовок, описание, главы, теги
   - Прочитай `subtitles.txt` — полный текст субтитров
   - Просмотри `thumbnail.jpg` — превью видео
   - Дай саммари на основе описания + субтитров + глав

4. **Если локальный файл** (mode: "local"):
   - Прочитай `transcript.txt` — транскрипция аудио
   - Просмотри кадры из `frames/` (Read для изображений)
   - Дай саммари на основе кадров + транскрипции

5. Формат саммари:
   - О чём видео (тема, контекст)
   - Ключевые моменты с таймкодами (если есть главы/субтитры)
   - Основные тезисы
   - Выводы и рекомендации (если применимо)

## Параметры (только для локальных файлов)

- `--interval N` — интервал между кадрами (по умолчанию: 5)
- `--max-frames N` — максимум кадров (по умолчанию: 20)
- `--output DIR` — папка для вывода
- `--no-audio` — пропустить транскрипцию

## Если что-то не сработало

- ffmpeg не найден → `winget install ffmpeg`
- yt-dlp не найден → `winget install yt-dlp`
- Нет субтитров → саммари из описания и метаданных
- Нет API-ключа (локальный файл) → проверь `.env` (`OPENROUTER_API_KEY`)
- Транскрипция не удалась → проанализируй только кадры
