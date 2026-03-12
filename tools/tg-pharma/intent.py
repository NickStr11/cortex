from __future__ import annotations

import json
import mimetypes
import re
from pathlib import Path
from typing import Any

from beartype import beartype
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError


class ParsedIntent(BaseModel):
    action: str = Field(default="unknown")
    query: str = Field(default="")
    qty: int | None = Field(default=None)
    period: str | None = Field(default="last_month")
    compare_period: str | None = Field(default=None)
    confidence: float = Field(default=0.0)
    note: str = Field(default="")


NAMED_PERIODS = {"last_month", "this_month", "last_90_days", "last_180_days", "all_time"}

INVENTORY_PREFIXES = (
    "поставь остаток",
    "установи остаток",
    "сделай остаток",
    "измени остаток",
    "обнови остаток",
    "остаток",
)

ADD_HINTS = (
    "добавь",
    "добавить",
    "прибавь",
    "увеличь",
    "в остатки добавить",
    "докинь",
    "накинь",
    "домаркируй",
    "домаркировать",
    "плюс",
)

SUBTRACT_HINTS = (
    "убавь",
    "убрать",
    "уменьши",
    "спиши",
    "вычти",
    "убери из остатков",
)

DELETE_HINTS = (
    "удали из остатков",
    "удалить из остатков",
    "удалить",
    "удали",
    "убери совсем",
    "убери позицию",
    "снеси",
    "выпили",
)

DELETE_CONTEXT_MARKERS = (
    "эту позицию",
    "этой позиции",
    "этот товар",
    "этот препарат",
    "эту штуку",
    "эту",
    "этой",
    "этот",
)

CLEAR_HINTS = (
    "очисти остаток",
    "обнули остаток",
    "обнули",
    "сделай 0",
    "сделай ноль",
    "поставь 0",
    "поставь ноль",
    "чтобы там 0 было",
    "чтобы там ноль был",
)

RESTORE_HINTS = (
    "верни позицию назад",
    "верни назад",
    "восстанови позицию",
    "восстанови назад",
    "верни как было",
)

SHOW_HINTS = (
    "покажи остаток",
    "покажи что сейчас в остатках",
    "что сейчас в остатках",
    "сколько сейчас в остатках",
    "сколько в остатках",
    "какой остаток",
    "что по остаткам",
)

RESOLVE_PREFIXES = (
    "какой у нас обычно",
    "какой у нас",
    "какой обычно",
    "что у нас по",
    "какой",
    "что по",
)

CHAT_EXACT = {
    "привет",
    "привет!",
    "ты тут",
    "привет тут",
    "хай",
    "здарова",
}

UNIT_SUFFIX_RE = re.compile(
    r"\s*(шт|штука|штуки|штук|уп|упаковка|упаковки|упаковок|пачка|пачки|пачек)\s*$",
    re.IGNORECASE,
)
INT_RE = re.compile(r"\b(\d{1,5})\b")
WORD_QTY_MAP = {
    "один": 1,
    "одна": 1,
    "одно": 1,
    "одну": 1,
    "одной": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
}

RELATIVE_PERIOD_PATTERNS = (
    (r"за\s+(?:последн(?:ие|их|ий)\s+)?(\d{1,4})\s*д(ень|ня|ней)\b", 1),
    (r"за\s+(?:последн(?:ие|их|ий)\s+)?(\d{1,4})\s*нед(елю|ели|ель|еля|ель)\b", 7),
    (r"за\s+(?:последн(?:ие|их|ий)\s+)?(\d{1,4})\s*мес(яц|яца|яцев)?\b", 30),
    (r"за\s+(?:последн(?:ие|их|ий)\s+)?(\d{1,4})\s*год(а|ов)?\b", 365),
)


@beartype
def _clean_text(text: str) -> str:
    return " ".join(text.strip().split())


@beartype
def _strip_markdown(text: str) -> str:
    cleaned = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1: \2", text)
    cleaned = re.sub(r"[*_`#]+", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


@beartype
def normalize_period_value(period: str | None) -> str:
    normalized = (period or "last_month").strip().lower()
    if normalized in NAMED_PERIODS:
        return normalized
    match = re.fullmatch(r"last_(\d+)_days", normalized)
    if match and 1 <= int(match.group(1)) <= 3650:
        return normalized
    return "last_month"


@beartype
def previous_period_value(period: str | None) -> str:
    normalized = normalize_period_value(period)
    if normalized == "this_month":
        return "last_month"
    if normalized == "last_month":
        return "last_30_days"
    match = re.fullmatch(r"last_(\d+)_days", normalized)
    if match:
        return f"last_{match.group(1)}_days"
    if normalized == "all_time":
        return "last_180_days"
    return "last_month"


@beartype
def detect_relative_period(lowered: str) -> str | None:
    if "за полгода" in lowered or "за пол года" in lowered:
        return "last_180_days"

    for pattern, multiplier in RELATIVE_PERIOD_PATTERNS:
        match = re.search(pattern, lowered)
        if not match:
            continue
        amount = int(match.group(1))
        days = amount * multiplier
        if 1 <= days <= 3650:
            return f"last_{days}_days"
    return None


@beartype
def strip_relative_period_phrases(text: str) -> str:
    stripped = text
    for pattern, _multiplier in RELATIVE_PERIOD_PATTERNS:
        stripped = re.sub(pattern, " ", stripped, flags=re.IGNORECASE)
    return stripped


@beartype
def detect_compare_period(lowered: str, primary_period: str | None = None) -> str | None:
    if "с прошлым месяцем" in lowered or "против прошлого месяца" in lowered:
        return "last_month"
    if "с этим месяцем" in lowered or "против этого месяца" in lowered:
        return "this_month"
    if "с полугодием" in lowered or "с прошлым полугодием" in lowered:
        return "last_180_days"
    if "с 90 днями" in lowered:
        return "last_90_days"
    if "со всем временем" in lowered or "с общим периодом" in lowered:
        return "all_time"
    if "с прошлым периодом" in lowered or "по сравнению с прошлым периодом" in lowered:
        return previous_period_value(primary_period)
    return None


@beartype
def heuristic_parse_inventory_command(text: str) -> ParsedIntent | None:
    cleaned = _clean_text(text)
    lowered = cleaned.lower()
    action = "set_inventory"
    if any(hint in lowered for hint in ADD_HINTS):
        action = "add_inventory"
    elif any(hint in lowered for hint in SUBTRACT_HINTS):
        action = "subtract_inventory"
    matched_prefix = next((prefix for prefix in INVENTORY_PREFIXES if lowered.startswith(prefix)), None)
    if not matched_prefix and action == "set_inventory":
        return None

    qty_match = INT_RE.search(lowered)
    qty_word = None
    qty = None
    if qty_match is not None:
        qty = int(qty_match.group(1))
    else:
        tokens = re.findall(r"[а-яёa-z]+", lowered)
        qty_word = next((token for token in tokens if token in WORD_QTY_MAP), None)
        if qty_word is None:
            return None
        qty = WORD_QTY_MAP[qty_word]

    if matched_prefix and action == "set_inventory":
        if qty_match is not None:
            head = lowered[:qty_match.start()].strip(" ,.;:!?")
        else:
            head = re.sub(rf"\b{re.escape(qty_word)}\b", " ", lowered, count=1).strip(" ,.;:!?")
        query = head[len(matched_prefix):].strip(" ,.;:!?")
    else:
        if qty_match is not None:
            query = (lowered[:qty_match.start()] + " " + lowered[qty_match.end():]).strip(" ,.;:!?")
        else:
            query = re.sub(rf"\b{re.escape(qty_word)}\b", " ", lowered, count=1).strip(" ,.;:!?")
        for hint in (*ADD_HINTS, *SUBTRACT_HINTS):
            query = query.replace(hint, " ")
        for filler in ("давай", "попробуем", "пожалуйста", "еще", "ещё"):
            query = query.replace(filler, " ")

    query = re.sub(r"^(для|по)\s+", "", query, flags=re.IGNORECASE)
    query = re.sub(r"\b(в|во)\s+остатки\b", " ", query, flags=re.IGNORECASE)
    query = re.sub(r"\bок\b", " ", query, flags=re.IGNORECASE)
    query = re.sub(r"\b(шт|штук|штука|штуки)\b", " ", query, flags=re.IGNORECASE)
    query = UNIT_SUFFIX_RE.sub("", query).strip(" ,.;:!?")
    query = re.sub(r"\s+", " ", query).strip(" ,.;:!?")
    if not query:
        return None
    return ParsedIntent(action=action, query=query, qty=qty, confidence=0.98, note="heuristic")


@beartype
def heuristic_parse_inventory_delete(text: str) -> ParsedIntent | None:
    cleaned = _clean_text(text)
    lowered = cleaned.lower().strip(" ?!.")
    if not any(hint in lowered for hint in DELETE_HINTS):
        return None
    query = lowered
    for hint in sorted(DELETE_HINTS, key=len, reverse=True):
        query = re.sub(rf"\b{re.escape(hint)}\b", " ", query, flags=re.IGNORECASE)
    query = re.sub(r"\bиз\s+(остатков|inventory)\b", " ", query, flags=re.IGNORECASE)
    query = re.sub(r"\b(вообще|совсем|пока|надо|нужно)\b", " ", query, flags=re.IGNORECASE)
    if any(marker in lowered for marker in DELETE_CONTEXT_MARKERS):
        query = "эту позицию"
    query = re.sub(r"\s+", " ", query).strip(" ,.;:!?")
    if not query:
        query = "эту позицию"
    return ParsedIntent(action="delete_inventory", query=query, confidence=0.98, note="heuristic")


@beartype
def heuristic_parse_inventory_clear(text: str) -> ParsedIntent | None:
    cleaned = _clean_text(text)
    lowered = cleaned.lower().strip(" ?!.")
    if not any(hint in lowered for hint in CLEAR_HINTS):
        return None
    query = lowered
    for hint in sorted(CLEAR_HINTS, key=len, reverse=True):
        query = re.sub(rf"\b{re.escape(hint)}\b", " ", query, flags=re.IGNORECASE)
    query = re.sub(r"\bиз\s+(остатков|inventory)\b", " ", query, flags=re.IGNORECASE)
    if any(marker in lowered for marker in DELETE_CONTEXT_MARKERS):
        query = "эту позицию"
    query = re.sub(r"\b(пожалуйста|просто|наоборот|ок)\b", " ", query, flags=re.IGNORECASE)
    query = re.sub(r"\s+", " ", query).strip(" ,.;:!?")
    if not query:
        query = "эту позицию"
    return ParsedIntent(action="set_inventory", query=query, qty=0, confidence=0.98, note="heuristic")


@beartype
def heuristic_parse_inventory_restore(text: str) -> ParsedIntent | None:
    cleaned = _clean_text(text)
    lowered = cleaned.lower().strip(" ?!.")
    if not any(hint in lowered for hint in RESTORE_HINTS):
        return None
    return ParsedIntent(action="restore_inventory", query="последнюю удаленную позицию", confidence=0.98, note="heuristic")


@beartype
def heuristic_parse_inventory_show(text: str) -> ParsedIntent | None:
    cleaned = _clean_text(text)
    lowered = cleaned.lower().strip(" ?!.")
    if not any(hint in lowered for hint in SHOW_HINTS):
        return None
    query = lowered
    for hint in sorted(SHOW_HINTS, key=len, reverse=True):
        query = re.sub(rf"\b{re.escape(hint)}\b", " ", query, flags=re.IGNORECASE)
    query = re.sub(r"\b(по|для|у)\b", " ", query, flags=re.IGNORECASE)
    if any(marker in lowered for marker in DELETE_CONTEXT_MARKERS):
        query = "эту позицию"
    query = re.sub(r"\s+", " ", query).strip(" ,.;:!?")
    if not query:
        query = "эту позицию"
    return ParsedIntent(action="show_inventory", query=query, confidence=0.98, note="heuristic")


@beartype
def heuristic_parse_resolution_query(text: str) -> ParsedIntent | None:
    cleaned = _clean_text(text)
    lowered = cleaned.lower().strip(" ?!.")
    matched_prefix = next((prefix for prefix in RESOLVE_PREFIXES if lowered.startswith(prefix)), None)
    if not matched_prefix:
        return None
    query = lowered[len(matched_prefix):].strip(" ,.;:!?")
    query = re.sub(r"^(по|из)\s+", "", query, flags=re.IGNORECASE)
    if not query:
        return None
    return ParsedIntent(action="resolve_product", query=query, confidence=0.97, note="heuristic")


@beartype
def heuristic_parse_compare_suppliers(text: str) -> ParsedIntent | None:
    cleaned = _clean_text(text)
    lowered = cleaned.lower().strip(" ?!.")
    if "поставщик" not in lowered and "поставщикам" not in lowered and "у кого" not in lowered:
        return None
    if "сравни" not in lowered and "сравнить" not in lowered and "выгоднее" not in lowered and "чаще" not in lowered:
        return None
    period = detect_relative_period(lowered) or "last_month"
    if "в этом месяце" in lowered or "за этот месяц" in lowered:
        period = "this_month"
    elif "за все время" in lowered or "за всё время" in lowered or "за всё" in lowered or "за все" in lowered:
        period = "all_time"

    query = lowered
    for phrase in (
        "сравни по поставщикам",
        "сравнить по поставщикам",
        "по поставщикам",
        "у какого поставщика",
        "какой поставщик",
        "у кого чаще",
        "у кого выгоднее",
        "сравни",
        "сравнить",
        "выгоднее",
        "чаще",
        "в прошлом месяце",
        "в этом месяце",
        "за этот месяц",
        "за все время",
        "за всё время",
        "за всё",
        "за все",
        "за полгода",
        "за пол года",
    ):
        query = query.replace(phrase, " ")
    query = strip_relative_period_phrases(query)
    query = re.sub(r"^(а|ну|и)\s+", " ", query, flags=re.IGNORECASE)
    query = re.sub(r"\s+", " ", query).strip(" ,.;:!?")
    if not query:
        return None
    return ParsedIntent(action="compare_suppliers", query=query, period=period, confidence=0.96, note="heuristic")


@beartype
def heuristic_parse_compare_periods(text: str) -> ParsedIntent | None:
    cleaned = _clean_text(text)
    lowered = cleaned.lower().strip(" ?!.")
    if "поставщик" in lowered or "поставщикам" in lowered or "у кого" in lowered:
        return None
    if "сравни" not in lowered and "сравнить" not in lowered and "по сравнению" not in lowered:
        return None
    period = detect_relative_period(lowered) or "last_month"
    if "в этом месяце" in lowered or "за этот месяц" in lowered:
        period = "this_month"
    elif "за все время" in lowered or "за всё время" in lowered or "за всё" in lowered or "за все" in lowered:
        period = "all_time"
    compare_period = detect_compare_period(lowered, period) or previous_period_value(period)

    query = lowered
    for phrase in (
        "сравни",
        "сравнить",
        "по сравнению",
        "с прошлым месяцем",
        "с этим месяцем",
        "против прошлого месяца",
        "против этого месяца",
        "с прошлым периодом",
        "в прошлом месяце",
        "в этом месяце",
        "за этот месяц",
        "за все время",
        "за всё время",
        "за всё",
        "за все",
        "за полгода",
        "за пол года",
    ):
        query = query.replace(phrase, " ")
    query = strip_relative_period_phrases(query)
    query = re.sub(r"^(а|ну|и)\s+", " ", query, flags=re.IGNORECASE)
    query = re.sub(r"\s+", " ", query).strip(" ,.;:!?")
    if not query:
        return None
    return ParsedIntent(
        action="compare_periods",
        query=query,
        period=period,
        compare_period=compare_period,
        confidence=0.95,
        note="heuristic",
    )


@beartype
def heuristic_parse_purchase_stats(text: str) -> ParsedIntent | None:
    cleaned = _clean_text(text)
    lowered = cleaned.lower().strip(" ?!.")
    if not any(token in lowered for token in ("покупали", "берем", "берём", "заказывали", "брали")):
        return None
    if not any(token in lowered for token in ("чаще", "чаще всего", "какой", "что", "сравни", "сравнить", "у кого")):
        return None

    period = detect_relative_period(lowered) or "last_month"
    if "в этом месяце" in lowered or "за этот месяц" in lowered:
        period = "this_month"
    elif "90 дней" in lowered or "за 90" in lowered:
        period = "last_90_days"
    elif "за все время" in lowered or "за всё время" in lowered or "за всё" in lowered or "за все" in lowered:
        period = "all_time"

    query = lowered
    for phrase in (
        "мы чаще покупали",
        "чаще покупали",
        "мы чаще всего берем",
        "мы чаще всего берём",
        "чаще всего берем",
        "чаще всего берём",
        "мы чаще всего заказывали",
        "чаще всего заказывали",
        "мы чаще брали",
        "чаще брали",
        "берем",
        "берём",
        "заказывали",
        "брали",
        "в прошлом месяце",
        "в этом месяце",
        "за этот месяц",
        "за полгода",
        "за пол года",
        "за 6 месяцев",
        "за 6 месяца",
        "за последние 6 месяцев",
        "за 180 дней",
        "за последние 180 дней",
        "за 90 дней",
        "за 90",
        "за все время",
        "за всё время",
        "за всё",
        "за все",
        "и у какого поставщика",
        "у какого поставщика",
        "какой",
        "какие",
        "какая",
        "какого",
        "какую",
        "чаще",
        "всего",
        "мы",
        "что",
        "сравни",
        "сравнить",
    ):
        query = query.replace(phrase, " ")
    query = strip_relative_period_phrases(query)
    query = re.sub(r"^(а|ну|и)\s+", " ", query, flags=re.IGNORECASE)
    query = re.sub(r"\s+", " ", query).strip(" ,.;:!?")
    if not query:
        return None
    return ParsedIntent(action="purchase_stats", query=query, period=period, confidence=0.96, note="heuristic")


@beartype
def heuristic_parse_chat(text: str) -> ParsedIntent | None:
    cleaned = _clean_text(text)
    lowered = cleaned.lower()
    if lowered in CHAT_EXACT:
        return ParsedIntent(action="chat", query=cleaned, confidence=0.9, note="heuristic")
    if "можно с тобой просто общаться" in lowered or "что ты умеешь" in lowered:
        return ParsedIntent(action="chat", query=cleaned, confidence=0.9, note="heuristic")
    return None


@beartype
def looks_like_write_command(text: str) -> bool:
    lowered = _clean_text(text).lower()
    return any(
        hint in lowered
        for hint in (
            *INVENTORY_PREFIXES,
            *ADD_HINTS,
            *SUBTRACT_HINTS,
            *DELETE_HINTS,
            *CLEAR_HINTS,
            *RESTORE_HINTS,
        )
    )


class IntentParser:
    @beartype
    def __init__(self, api_key: str, model: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model

    @beartype
    def transcribe_voice(self, path: Path) -> str:
        mime_type = mimetypes.guess_type(path.name)[0] or "audio/ogg"
        audio_bytes = path.read_bytes()
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                "Transcribe this Russian voice message verbatim. Return only the transcript text.",
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            ],
        )
        return (response.text or "").strip()

    @beartype
    def _parse_json(self, prompt: str) -> dict[str, Any]:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"),
        )
        raw = (response.text or "").strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Bad parse payload: {raw}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Bad parse payload: {raw}")
        return payload

    @beartype
    def parse(self, text: str) -> ParsedIntent:
        for parser in (
            heuristic_parse_inventory_clear,
            heuristic_parse_inventory_command,
            heuristic_parse_inventory_delete,
            heuristic_parse_inventory_restore,
            heuristic_parse_inventory_show,
            heuristic_parse_compare_periods,
            heuristic_parse_compare_suppliers,
            heuristic_parse_purchase_stats,
            heuristic_parse_resolution_query,
            heuristic_parse_chat,
        ):
            parsed = parser(text)
            if parsed is not None:
                parsed.period = normalize_period_value(parsed.period)
                return parsed

        prompt = f"""
Parse this Russian pharmacy-assistant message into JSON.

Allowed actions:
- set_inventory
- add_inventory
- subtract_inventory
- delete_inventory
- restore_inventory
- show_inventory
- compare_suppliers
- compare_periods
- resolve_product
- purchase_stats
- chat
- unknown

Return JSON only with:
- action
- query
- qty
- period
- compare_period
- confidence
- note

Rules:
- set_inventory: user clearly wants to set an exact stock number
- add_inventory: user wants to add/increase stock by N
- subtract_inventory: user wants to subtract/decrease stock by N
- delete_inventory: user wants to remove item from inventory entirely
- restore_inventory: user wants to restore the last deleted inventory position
- show_inventory: user wants current inventory qty for a product
- compare_suppliers: user wants supplier comparison for one product over a period
- compare_periods: user wants the same product compared across two periods
- resolve_product: user asks which exact product is usually meant
- purchase_stats: user asks what was bought more often and/or from which supplier
- chat: greeting, capability question, or general talk
- period may be:
  - last_month
  - this_month
  - last_90_days
  - last_180_days
  - all_time
  - or dynamic like last_17_days / last_240_days
- never substitute one drug for another
- if unsure, return unknown

Message:
{text}
""".strip()
        payload = self._parse_json(prompt)
        try:
            parsed = ParsedIntent.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f"Bad parse payload: {payload!r}") from exc
        parsed.action = parsed.action.strip().lower() or "unknown"
        parsed.query = parsed.query.strip()
        parsed.period = normalize_period_value(parsed.period)
        parsed.compare_period = normalize_period_value(parsed.compare_period) if parsed.compare_period else None
        parsed.note = (parsed.note or "").strip()
        if parsed.action in {"set_inventory", "add_inventory", "subtract_inventory", "delete_inventory", "restore_inventory"}:
            if not looks_like_write_command(text):
                parsed.action = "unknown"
                parsed.query = ""
                parsed.qty = None
                parsed.note = f"{parsed.note}; downgraded_non_write".strip("; ")
        return parsed

    @beartype
    def plan_readonly(self, message: str, context: str = "") -> ParsedIntent:
        prompt = f"""
Route this Russian PharmOrder message into exactly one read-only action.

Allowed actions:
- purchase_stats
- compare_suppliers
- compare_periods
- resolve_product
- show_inventory
- chat
- unknown

Return JSON only with:
- action
- query
- period
- compare_period
- confidence
- note

Rules:
- If user asks what they usually buy or what they bought more often -> purchase_stats
- If user asks to compare suppliers for a product -> compare_suppliers
- If user asks to compare one period with another for a product -> compare_periods
- If user asks which exact product they usually mean -> resolve_product
- If user asks about current stock / inventory -> show_inventory
- If this is greeting, small talk, or capability question -> chat
- period may be:
  - last_month
  - this_month
  - last_90_days
  - last_180_days
  - all_time
  - or dynamic like last_17_days / last_540_days
- If the message implies a relative period, extract it
- If no period is mentioned for analytics, default to the chat context period if present, otherwise last_month
- Never invent a different drug than the one user likely means
- Keep query short and searchable

Chat context:
{context or "нет"}

Message:
{message}
""".strip()
        payload = self._parse_json(prompt)
        payload.setdefault("qty", None)
        try:
            parsed = ParsedIntent.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f"Bad readonly plan payload: {payload!r}") from exc
        parsed.action = parsed.action.strip().lower() or "unknown"
        parsed.query = parsed.query.strip()
        parsed.period = normalize_period_value(parsed.period)
        parsed.compare_period = normalize_period_value(parsed.compare_period) if parsed.compare_period else None
        parsed.note = (parsed.note or "").strip()
        return parsed

    @beartype
    def render_grounded_reply(
        self,
        *,
        user_message: str,
        context: str,
        tool_name: str,
        tool_payload: dict[str, Any],
    ) -> str:
        prompt = f"""
Ты приватный assistant для PharmOrder.
Собери короткий естественный ответ по-русски на основе результата инструмента.

Правила:
- не используй markdown
- не используй **, `, #, таблицы
- не выдумывай факты вне tool payload
- если инструмент ничего не нашёл, скажи это прямо и коротко
- если есть список вариантов, можно дать топ-3
- если пользователь просил аналитику, ответ должен звучать как нормальный живой помощник, а не как роутер команд
- не предлагай write-операции сам, если пользователь об этом не просил

Контекст:
{context or "нет"}

Сообщение пользователя:
{user_message}

Имя инструмента:
{tool_name}

Результат инструмента JSON:
{json.dumps(tool_payload, ensure_ascii=False)}
""".strip()
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.35),
        )
        return _strip_markdown(response.text or "")

    @beartype
    def chat_reply(self, message: str, context: str = "") -> str:
        prompt = f"""
Ты приватный помощник для PharmOrder.
Отвечай по-русски, коротко, по делу, без markdown-разметки.
Ты умеешь:
- помочь понять, какой товар обычно имеется в виду
- сказать, что чаще покупали в истории закупок
- посмотреть текущий остаток
- подготовить смену остатка через confirm

Контекст:
{context or "нет"}

Сообщение:
{message}
""".strip()
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.4),
        )
        return _strip_markdown(response.text or "")
