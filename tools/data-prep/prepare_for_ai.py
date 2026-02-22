#!/usr/bin/env python3
"""
Подготовка данных для AI-анализа.

Поддерживаемые форматы:
- JSON (Telegram/Discord экспорты)
- TXT/MD (книги, документация)

Режимы:
- chunk: разбить на части по токенам
- topic: фильтровать по теме
- summary: компактная сводка
- thread: извлечь треды обсуждений
"""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

CHARS_PER_TOKEN = 3.5
DEFAULT_MAX_TOKENS = 500_000

# ============== Topic Keywords ==============
# Расширьте под свой проект — добавьте нужные темы

TOPICS = {
    "ai": ["ai", "claude", "gpt", "gemini", "copilot", "llm", "chatgpt", "openai", "модель"],
    "dev": ["code", "github", "python", "typescript", "react", "javascript", "api", "backend"],
    "prompts": ["prompt", "промпт", "system", "системный", "инструкция", "rules"],
    "automation": ["automation", "автоматизация", "script", "скрипт", "bot", "бот", "workflow"],
    # Добавьте свои темы:
    # "your_topic": ["keyword1", "keyword2", ...],
}


def extract_text(msg: dict) -> str:
    text_data = msg.get("text", "")
    if isinstance(text_data, str):
        return text_data
    elif isinstance(text_data, list):
        parts = []
        for item in text_data:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", ""))
        return " ".join(parts)
    return ""


def count_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)


def compact_message(msg: dict) -> dict | None:
    text = extract_text(msg)
    if not text.strip():
        return None
    compact = {
        "t": msg.get("date", "")[:16],
        "u": msg.get("from", msg.get("author", "Unknown")),
        "m": text,
    }
    reply_to = msg.get("reply_to_message_id")
    if reply_to:
        compact["r"] = reply_to
    return compact


def load_telegram_export(json_path: Path) -> tuple[dict, list]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    meta = {
        "source": "telegram",
        "chat": data.get("name", "Unknown"),
        "type": data.get("type", "unknown"),
        "export_date": datetime.now().isoformat()[:10],
    }
    messages = [m for m in data.get("messages", []) if m.get("type") == "message" and extract_text(m).strip()]
    return meta, messages


def load_text_file(path: Path) -> tuple[dict, list]:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    meta = {"source": "text", "filename": path.name, "export_date": datetime.now().isoformat()[:10]}
    messages = [{"text": p, "date": "", "from": "Document"} for p in paragraphs]
    return meta, messages


def load_messages(input_path: Path) -> tuple[dict, list]:
    suffix = input_path.suffix.lower()
    if suffix == ".json":
        return load_telegram_export(input_path)
    elif suffix in [".txt", ".md"]:
        return load_text_file(input_path)
    else:
        raise ValueError(f"Unsupported format: {suffix}")


def save_output(data: Any, output_path: Path, as_markdown: bool = False) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if as_markdown:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(data)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=None, separators=(",", ":"))
    print(f"✅ Saved: {output_path}")


def mode_chunk(messages: list, meta: dict, output_dir: Path, max_tokens: int = DEFAULT_MAX_TOKENS) -> None:
    chunks, current_chunk, current_tokens = [], [], 0
    for msg in messages:
        compact = compact_message(msg)
        if not compact:
            continue
        msg_tokens = count_tokens(json.dumps(compact, ensure_ascii=False))
        if current_tokens + msg_tokens > max_tokens and current_chunk:
            chunks.append(current_chunk)
            current_chunk, current_tokens = [], 0
        current_chunk.append(compact)
        current_tokens += msg_tokens
    if current_chunk:
        chunks.append(current_chunk)
    for i, chunk in enumerate(chunks, 1):
        chunk_data = {"meta": {**meta, "chunk": i, "total_chunks": len(chunks), "messages_count": len(chunk)}, "messages": chunk}
        save_output(chunk_data, output_dir / f"chunk_{i}.json")
    print(f"📦 Created {len(chunks)} chunks with ~{max_tokens} tokens each")


def mode_topic(messages: list, meta: dict, output_dir: Path, topics: list[str], min_length: int = 50) -> None:
    keywords = []
    for topic in topics:
        if topic in TOPICS:
            keywords.extend(TOPICS[topic])
        else:
            keywords.append(topic)
    keywords_lower = [k.lower() for k in keywords]
    filtered = []
    for msg in messages:
        text = extract_text(msg)
        text_lower = text.lower()
        if len(text) >= min_length and any(kw in text_lower for kw in keywords_lower):
            compact = compact_message(msg)
            if compact:
                filtered.append(compact)
    topic_name = "_".join(topics)
    output_data = {"meta": {**meta, "topic": topic_name, "keywords": keywords, "total": len(messages), "filtered": len(filtered)}, "messages": filtered}
    save_output(output_data, output_dir / f"topic_{topic_name}.json")
    print(f"🎯 Filtered {len(filtered)}/{len(messages)} messages for topics: {topics}")


def mode_summary(messages: list, meta: dict, output_dir: Path) -> None:
    total = len(messages)
    authors = Counter(m.get("from", m.get("author", "Unknown")) for m in messages)
    top_authors = authors.most_common(10)
    years = Counter()
    for msg in messages:
        date = msg.get("date", "")[:4]
        if date:
            years[date] += 1
    topic_counts = {}
    for topic_name, keywords in TOPICS.items():
        count = sum(1 for msg in messages if any(kw in extract_text(msg).lower() for kw in keywords))
        if count > 0:
            topic_counts[topic_name] = count
    top_messages = sorted([m for m in messages if len(extract_text(m)) > 200], key=lambda x: len(extract_text(x)), reverse=True)[:10]
    source_name = meta.get('chat', meta.get('filename', 'Unknown'))
    md = f"# Сводка: {source_name}\n\n**Дата анализа**: {datetime.now().isoformat()[:10]}\n**Всего элементов**: {total:,}\n\n## 📊 Активность по годам\n"
    for year in sorted(years.keys()):
        md += f"- **{year}**: {years[year]:,}\n"
    if top_authors:
        md += "\n## 👥 Топ-10 участников\n"
        for i, (author, count) in enumerate(top_authors, 1):
            md += f"{i}. **{author}**: {count:,}\n"
    md += "\n## 🏷️ Упоминания тем\n"
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        md += f"- **{topic}**: {count:,}\n"
    md += "\n## 💬 Самые длинные сообщения\n"
    for i, msg in enumerate(top_messages, 1):
        text = extract_text(msg)
        author = msg.get("from", msg.get("author", "Unknown"))
        date = msg.get("date", "")[:10]
        preview = text[:200].replace("\n", " ") + "..."
        md += f"\n### {i}. {author} ({date})\n> {preview}\n"
    save_output(md, output_dir / "summary.md", as_markdown=True)
    json_summary = {"meta": meta, "stats": {"total": total, "years": dict(years), "topic_mentions": topic_counts}, "top_authors": [{"name": a, "count": c} for a, c in top_authors], "sample_messages": [compact_message(m) for m in top_messages[:5] if compact_message(m)]}
    save_output(json_summary, output_dir / "summary.json")


def mode_thread(messages: list, meta: dict, output_dir: Path, min_replies: int = 3) -> None:
    msg_by_id = {m.get("id"): m for m in messages if m.get("id")}
    reply_counts = Counter()
    for msg in messages:
        reply_to = msg.get("reply_to_message_id")
        if reply_to:
            reply_counts[reply_to] += 1
    threads = []
    for msg_id, count in reply_counts.most_common():
        if count < min_replies:
            break
        if msg_id not in msg_by_id:
            continue
        root_msg = msg_by_id[msg_id]
        replies = [m for m in messages if m.get("reply_to_message_id") == msg_id]
        thread = {"root": compact_message(root_msg), "replies": [compact_message(r) for r in replies if compact_message(r)], "reply_count": count}
        threads.append(thread)
    output_data = {"meta": {**meta, "threads_count": len(threads), "min_replies": min_replies}, "threads": threads[:50]}
    save_output(output_data, output_dir / "threads.json")
    print(f"🧵 Extracted {len(threads)} threads with {min_replies}+ replies")


# ============== Mode: Narratives ==============

def mode_narratives(messages: list, meta: dict, output_dir: Path, period: str = "month") -> None:
    """Анализ нарративов: частотность, временные кластеры, co-occurrence."""
    import re
    from collections import defaultdict
    
    # Стоп-слова (русские + английские)
    STOP_WORDS = {
        "и", "в", "на", "с", "к", "о", "по", "за", "из", "у", "от", "до", "не", "что", "это", "как", "я", "он", "она",
        "мы", "вы", "они", "ты", "быть", "весь", "если", "так", "же", "но", "тоже", "для", "или", "бы", "уже",
        "только", "еще", "ещё", "да", "нет", "когда", "надо", "можно", "может", "потому", "там", "тут",
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
        "do", "does", "did", "will", "would", "could", "should", "may", "might", "can",
        "and", "or", "but", "if", "then", "else", "when", "at", "by", "for", "with", "about",
        "to", "from", "in", "on", "of", "it", "this", "that", "these", "those", "i", "you", "he", "she", "we", "they",
    }
    
    # Извлечение слов из текста
    def tokenize(text: str) -> list[str]:
        words = re.findall(r'[a-zа-яё]{3,}', text.lower())
        return [w for w in words if w not in STOP_WORDS and len(w) >= 3]
    
    # Биграммы
    def get_bigrams(words: list[str]) -> list[tuple[str, str]]:
        return [(words[i], words[i+1]) for i in range(len(words)-1)]
    
    # Группировка по периодам
    period_data = defaultdict(lambda: {"words": Counter(), "bigrams": Counter(), "count": 0})
    all_words = Counter()
    all_bigrams = Counter()
    co_occurrence = Counter()
    
    for msg in messages:
        text = extract_text(msg)
        date_str = msg.get("date", "")[:10]
        
        if period == "month":
            period_key = date_str[:7]  # YYYY-MM
        elif period == "quarter":
            month = int(date_str[5:7]) if len(date_str) >= 7 else 1
            q = (month - 1) // 3 + 1
            period_key = f"{date_str[:4]}-Q{q}"
        else:  # year
            period_key = date_str[:4]
        
        if not period_key or period_key == "":
            continue
            
        words = tokenize(text)
        bigrams = get_bigrams(words)
        
        period_data[period_key]["words"].update(words)
        period_data[period_key]["bigrams"].update(bigrams)
        period_data[period_key]["count"] += 1
        
        all_words.update(words)
        all_bigrams.update(bigrams)
        
        # Co-occurrence: пары слов в одном сообщении
        unique_words = list(set(words))
        for i, w1 in enumerate(unique_words):
            for w2 in unique_words[i+1:]:
                pair = tuple(sorted([w1, w2]))
                co_occurrence[pair] += 1
    
    # Формирование нарративов на основе топ-биграмм
    narratives = []
    for bigram, count in all_bigrams.most_common(20):
        # Найти пик активности
        peak_period = ""
        peak_count = 0
        for p, data in period_data.items():
            if bigram in data["bigrams"] and data["bigrams"][bigram] > peak_count:
                peak_count = data["bigrams"][bigram]
                peak_period = p
        
        # Связанные слова через co-occurrence
        related = []
        for (w1, w2), cnt in co_occurrence.most_common(100):
            if bigram[0] in (w1, w2) or bigram[1] in (w1, w2):
                other = w2 if w1 in bigram else w1
                if other not in bigram:
                    related.append(other)
            if len(related) >= 5:
                break
        
        narratives.append({
            "phrase": " ".join(bigram),
            "count": count,
            "peak_period": peak_period,
            "related": related[:5],
        })
    
    # Markdown отчёт
    source_name = meta.get('chat', meta.get('filename', 'Unknown'))
    md = f"""# Нарративы: {source_name}

**Дата анализа**: {datetime.now().isoformat()[:10]}
**Периодизация**: {period}

## 📊 Топ-20 нарративов (по частотным фразам)

"""
    for i, n in enumerate(narratives, 1):
        md += f"### {i}. {n['phrase']} ({n['count']:,} упом.)
"
        md += f"**Пик**: {n['peak_period']}\n"
        if n['related']:
            md += f"**Связанные**: {', '.join(n['related'])}\n"
        md += "\n"
    
    # Топ слова по периодам
    md += "## 📅 Ключевые слова по периодам\n\n"
    for p in sorted(period_data.keys())[-12:]:  # Последние 12 периодов
        top_words = [w for w, _ in period_data[p]["words"].most_common(8)]
        md += f"- **{p}**: {', '.join(top_words)}\n"
    
    # Co-occurrence топ
    md += "\n## 🔗 Сильные связи (co-occurrence)\n\n"
    for (w1, w2), cnt in co_occurrence.most_common(15):
        md += f"- **{w1}** ↔ **{w2}**: {cnt:,}\n"
    
    save_output(md, output_dir / "narratives.md", as_markdown=True)
    
    # JSON
    json_data = {
        "meta": meta,
        "narratives": narratives,
        "top_words": [w for w, _ in all_words.most_common(50)],
        "top_bigrams": [{"phrase": " ".join(b), "count": c} for b, c in all_bigrams.most_common(30)],
        "co_occurrence": [{"pair": list(p), "count": c} for p, c in co_occurrence.most_common(30)],
    }
    save_output(json_data, output_dir / "narratives.json")
    print(f"📝 Extracted {len(narratives)} narratives")


def main():
    parser = argparse.ArgumentParser(description="Подготовка данных для AI-анализа")
    parser.add_argument("--mode", choices=["chunk", "topic", "summary", "thread", "narratives"], default="summary")
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--topic", type=str, default="ai")
    parser.add_argument("--min-replies", type=int, default=3)
    parser.add_argument("--period", type=str, choices=["month", "quarter", "year"], default="month")
    args = parser.parse_args()
    if args.input is None:
        files_dir = Path(__file__).parent / "files"
        exports = list(files_dir.glob("**/*.json")) + list(files_dir.glob("**/*.txt"))
        if exports:
            args.input = exports[0]
            print(f"📂 Found: {args.input}")
        else:
            print("❌ No input found. Use --input to specify path.")
            return
    if not args.input.exists():
        print(f"❌ File not found: {args.input}")
        return
    print(f"📖 Loading {args.input}...")
    meta, messages = load_messages(args.input)
    print(f"📊 Loaded {len(messages):,} items from '{meta.get('chat', meta.get('filename', 'Unknown'))}'")
    if args.mode == "chunk":
        mode_chunk(messages, meta, args.output, args.tokens)
    elif args.mode == "topic":
        topics = [t.strip() for t in args.topic.split(",")]
        mode_topic(messages, meta, args.output, topics)
    elif args.mode == "summary":
        mode_summary(messages, meta, args.output)
    elif args.mode == "thread":
        mode_thread(messages, meta, args.output, args.min_replies)
    elif args.mode == "narratives":
        mode_narratives(messages, meta, args.output, args.period)
    print("✨ Done!")


if __name__ == "__main__":
    main()
