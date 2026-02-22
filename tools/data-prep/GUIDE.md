# Data Preparation for AI

Универсальный инструмент для подготовки больших объёмов данных к AI-анализу.

## Поддерживаемые форматы

| Формат | Источник | Обработка |
|--------|----------|-----------|
| JSON | Telegram, Discord экспорты | `prepare_for_ai.py` |
| TXT/MD | Книги, документация | Chunking по токенам |
| PDF | Документы, книги | Извлечение текста + chunking |
| EPUB | Электронные книги | Конвертация + chunking |

## Использование

```bash
# Telegram чат -> chunks по 500K токенов
python tools/data-prep/prepare_for_ai.py --mode chunk --input files/result.json

# Фильтр по темам
python tools/data-prep/prepare_for_ai.py --mode topic --topic "<тема>"

# Быстрая сводка
python tools/data-prep/prepare_for_ai.py --mode summary

# Извлечение тредов обсуждений
python tools/data-prep/prepare_for_ai.py --mode thread --min-replies 3

# Анализ нарративов (биграммы, тренды, связи)
python tools/data-prep/prepare_for_ai.py --mode narratives --period month
```

## Формат вывода

Compact JSON для экономии токенов:

```json
{
  "meta": {"source": "telegram", "total": 34000, "filtered": 500},
  "messages": [
    {"t": "2026-01-26T12:00", "u": "User", "m": "текст"}
  ]
}
```

Файлы сохраняются в `output/`:
- `chunk_*.json` — части по ~500K токенов
- `topic_*.json` — отфильтрованные сообщения
- `summary.md` — сводка для быстрого обзора
- `threads.json` — группированные обсуждения

## Темы (примеры)

| Тема | Ключевые слова |
|------|----------------|
| ai | claude, gpt, gemini, llm |
| dev | github, python, typescript, react |
| prompts | prompt, system, инструкция |
| automation | bot, script, workflow |

Темы расширяются в `TOPICS` внутри `prepare_for_ai.py`.
