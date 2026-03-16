"""Telegram Group Digest — MapReduce pipeline.

Pipeline: Enrich → MAP (parallel chunks) → REDUCE → VERIFY
Adapted from sereja.tech/blog/digest-subagents-mapreduce

Usage:
    uv run python tools/tg-monitor/digest.py                   # generate + send
    uv run python tools/tg-monitor/digest.py --dry-run         # print only
    uv run python tools/tg-monitor/digest.py --hours 48        # last 48h

Requires env:
    GOOGLE_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""
from __future__ import annotations

import io
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx
from beartype import beartype
from google import genai

from config import (
    DATA_DIR,
    DIGEST_WINDOW_HOURS,
    GEMINI_MODEL,
    GROUPS,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)

# Fast model for MAP/VERIFY (cheap), Pro for REDUCE (quality)
GEMINI_MODEL_FAST = "gemini-2.0-flash"
try:
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")
except ZoneInfoNotFoundError:
    MOSCOW_TZ = timezone(timedelta(hours=3))
WEEKLY_MATERIALS_HOURS = 24 * 7

CHUNK_SIZE = 15  # messages per MAP chunk
URL_RE = re.compile(r"https?://\S+")
NUMBER_RE = re.compile(r"\b\d[\d\s.,/%$]*\b")

MAP_PROMPT = """Собери один сигнал из кластера сообщений Telegram-группы.

Правила:
- Не усредняй мнения: если это позиция одного человека, так и пиши
- Не превращай локальный спор в тренд всей индустрии
- Отделяй факт, мнение и гипотезу
- Конкретика: имена участников, инструменты, числа, ссылки
- Если есть URL — обязательно включи с коротким описанием
- Если сигнал слабый, прямо пометь это
- Не додумывай — только то, что явно написано
- 80-180 слов
- Русский, технические термины на английском

Формат:
**Сигнал: [название]**
- Сила сигнала: low | medium | high
- Кто говорил: [имена]
- Что обсуждали: [2-4 предложения]
- Инструменты/модели: [если есть]
- Ссылки: [если есть]
- Практический смысл: [зачем это важно]
"""

REDUCE_PROMPT = """Собери полезный дайджест Telegram-группы из извлечённых сигналов.

Структура:
1. *Что появилось с прошлого выпуска* — 2-4 буллета именно про текущее окно наблюдения
2. *Главные сигналы* — 3-5 самых полезных тем, с привязкой к участникам
3. *Кейсы и практики* — кто что реально сделал, протестировал или выкатил
4. *Инструменты и модели* — что хвалят, что ругают, где ограничения
5. *Ссылки* — каждый URL с однострочным пояснением
6. *Что стоит проверить* — 2-4 практических вывода или идеи для теста

Правила:
- 350-900 слов
- Конкретика: имена, инструменты, числа
- Дайджест должен ощущаться как выпуск за конкретное окно наблюдения, а не вечный общий обзор
- В секции "Что появилось с прошлого выпуска" пиши только про то, что всплыло, изменилось или усилилось в текущем окне
- Если тема не новая, но продолжилась, так и напиши: "снова всплыло", "продолжилось", "дожали"
- Каждое сильное утверждение привязывай к участнику или группе участников
- Если это просто мнение, формулируй как мнение, а не как факт
- Если данные слабые или спорные — прямо это укажи
- Не делай напыщенных общих выводов уровня "рынок решил" или "все пришли к выводу"
- Не пропускай ссылки
- Формат для Telegram: короткие абзацы, *жирный*, списки через дефис
- Если тема пересекается с предыдущими выпусками, укажи связь: "в прошлом выпуске обсуждали X, сегодня Y"
- В секции "Что стоит проверить" ссылайся на предыдущие рекомендации если они всё ещё актуальны
- Русский, технические термины на английском
- Пропусти болтовню, оффтоп
- Не пиши "В заключение...", "Подводя итоги..."
- Если ничего интересного — так и скажи

Формат:
*Дайджест {group_name} — {date}*

[Структурированный отчёт]
"""

VERIFY_PROMPT = """Проверь дайджест на фактическую точность и на раздувание выводов.

Сверь КАЖДОЕ утверждение дайджеста с исходными сообщениями.

Для каждого факта:
- CONFIRMED — есть прямое подтверждение в сообщениях
- UNVERIFIED — нет источника, но возможно
- HALLUCINATION — противоречит сообщениям или выдумано
- OVERSTATED — в дайджесте это звучит как общий вывод, хотя в источнике это частное мнение

Формат:
ФАКТ: [утверждение]
СТАТУС: [CONFIRMED/UNVERIFIED/HALLUCINATION/OVERSTATED]
ИСТОЧНИК: [цитата из сообщения или "не найден"]

В конце: итого X confirmed, Y unverified, Z hallucinations.
Если есть HALLUCINATION или OVERSTATED — предложи более точную формулировку.
"""

WEEKLY_MATERIALS_PROMPT = """Собери раздел *Топ материалы за неделю* по материалам, которые тащили в чат.

Правила:
- Возьми только реально переданные URL из входных данных
- Выбери 3-5 самых стоящих материалов
- Пиши по-русски, коротко и по делу
- Не выдумывай содержимое статьи; опирайся только на URL, сниппеты и контекст сообщений
- Если точного названия материала не видно, можно использовать домен или короткое описание по сниппету

Формат:
*Топ материалы за неделю*
- [название](url) — почему это вообще тащили в чат / что там полезного
"""


# --- Enrichment ---


@beartype
def group_keywords(group_name: str) -> list[str]:
    """Return configured keywords for a group name."""
    normalized = group_name.strip().lower()
    for group in GROUPS:
        if group.name.lower() == normalized:
            return group.keywords
    return []


@beartype
def compute_signal_metadata(
    text: str,
    reply_text: str,
    has_media: bool,
    engagement_score: float,
    keywords: list[str],
) -> tuple[float, list[str], bool, bool]:
    """Compute a richer score than replies/thread size alone."""
    combined = f"{text}\n{reply_text}".lower()
    matched_keywords = sorted({keyword for keyword in keywords if keyword.lower() in combined})
    has_url = URL_RE.search(text) is not None
    has_numbers = NUMBER_RE.search(text) is not None

    score = engagement_score
    score += min(len(matched_keywords), 4) * 0.8
    if has_url:
        score += 1.4
    if has_numbers:
        score += 0.6
    if reply_text:
        score += 0.4
    if has_media:
        score += 0.2

    return round(score, 2), matched_keywords[:4], has_url, has_numbers


@beartype
def utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


@beartype
def parse_message_date(date_str: str) -> datetime | None:
    """Parse ISO message datetime with UTC fallback."""
    if not date_str:
        return None
    try:
        message_date = datetime.fromisoformat(date_str)
    except ValueError:
        return None
    if message_date.tzinfo is None:
        message_date = message_date.replace(tzinfo=timezone.utc)
    return message_date


@beartype
def format_window_label(window_end: datetime, hours: int) -> str:
    """Format the digest window in Moscow time."""
    window_start = window_end - timedelta(hours=hours)
    start_msk = window_start.astimezone(MOSCOW_TZ).strftime("%Y-%m-%d %H:%M")
    end_msk = window_end.astimezone(MOSCOW_TZ).strftime("%Y-%m-%d %H:%M")
    return f"{start_msk} -> {end_msk} МСК"


@beartype
def build_freshness_context(messages: list[dict[str, object]], window_end: datetime, hours: int) -> str:
    """Build compact metadata so the digest feels tied to a concrete time window."""
    parsed_dates = [
        parsed
        for msg in messages
        if (parsed := parse_message_date(str(msg.get("date", "")))) is not None
    ]
    if not parsed_dates:
        return "Нет валидных временных меток."

    first_message = min(parsed_dates).astimezone(MOSCOW_TZ).strftime("%Y-%m-%d %H:%M МСК")
    last_message = max(parsed_dates).astimezone(MOSCOW_TZ).strftime("%Y-%m-%d %H:%M МСК")
    recent_6h_cutoff = window_end - timedelta(hours=min(6, hours))
    recent_3h_cutoff = window_end - timedelta(hours=min(3, hours))
    messages_6h = sum(1 for dt in parsed_dates if dt >= recent_6h_cutoff)
    messages_3h = sum(1 for dt in parsed_dates if dt >= recent_3h_cutoff)

    return "\n".join([
        f"- Окно наблюдения: {format_window_label(window_end, hours)}",
        f"- Сообщений в окне: {len(messages)}",
        f"- Сообщений за последние 6 часов окна: {messages_6h}",
        f"- Сообщений за последние 3 часа окна: {messages_3h}",
        f"- Первое сообщение окна: {first_message}",
        f"- Последнее сообщение окна: {last_message}",
    ])


@beartype
def inject_window_label(digest: str, window_label: str) -> str:
    """Insert the explicit Moscow-time observation window into the digest."""
    if "Окно наблюдения" in digest:
        return digest

    lines = digest.splitlines()
    window_line = f"*Окно наблюдения:* {window_label}"
    if lines and lines[0].startswith("*Дайджест "):
        return "\n".join([lines[0], "", window_line, *lines[1:]])
    return f"{window_line}\n\n{digest}"


@beartype
def normalize_url(url: str) -> str:
    """Normalize URLs extracted from Telegram messages."""
    return url.strip().rstrip(").,!?]>\"'")


@beartype
def extract_message_urls(text: str) -> list[str]:
    """Extract unique normalized URLs from a message."""
    urls: list[str] = []
    seen: set[str] = set()
    for raw_url in URL_RE.findall(text):
        normalized = normalize_url(raw_url)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        urls.append(normalized)
    return urls


@beartype
def collect_weekly_material_candidates(
    messages: list[dict[str, object]],
    top_n: int = 5,
) -> list[dict[str, object]]:
    """Aggregate the most-cited materials from the last week."""
    candidates: dict[str, dict[str, object]] = {}

    for msg in messages:
        text = str(msg.get("text", "")).strip()
        if not text:
            continue

        urls = extract_message_urls(text)
        if not urls:
            continue

        sender = str(msg.get("sender_name", "Unknown")).strip() or "Unknown"
        date_str = str(msg.get("date", ""))
        snippet = " ".join(text.split())
        if len(snippet) > 220:
            snippet = f"{snippet[:217]}..."

        try:
            score = float(msg.get("signal_score", msg.get("engagement_score", 0.0)))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            score = 0.0

        for url in urls:
            item = candidates.setdefault(
                url,
                {
                    "url": url,
                    "mentions": 0,
                    "score": 0.0,
                    "senders": set(),
                    "snippets": [],
                    "first_seen": date_str,
                    "last_seen": date_str,
                    "domain": urlparse(url).netloc.replace("www.", ""),
                },
            )
            item["mentions"] = int(item["mentions"]) + 1
            item["score"] = float(item["score"]) + 1.0 + score

            senders = item["senders"]
            if isinstance(senders, set):
                senders.add(sender)

            snippets = item["snippets"]
            if isinstance(snippets, list) and snippet and snippet not in snippets and len(snippets) < 3:
                snippets.append(snippet)

            first_seen = str(item.get("first_seen", ""))
            last_seen = str(item.get("last_seen", ""))
            if date_str and (not first_seen or date_str < first_seen):
                item["first_seen"] = date_str
            if date_str and (not last_seen or date_str > last_seen):
                item["last_seen"] = date_str

    ranked = sorted(
        candidates.values(),
        key=lambda item: (
            float(item.get("score", 0.0)),
            int(item.get("mentions", 0)),
        ),
        reverse=True,
    )

    normalized: list[dict[str, object]] = []
    for item in ranked[:top_n]:
        senders = item.get("senders", set())
        snippets = item.get("snippets", [])
        normalized.append(
            {
                "url": str(item.get("url", "")),
                "domain": str(item.get("domain", "")),
                "mentions": int(item.get("mentions", 0)),
                "score": round(float(item.get("score", 0.0)), 2),
                "senders": sorted(str(sender) for sender in senders)[:4] if isinstance(senders, set) else [],
                "snippets": [str(snippet) for snippet in snippets][:3] if isinstance(snippets, list) else [],
                "first_seen": str(item.get("first_seen", "")),
                "last_seen": str(item.get("last_seen", "")),
            }
        )
    return normalized


@beartype
def render_weekly_materials_fallback(candidates: list[dict[str, object]]) -> str | None:
    """Render weekly materials deterministically if the model output is weak."""
    if not candidates:
        return None

    lines = ["*Топ материалы за неделю*"]
    for item in candidates:
        url = str(item.get("url", ""))
        if not url:
            continue

        domain = str(item.get("domain", "")) or url
        mentions = int(item.get("mentions", 0))
        senders = item.get("senders", [])
        snippets = item.get("snippets", [])

        reason_parts = [f"упоминали {mentions} раз" if mentions > 1 else "принесли в чат"]
        if isinstance(senders, list) and senders:
            reason_parts.append(f"тащили {', '.join(str(sender) for sender in senders[:3])}")
        if isinstance(snippets, list) and snippets:
            reason_parts.append(str(snippets[0]))

        lines.append(f"- [{domain}]({url}) — {'; '.join(reason_parts)}")

    return "\n".join(lines) if len(lines) > 1 else None


@beartype
def build_weekly_materials_section(messages: list[dict[str, object]]) -> str | None:
    """Build a compact 7-day top-materials block from chat-shared URLs."""
    candidates = collect_weekly_material_candidates(messages)
    if not candidates:
        return None

    payload_lines: list[str] = []
    for index, item in enumerate(candidates, start=1):
        snippets = item.get("snippets", [])
        snippet_block = "\n".join(
            f"- {snippet}" for snippet in snippets[:3]
        ) if isinstance(snippets, list) and snippets else "- нет сниппетов"
        senders = item.get("senders", [])
        payload_lines.append(
            "\n".join([
                f"{index}. url={item['url']}",
                f"domain={item['domain']}",
                f"mentions={item['mentions']}",
                f"score={item['score']}",
                f"senders={', '.join(str(sender) for sender in senders)}",
                "snippets:",
                snippet_block,
            ])
        )

    generated = ""
    try:
        generated = call_gemini(
            WEEKLY_MATERIALS_PROMPT,
            "\n\n".join(payload_lines),
            model=GEMINI_MODEL_FAST,
        ).strip()
    except Exception as e:
        print(f"    WEEKLY MATERIALS error: {e}")

    if generated:
        normalized = generated.strip()
        if normalized.startswith("### Топ материалы за неделю"):
            normalized = normalized.replace("### Топ материалы за неделю", "*Топ материалы за неделю*", 1)
        elif not normalized.startswith("*Топ материалы за неделю*"):
            normalized = f"*Топ материалы за неделю*\n{normalized}"
        link_count = len(re.findall(r"\[.+?\]\(https?://.+?\)", normalized))
        if link_count >= max(1, min(2, len(candidates))):
            return normalized

    return render_weekly_materials_fallback(candidates)


@beartype
def inject_weekly_materials_section(digest: str, weekly_section: str | None) -> str:
    """Append weekly materials without touching the verified 24h digest body."""
    if not weekly_section or "Топ материалы за неделю" in digest:
        return digest
    return f"{digest.rstrip()}\n\n{weekly_section.strip()}"

@beartype
def enrich_messages(messages: list[dict[str, object]]) -> list[dict[str, object]]:
    """Add engagement scores and resolve reply_to context."""
    msg_index: dict[int, dict[str, object]] = {}
    keywords = group_keywords(str(messages[0].get("group", ""))) if messages else []
    for msg in messages:
        msg_index[int(msg["message_id"])] = msg  # type: ignore[arg-type]

    # Count replies per message
    reply_counts: dict[int, int] = {}
    thread_sizes: dict[int, int] = {}
    for msg in messages:
        reply_to = msg.get("reply_to")
        if reply_to is not None:
            rid = int(reply_to)  # type: ignore[arg-type]
            reply_counts[rid] = reply_counts.get(rid, 0) + 1
            # Thread = root message
            thread_sizes[rid] = thread_sizes.get(rid, 0) + 1

    enriched: list[dict[str, object]] = []
    for msg in messages:
        mid = int(msg["message_id"])  # type: ignore[arg-type]
        replies = reply_counts.get(mid, 0)
        thread = thread_sizes.get(mid, 0)
        score = replies * 2.0 + thread * 0.5

        enriched_msg = dict(msg)
        enriched_msg["engagement_score"] = score

        # Resolve reply_to text
        reply_to = msg.get("reply_to")
        if reply_to is not None:
            parent = msg_index.get(int(reply_to))  # type: ignore[arg-type]
            if parent:
                enriched_msg["reply_to_text"] = parent.get("text", "")
                enriched_msg["reply_to_sender"] = parent.get("sender_name", "")

        signal_score, matched_keywords, has_url, has_numbers = compute_signal_metadata(
            text=str(enriched_msg.get("text", "")),
            reply_text=str(enriched_msg.get("reply_to_text", "")),
            has_media=bool(enriched_msg.get("has_media", False)),
            engagement_score=score,
            keywords=keywords,
        )
        enriched_msg["signal_score"] = signal_score
        enriched_msg["matched_keywords"] = matched_keywords
        enriched_msg["has_url"] = has_url
        enriched_msg["has_numbers"] = has_numbers

        enriched.append(enriched_msg)

    return enriched


@beartype
def filter_top_messages(messages: list[dict[str, object]], top_n: int = 100) -> list[dict[str, object]]:
    """Filter top messages by signal score, keep chronological order."""
    scored = [m for m in messages if float(m.get("signal_score", 0)) >= 2.0]  # type: ignore[arg-type]
    if len(scored) < 5:
        scored = list(messages)
    scored.sort(
        key=lambda m: (
            float(m.get("signal_score", 0)),  # type: ignore[arg-type]
            float(m.get("engagement_score", 0)),  # type: ignore[arg-type]
        ),
        reverse=True,
    )
    top = scored[:top_n]
    # Restore chronological order
    top.sort(key=lambda m: str(m.get("date", "")))
    return top


# --- Format ---

@beartype
def format_chunk(messages: list[dict[str, object]]) -> str:
    """Format a chunk of messages for LLM."""
    lines: list[str] = []
    for msg in messages:
        sender = msg.get("sender_name", "Unknown")
        text = str(msg.get("text", ""))
        date = str(msg.get("date", ""))[:16]
        signal_score = float(msg.get("signal_score", 0))
        engagement_score = float(msg.get("engagement_score", 0))

        reply_ctx = ""
        reply_text = msg.get("reply_to_text")
        reply_sender = msg.get("reply_to_sender")
        if reply_text:
            short = str(reply_text)[:100]
            reply_ctx = f" [ответ на {reply_sender}: {short}]"

        feature_bits: list[str] = []
        matched_keywords = msg.get("matched_keywords")
        if isinstance(matched_keywords, list) and matched_keywords:
            joined = ", ".join(str(keyword) for keyword in matched_keywords)
            feature_bits.append(f"keywords={joined}")
        if bool(msg.get("has_url", False)):
            feature_bits.append("url")
        if bool(msg.get("has_numbers", False)):
            feature_bits.append("numbers")
        if bool(msg.get("has_media", False)):
            feature_bits.append("media")

        features = f" [{' | '.join(feature_bits)}]" if feature_bits else ""
        lines.append(
            f"[{date}] {sender} [signal={signal_score:.1f}, engagement={engagement_score:.1f}]"
            f"{reply_ctx}{features} {text}"
        )
    return "\n".join(lines)


# --- Gemini calls ---

@beartype
def call_gemini(prompt: str, content: str, model: str | None = None) -> str:
    """Single Gemini API call."""
    client = genai.Client()
    response = client.models.generate_content(
        model=model or GEMINI_MODEL,
        contents=f"{prompt}\n\n{content}",
    )
    return response.text or ""


# --- Pipeline ---

@beartype
def pipeline_map(chunks: list[list[dict[str, object]]]) -> list[str]:
    """MAP: extract one topic per chunk (fast model)."""
    topics: list[str] = []
    for i, chunk in enumerate(chunks):
        formatted = format_chunk(chunk)
        print(f"    MAP [{i+1}/{len(chunks)}] ({len(chunk)} msgs)...")
        topic = call_gemini(MAP_PROMPT, formatted, model=GEMINI_MODEL_FAST)
        topics.append(topic)
    return topics


@beartype
def pipeline_reduce(
    group_name: str,
    topics: list[str],
    messages: list[dict[str, object]],
    hours: int,
    window_end: datetime | None = None,
) -> str:
    """REDUCE: assemble topics into a time-bounded digest."""
    current_window_end = window_end or utc_now()
    date_str = current_window_end.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y")
    window_label = format_window_label(current_window_end, hours)
    freshness_context = build_freshness_context(messages, current_window_end, hours)
    prompt = REDUCE_PROMPT.format(group_name=group_name, date=date_str)
    combined = (
        f"ОКНО НАБЛЮДЕНИЯ:\n{window_label}\n\n"
        f"КОНТЕКСТ СВЕЖЕСТИ:\n{freshness_context}\n\n"
        + "\n\n---\n\n".join(f"Тема {i+1}:\n{t}" for i, t in enumerate(topics))
    )
    print(f"    REDUCE ({len(topics)} topics → digest)...")
    digest = call_gemini(prompt, combined)
    return inject_window_label(digest, window_label)


@beartype
def pipeline_verify(digest: str, messages: list[dict[str, object]]) -> str:
    """VERIFY: fact-check digest against source messages (fast model)."""
    source = format_chunk(messages)  # all filtered messages for accurate verification
    content = f"ДАЙДЖЕСТ:\n{digest}\n\nИСХОДНЫЕ СООБЩЕНИЯ:\n{source}"
    print("    VERIFY (fact-check)...")
    return call_gemini(VERIFY_PROMPT, content, model=GEMINI_MODEL_FAST)


@beartype
def has_verification_issues(verify_result: str) -> bool:
    """Detect real verify failures without triggering on summary counts."""
    upper = verify_result.upper()
    return re.search(r":\s*(HALLUCINATION|OVERSTATED)\b", upper) is not None


# --- Load ---

@beartype
def load_recent_messages(
    hours: int,
    window_end: datetime | None = None,
) -> dict[str, list[dict[str, object]]]:
    """Load messages from all groups within the time window."""
    current_window_end = window_end or utc_now()
    cutoff = current_window_end - timedelta(hours=hours)
    result: dict[str, list[dict[str, object]]] = {}

    for group in GROUPS:
        safe_name = group.name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        path = DATA_DIR / f"{safe_name}.json"
        if not path.exists():
            print(f"  No data for {group.name} ({path})")
            continue

        all_msgs: list[dict[str, object]] = json.loads(path.read_text(encoding="utf-8"))
        recent = []
        for msg in all_msgs:
            date_str = str(msg.get("date", ""))
            if not date_str:
                continue
            msg_date = parse_message_date(date_str)
            if msg_date is None:
                continue
            if msg_date >= cutoff:
                recent.append(msg)

        if recent:
            result[group.name] = recent
            print(f"  {group.name}: {len(recent)} messages in last {hours}h")
        else:
            print(f"  {group.name}: no messages in last {hours}h")

    return result


# --- Send ---

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


# --- Main ---

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="TG Group Digest (MapReduce)")
    parser.add_argument("--dry-run", action="store_true", help="Print only, don't send")
    parser.add_argument("--hours", type=int, default=DIGEST_WINDOW_HOURS, help="Time window in hours")
    parser.add_argument("--no-verify", action="store_true", help="Skip verification step")
    args = parser.parse_args()

    if not os.environ.get("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY required", file=sys.stderr)
        sys.exit(1)

    token = TELEGRAM_BOT_TOKEN
    chat_id = TELEGRAM_CHAT_ID
    if not args.dry_run and (not token or not chat_id):
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required", file=sys.stderr)
        sys.exit(1)

    current_window_end = utc_now()
    print(f"Loading messages from last {args.hours}h...")
    groups_messages = load_recent_messages(args.hours, window_end=current_window_end)
    weekly_groups_messages = load_recent_messages(
        WEEKLY_MATERIALS_HOURS,
        window_end=current_window_end,
    )

    if not groups_messages:
        print("No recent messages found. Run monitor.py first.")
        sys.exit(0)

    for group_name, messages in groups_messages.items():
        print(f"\n{'='*50}")
        print(f"Pipeline for {group_name} ({len(messages)} messages)")
        print(f"{'='*50}")

        # 1. Enrich
        print("  ENRICH: engagement scores + reply_to context...")
        enriched = enrich_messages(messages)

        # 2. Filter
        top = filter_top_messages(enriched)
        if len(top) < 5:
            # Not enough engaging messages, use all (sorted by date)
            top = sorted(enriched, key=lambda m: str(m.get("date", "")))
        print(f"  FILTER: {len(messages)} → {len(top)} messages (signal score priority)")

        # 3. MAP: split into chunks
        n_chunks = max(1, math.ceil(len(top) / CHUNK_SIZE))
        chunks = [top[i * CHUNK_SIZE:(i + 1) * CHUNK_SIZE] for i in range(n_chunks)]
        print(f"  MAP: {n_chunks} chunks × ~{CHUNK_SIZE} messages")
        topics = pipeline_map(chunks)

        # 4. REDUCE
        digest = pipeline_reduce(
            group_name,
            topics,
            top,
            args.hours,
            window_end=current_window_end,
        )

        # 5. VERIFY
        if not args.no_verify:
            verify_result = pipeline_verify(digest, top)
            print(f"\nVERIFY:\n{verify_result}")

            if has_verification_issues(verify_result):
                print("\n  WARNING: verification flagged issues, check output above")

        weekly_messages = weekly_groups_messages.get(group_name, [])
        if weekly_messages:
            weekly_enriched = enrich_messages(weekly_messages)
            weekly_section = build_weekly_materials_section(weekly_enriched)
            digest = inject_weekly_materials_section(digest, weekly_section)
            if weekly_section:
                print(f"  WEEKLY MATERIALS: {len(weekly_messages)} messages scanned")

        print(f"\n{digest}\n")
        print(f"Length: {len(digest)} chars")

        if args.dry_run:
            print("Dry run — not sending")
            continue

        # Save and send
        safe_name = group_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        date_str = current_window_end.astimezone(MOSCOW_TZ).strftime("%Y-%m-%d")
        md_path = DATA_DIR / f"{safe_name}_digest_{date_str}.md"
        md_path.write_text(digest, encoding="utf-8")
        print(f"Saved: {md_path}")

        caption = f"Дайджест {group_name} — {date_str}"
        msg_id = send_file_to_telegram(md_path, caption, token, chat_id)
        print(f"Sent to Telegram: message_id={msg_id}")


if __name__ == "__main__":
    main()
