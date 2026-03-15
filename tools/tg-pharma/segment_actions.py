from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from beartype import beartype
from google import genai
from google.genai import types

VOICE_DRAFT_DIR = Path(__file__).resolve().parent / "voice_draft_state"
VOICE_DRAFT_DIR.mkdir(exist_ok=True)

_EXTRACT_SYSTEM = (
    "Ты ассистент аптеки. Из транскрипции голосового сообщения извлеки "
    "ВСЕ команды управления остатками. Игнорируй вопросы и разговор.\n\n"
    "Поддерживаемые операции:\n"
    "- inventory_set: «поставь X = N», «установи X N», «X будет N штук»\n"
    "- inventory_add: «добавь N X», «пришло N X», «поставили N X»\n"
    "- inventory_subtract: «убрать N X», «продал N X», «вычти N»\n"
    "- inventory_delete: «удали X», «убери X из остатков», «X нет в аптеке»\n\n"
    "qty = 0 для delete.\n\n"
    "Нормализуй query до короткой поисковой фразы, без мата и разговорного мусора.\n"
    "Если в речи есть дозировка словами, переводи её в цифры в query:\n"
    "- пятисотый/пятисотого -> 500\n"
    "- двухсотпятидесятый -> 250\n"
    "- стопятидесятый -> 150\n"
    "- стодвадцатипятый -> 125\n"
    "- тысячный -> 1000\n"
    "Если сказано обычный/не форте, не подставляй форте в query.\n\n"
    "Ответ — ТОЛЬКО JSON массив без комментариев:\n"
    '[\n  {"kind": "inventory_set", "raw": "оригинальная фраза", '
    '"query": "название товара", "qty": 10, "note": ""},\n  ...\n]\n\n'
    "Если команд нет — верни []."
)

_VALID_KINDS = frozenset(
    ("inventory_set", "inventory_add", "inventory_subtract", "inventory_delete")
)
_SET_MARKERS = ("поставь", "установи", "сделай", "остаток", "будет", "пусть будет")
_ADD_MARKERS = ("добавь", "добавить", "в остатки", "брось", "закинь", "кинь", "докинь", "накинь", "домаркируй")
_SUBTRACT_MARKERS = ("убавь", "убрать", "уменьши", "спиши", "вычти")
_DELETE_MARKERS = ("удали", "удалить", "убери совсем", "убери позицию", "снеси")


@dataclass(slots=True)
class ExtractedAction:
    kind: str   # inventory_set / inventory_add / inventory_subtract / inventory_delete
    raw: str    # оригинальная фраза
    query: str  # запрос для поиска товара
    qty: int    # количество (0 для delete)
    note: str = ""


@dataclass(slots=True)
class VoiceDraft:
    chat_id: int
    created_at: float
    transcript: str
    message_id: int | None = None          # TG message_id статусного сообщения
    resolved: list[dict[str, Any]] = field(default_factory=list)
    # [{"action": {...}, "ean": "...", "name": "...", "maker": "..."}]
    ambiguous: list[dict[str, Any]] = field(default_factory=list)
    # [{"action": {...}, "candidates": [{"ean":..., "name":..., "maker":..., "score":...}]}]
    not_found: list[dict[str, Any]] = field(default_factory=list)
    # [{"kind":..., "raw":..., "query":..., "qty":..., "note":...}]
    apply_status: str = "pending"  # pending / partial / done
    apply_log: list[str] = field(default_factory=list)


@beartype
def _normalize_action_kind(kind: str, raw: str, query: str, qty: int) -> str:
    lowered = f"{raw} {query}".lower().strip()
    if any(marker in lowered for marker in _DELETE_MARKERS):
        return "inventory_delete"
    if any(marker in lowered for marker in _SUBTRACT_MARKERS):
        return "inventory_subtract"
    if any(marker in lowered for marker in _ADD_MARKERS):
        return "inventory_add"
    if kind == "inventory_set":
        if qty == 0:
            return "inventory_set"
        if any(marker in lowered for marker in _SET_MARKERS):
            return "inventory_set"
        # В голосовых диктовках "товар + количество" почти всегда значит add, а не set.
        return "inventory_add"
    return kind


@beartype
def _normalize_action_payload(payload: dict[str, Any]) -> dict[str, Any]:
    fixed = dict(payload)
    kind = str(fixed.get("kind", "")).strip()
    raw = str(fixed.get("raw", "")).strip()
    query = str(fixed.get("query", "")).strip()
    qty = int(fixed.get("qty", 0) or 0)
    fixed["kind"] = _normalize_action_kind(kind, raw, query, qty)
    fixed["qty"] = qty
    return fixed


@beartype
def save_draft(draft: VoiceDraft) -> None:
    """Atomic write — write to temp file then replace to avoid corrupt drafts."""
    path = VOICE_DRAFT_DIR / f"{draft.chat_id}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(asdict(draft), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tmp.replace(path)


@beartype
def load_draft(chat_id: int) -> VoiceDraft | None:
    path = VOICE_DRAFT_DIR / f"{chat_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text("utf-8"))
    for entry in data.get("resolved", []) or []:
        action = entry.get("action")
        if isinstance(action, dict):
            entry["action"] = _normalize_action_payload(action)
    for entry in data.get("ambiguous", []) or []:
        action = entry.get("action")
        if isinstance(action, dict):
            entry["action"] = _normalize_action_payload(action)
    for idx, entry in enumerate(data.get("not_found", []) or []):
        if isinstance(entry, dict):
            data["not_found"][idx] = _normalize_action_payload(entry)
    return VoiceDraft(**data)


@beartype
def clear_draft(chat_id: int) -> None:
    path = VOICE_DRAFT_DIR / f"{chat_id}.json"
    path.unlink(missing_ok=True)


@beartype
def extract_actions(transcript: str, api_key: str, model: str) -> list[ExtractedAction]:
    """Call Gemini to extract inventory actions from transcript text."""
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=f"Транскрипция:\n{transcript}",
        config=types.GenerateContentConfig(
            system_instruction=_EXTRACT_SYSTEM,
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )
    text = (response.text or "").strip()
    # Strip markdown code fence if Gemini added one
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1].removeprefix("json").strip() if len(parts) > 1 else text
    try:
        raw_list: list[dict[str, Any]] = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return []
    result: list[ExtractedAction] = []
    for item in raw_list:
        kind = str(item.get("kind", ""))
        if kind not in _VALID_KINDS:
            continue
        query = str(item.get("query", "")).strip()
        if not query:
            continue
        raw = str(item.get("raw", ""))
        qty = int(item.get("qty", 0) or 0)
        kind = _normalize_action_kind(kind, raw, query, qty)
        result.append(
            ExtractedAction(
                kind=kind,
                raw=raw,
                query=query,
                qty=qty,
                note=str(item.get("note", "")),
            )
        )
    return result


_ADDITIVE = frozenset(("inventory_add", "inventory_subtract"))
_ABSOLUTE = frozenset(("inventory_set", "inventory_delete"))


def _merge_actions(actions: list[ExtractedAction]) -> list[ExtractedAction]:
    """Merge multiple actions for the same query key.

    Rules:
    - set / delete → last-wins (абсолютные операции, предыдущие неважны)
    - add / subtract → aggregate: суммируем qty со знаком (+add, -subtract)
    - mixed absolute + additive on same product → keep last absolute as-is,
      additive actions before it are discarded (absolute "сбрасывает" историю)
    - mixed add+subtract on same product → net delta, kind = add if positive, subtract if negative
    - conflicting absolutes (set then delete) → last-wins
    """
    # Group by normalized query
    groups: dict[str, list[ExtractedAction]] = {}
    for a in actions:
        key = a.query.lower().strip()
        if key:
            groups.setdefault(key, []).append(a)

    result: list[ExtractedAction] = []
    for key, group in groups.items():
        if len(group) == 1:
            result.append(group[0])
            continue

        kinds = {a.kind for a in group}
        has_absolute = bool(kinds & _ABSOLUTE)
        has_additive = bool(kinds & _ADDITIVE)

        if has_absolute and has_additive:
            # Mixed: find last absolute, discard everything before it
            last_abs_idx = max(i for i, a in enumerate(group) if a.kind in _ABSOLUTE)
            result.append(group[last_abs_idx])
            continue

        if has_absolute:
            # Only absolutes — last-wins
            result.append(group[-1])
            continue

        # Only additives — aggregate net delta
        net = 0
        for a in group:
            net += a.qty if a.kind == "inventory_add" else -a.qty
        ref = group[-1]
        if net == 0:
            # Net zero — skip (добавили и убрали одно и то же)
            continue
        merged_kind = "inventory_add" if net > 0 else "inventory_subtract"
        raws = " + ".join(a.raw for a in group)
        result.append(
            ExtractedAction(kind=merged_kind, raw=raws, query=ref.query, qty=abs(net))
        )

    return result


@beartype
def resolve_actions(
    actions: list[ExtractedAction],
    resolve_fn: Callable[..., Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Resolve actions against product catalog (duck-typed RankedCandidate via resolve_fn).

    resolve_fn(query: str) -> list[RankedCandidate]  (accessed as .candidate.ean etc.)

    Merge rules (applied before catalog resolve):
      set/delete  → last-wins
      add/subtract → aggregate net delta
      mixed absolute+additive → last absolute wins, additives before it discarded

    Returns (resolved, ambiguous, not_found):
      resolved:  [{"action": {...}, "ean": ..., "name": ..., "maker": ...}]
      ambiguous: [{"action": {...}, "candidates": [...]}]
      not_found: [{"kind":..., "raw":..., "query":..., "qty":..., "note":...}]
    """
    merged = _merge_actions(actions)

    resolved: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    not_found: list[dict[str, Any]] = []

    for action in merged:
        candidates = resolve_fn(action.query)
        if not candidates:
            not_found.append(asdict(action))
            continue
        top = candidates[0]
        score: float = float(getattr(top, "score", 0.0))
        if len(candidates) == 1 or score >= 2.0:
            resolved.append(
                {
                    "action": asdict(action),
                    "ean": top.candidate.ean,
                    "name": top.candidate.name,
                    "maker": top.candidate.maker,
                }
            )
        else:
            ambiguous.append(
                {
                    "action": asdict(action),
                    "candidates": [
                        {
                            "ean": c.candidate.ean,
                            "name": c.candidate.name,
                            "maker": c.candidate.maker,
                            "score": float(c.score),
                        }
                        for c in candidates[:3]
                    ],
                }
            )

    return resolved, ambiguous, not_found
