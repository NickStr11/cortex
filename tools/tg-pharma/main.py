from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from beartype import beartype

from history_client import (
    BotRefsClient,
    CatalogProduct,
    HistoryAnalyticsClient,
    HistoryProductSummary,
    LocalAnalyticsClient,
    SupplierBreakdown,
    make_identity_key,
)
from intent import IntentParser, ParsedIntent
from pharm_api import InventoryItem, PharmOrderAPI, PharmOrderError, ProductCandidate

ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_ENV = ROOT_DIR / ".env"
LOCAL_ENV = SCRIPT_DIR / ".env"
AUDIT_LOG = SCRIPT_DIR / "audit.jsonl"
CHAT_STATE_FILE = SCRIPT_DIR / "chat_state.json"
BOT_BUILD = "2026-03-11-agent-readonly-1"
PENDING_TTL_SECONDS = int(os.environ.get("PHARMA_PENDING_TTL_SECONDS", "900"))
PENDING_CLEANUP_INTERVAL_SECONDS = int(os.environ.get("PHARMA_PENDING_CLEANUP_INTERVAL_SECONDS", "60"))


@beartype
def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text("utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


load_env_file(ROOT_ENV)
load_env_file(LOCAL_ENV)

BOT_TOKEN = os.environ.get("PHARMA_TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
API_BASE = os.environ.get("PHARMORDER_API_BASE", "http://194.87.140.204:8000").strip()
API_KEY = os.environ.get("PHARMORDER_API_KEY", "").strip()
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("PHARMA_GEMINI_MODEL", "gemini-3-flash-preview").strip()
SSH_HOST = os.environ.get("PHARMORDER_SSH_HOST", "").strip()
SSH_USER = os.environ.get("PHARMORDER_SSH_USER", "").strip()
SSH_PASSWORD = os.environ.get("PHARMORDER_SSH_PASSWORD", "")
SSH_ORDER_DB = os.environ.get("PHARMORDER_REMOTE_ORDER_HISTORY_DB", "/opt/pharmorder/src/data/order_history.db").strip()
REFS_DB = os.environ.get("PHARMA_REFS_DB", str(SCRIPT_DIR / "data" / "bot_refs.db")).strip()
LOCAL_ANALYTICS_DB = os.environ.get("PHARMA_ANALYTICS_DB", str(SCRIPT_DIR / "data" / "bot_analytics.db")).strip()

ALLOWED_CHAT_IDS = {
    int(chunk.strip())
    for chunk in os.environ.get("PHARMA_ALLOWED_CHAT_IDS", "691773226").split(",")
    if chunk.strip()
}

API = PharmOrderAPI(API_BASE, API_KEY)
PARSER = IntentParser(GEMINI_API_KEY, GEMINI_MODEL)
HISTORY = HistoryAnalyticsClient(
    host=SSH_HOST,
    username=SSH_USER,
    password=SSH_PASSWORD,
    db_path=SSH_ORDER_DB,
)
REFS = BotRefsClient(db_path=REFS_DB)
LOCAL_ANALYTICS = LocalAnalyticsClient(db_path=LOCAL_ANALYTICS_DB)


@dataclass(slots=True)
class RankedCandidate:
    candidate: ProductCandidate
    score: float
    inventory_qty: int | None = None
    month_qty: float = 0.0
    month_count: int = 0
    all_time_qty: float = 0.0
    all_time_count: int = 0
    top_supplier: str = ""
    last_date: str = ""
    offer_count: int = 0
    best_priority: int = 999


@dataclass(slots=True)
class PendingAction:
    token: str
    chat_id: int
    source_text: str
    operation: str
    query: str
    qty: int
    ranked: list[RankedCandidate]
    selected_index: int = 0
    created_at: float = field(default_factory=time.time)

    @property
    def selected(self) -> RankedCandidate:
        return self.ranked[self.selected_index]


@dataclass(slots=True)
class ChatState:
    last_product_focus: str = ""
    last_period: str = "last_month"
    last_action: str = ""
    recent_queries: list[str] = field(default_factory=list)
    recent_turns: list[str] = field(default_factory=list)
    recent_candidates: list[dict[str, str]] = field(default_factory=list)
    last_deleted: dict[str, Any] | None = None


PENDING_LOCK = threading.Lock()
PENDING: dict[str, PendingAction] = {}
CHAT_STATE_LOCK = threading.Lock()
CHAT_STATE: dict[int, ChatState] = {}


@beartype
def load_chat_states() -> dict[int, ChatState]:
    if not CHAT_STATE_FILE.exists():
        return {}
    try:
        raw = json.loads(CHAT_STATE_FILE.read_text("utf-8"))
    except Exception:
        return {}
    loaded: dict[int, ChatState] = {}
    if not isinstance(raw, dict):
        return loaded
    for key, value in raw.items():
        try:
            chat_id = int(key)
        except Exception:
            continue
        if not isinstance(value, dict):
            continue
        loaded[chat_id] = ChatState(
            last_product_focus=str(value.get("last_product_focus", "")).strip(),
            last_period=str(value.get("last_period", "last_month") or "last_month").strip(),
            last_action=str(value.get("last_action", "")).strip(),
            recent_queries=[str(item).strip() for item in value.get("recent_queries", []) if str(item).strip()],
            recent_turns=[str(item).strip() for item in value.get("recent_turns", []) if str(item).strip()],
            recent_candidates=[
                {
                    "ean": str(item.get("ean", "")).strip(),
                    "name": str(item.get("name", "")).strip(),
                    "maker": str(item.get("maker", "")).strip(),
                }
                for item in value.get("recent_candidates", [])
                if isinstance(item, dict)
            ],
            last_deleted=(
                {
                    "ean": str(value.get("last_deleted", {}).get("ean", "")).strip(),
                    "name": str(value.get("last_deleted", {}).get("name", "")).strip(),
                    "maker": str(value.get("last_deleted", {}).get("maker", "")).strip(),
                    "qty": int(value.get("last_deleted", {}).get("qty", 0) or 0),
                }
                if isinstance(value.get("last_deleted"), dict)
                else None
            ),
        )
    return loaded


def save_chat_states_locked() -> None:
    payload = {
        str(chat_id): {
            "last_product_focus": state.last_product_focus,
            "last_period": state.last_period,
            "last_action": state.last_action,
            "recent_queries": state.recent_queries[-10:],
            "recent_turns": state.recent_turns[-20:],
            "recent_candidates": state.recent_candidates[-8:],
            "last_deleted": state.last_deleted,
        }
        for chat_id, state in CHAT_STATE.items()
    }
    CHAT_STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


CHAT_STATE.update(load_chat_states())


@beartype
def sanitize_outgoing_text(text: str) -> str:
    cleaned = text.replace("**", "")
    cleaned = cleaned.replace("__", "")
    cleaned = cleaned.replace("`", "")
    cleaned = cleaned.replace("last_180_days", "за полгода")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


@beartype
def friendly_period_label(period: str) -> str:
    named = {
        "last_month": "в прошлом месяце",
        "this_month": "в этом месяце",
        "last_90_days": "за 90 дней",
        "last_180_days": "за полгода",
        "all_time": "за всё время",
    }
    if period in named:
        return named[period]
    match = re.fullmatch(r"last_(\\d+)_days", period or "")
    if match:
        return f"за {int(match.group(1))} дней"
    return period


@beartype
def chat_context_summary(state: ChatState) -> str:
    focus = state.last_product_focus or "нет"
    period = friendly_period_label(state.last_period or "last_month")
    return f"Последний фокус: {focus}; последний период: {period}."


@beartype
def serialize_ranked_item(item: RankedCandidate) -> dict[str, Any]:
    return {
        "ean": item.candidate.ean,
        "name": item.candidate.name,
        "maker": item.candidate.maker,
        "inventory_qty": item.inventory_qty,
        "month_qty": item.month_qty,
        "month_count": item.month_count,
        "all_time_qty": item.all_time_qty,
        "all_time_count": item.all_time_count,
        "top_supplier": item.top_supplier,
        "last_date": item.last_date,
        "offer_count": item.offer_count,
        "score": round(item.score, 2),
    }


@beartype
def grounded_readonly_reply(
    *,
    user_message: str,
    state: ChatState,
    tool_name: str,
    tool_payload: dict[str, Any],
    fallback_text: str,
) -> str:
    try:
        reply = PARSER.render_grounded_reply(
            user_message=user_message,
            context=chat_context_summary(state),
            tool_name=tool_name,
            tool_payload=tool_payload,
        )
    except Exception:
        reply = ""
    return reply.strip() or fallback_text


@beartype
def api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"


@beartype
def send_message(client: httpx.Client, chat_id: int, text: str, buttons: list[list[dict[str, str]]] | None = None) -> None:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": sanitize_outgoing_text(text)}
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    client.post(api_url("sendMessage"), json=payload, timeout=30).raise_for_status()


@beartype
def edit_message(
    client: httpx.Client,
    chat_id: int,
    message_id: int,
    text: str,
    buttons: list[list[dict[str, str]]] | None = None,
) -> None:
    payload: dict[str, Any] = {"chat_id": chat_id, "message_id": message_id, "text": sanitize_outgoing_text(text)}
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    client.post(api_url("editMessageText"), json=payload, timeout=30).raise_for_status()


@beartype
def answer_callback(client: httpx.Client, callback_id: str, text: str = "") -> None:
    payload: dict[str, Any] = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
        payload["show_alert"] = False
    client.post(api_url("answerCallbackQuery"), json=payload, timeout=30).raise_for_status()


@beartype
def audit(event: dict[str, Any]) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"ts": time.time(), **event}, ensure_ascii=False) + "\n")


@beartype
def is_pending_expired(action: PendingAction, now: float | None = None) -> bool:
    check_at = now if now is not None else time.time()
    return (check_at - action.created_at) > PENDING_TTL_SECONDS


@beartype
def cleanup_pending_locked(now: float | None = None) -> int:
    check_at = now if now is not None else time.time()
    expired_tokens = [token for token, action in PENDING.items() if is_pending_expired(action, check_at)]
    for token in expired_tokens:
        PENDING.pop(token, None)
    return len(expired_tokens)


@beartype
def put_pending(action: PendingAction) -> None:
    with PENDING_LOCK:
        cleanup_pending_locked()
        PENDING[action.token] = action


@beartype
def get_pending(token: str) -> PendingAction | None:
    with PENDING_LOCK:
        cleanup_pending_locked()
        action = PENDING.get(token)
        if action and is_pending_expired(action):
            PENDING.pop(token, None)
            return None
        return action


@beartype
def pop_pending(token: str) -> PendingAction | None:
    with PENDING_LOCK:
        cleanup_pending_locked()
        action = PENDING.pop(token, None)
        if action and is_pending_expired(action):
            return None
        return action


@beartype
def delete_pending(token: str) -> None:
    with PENDING_LOCK:
        cleanup_pending_locked()
        PENDING.pop(token, None)


@beartype
def make_token() -> str:
    return uuid.uuid4().hex


@beartype
def get_chat_state(chat_id: int) -> ChatState:
    with CHAT_STATE_LOCK:
        return CHAT_STATE.setdefault(chat_id, ChatState())


@beartype
def update_chat_focus(chat_id: int, query: str, period: str = "last_month") -> None:
    state = get_chat_state(chat_id)
    with CHAT_STATE_LOCK:
        state.last_product_focus = query.strip()
        state.last_period = period or "last_month"
        if query.strip():
            state.recent_queries.append(query.strip())
            state.recent_queries = state.recent_queries[-10:]
        save_chat_states_locked()


@beartype
def remember_chat_turn(chat_id: int, action: str, source_text: str) -> None:
    state = get_chat_state(chat_id)
    with CHAT_STATE_LOCK:
        state.last_action = action.strip()
        if source_text.strip():
            state.recent_turns.append(source_text.strip())
            state.recent_turns = state.recent_turns[-20:]
        save_chat_states_locked()


@beartype
def remember_candidates(chat_id: int, ranked: list[RankedCandidate]) -> None:
    if not ranked:
        return
    state = get_chat_state(chat_id)
    with CHAT_STATE_LOCK:
        state.recent_candidates = [
            {
                "ean": item.candidate.ean,
                "name": item.candidate.name,
                "maker": item.candidate.maker,
            }
            for item in ranked[:8]
        ]
        save_chat_states_locked()


@beartype
def get_last_deleted_snapshot(chat_id: int) -> dict[str, Any] | None:
    state = get_chat_state(chat_id)
    snapshot = state.last_deleted or None
    if not isinstance(snapshot, dict):
        return None
    ean = str(snapshot.get("ean", "")).strip()
    name = str(snapshot.get("name", "")).strip()
    if not ean or not name:
        return None
    return {
        "ean": ean,
        "name": name,
        "maker": str(snapshot.get("maker", "")).strip(),
        "qty": int(snapshot.get("qty", 0) or 0),
    }


@beartype
def remember_last_deleted(chat_id: int, item: RankedCandidate) -> None:
    state = get_chat_state(chat_id)
    with CHAT_STATE_LOCK:
        state.last_deleted = {
            "ean": item.candidate.ean,
            "name": item.candidate.name,
            "maker": item.candidate.maker,
            "qty": int(item.inventory_qty if item.inventory_qty is not None else 0),
        }
        save_chat_states_locked()


@beartype
def build_deleted_candidate(chat_id: int) -> RankedCandidate | None:
    snapshot = get_last_deleted_snapshot(chat_id)
    if not snapshot:
        return None
    return RankedCandidate(
        candidate=ProductCandidate(
            ean=snapshot["ean"],
            name=snapshot["name"],
            maker=snapshot["maker"],
            id_name=None,
        ),
        score=0.0,
        inventory_qty=0,
        month_qty=0.0,
        month_count=0,
        all_time_qty=0.0,
        all_time_count=0,
        top_supplier="",
        last_date="",
        offer_count=0,
        best_priority=999,
    )


@beartype
def short_period_label(period: str) -> str:
    return {
        "last_month": "в прошлом месяце",
        "this_month": "в этом месяце",
        "last_90_days": "за 90 дней",
        "all_time": "за всё время",
    }.get(period, period)


@beartype
def chat_reply_context() -> str:
    return (
        "Ты приватный помощник PharmOrder. Помогаешь по товарам, истории закупок и остаткам. "
        "Если пользователь просто болтает или спрашивает, что ты умеешь, отвечай коротко и без навязчивого упоминания "
        "последнего товара или прошлого фокуса чата."
    )


@beartype
def product_line(candidate: ProductCandidate) -> str:
    maker = f" | {candidate.maker}" if candidate.maker else ""
    return f"{candidate.name}{maker}"


@beartype
def normalize_alias_token(value: str) -> str:
    normalized = value.lower().replace("ё", "е")
    normalized = re.sub(r"[^а-яa-z0-9]+", "", normalized)
    for suffix in (
        "овского",
        "евского",
        "ского",
        "ового",
        "евого",
        "ского",
        "овский",
        "евский",
        "ского",
        "овск",
        "евск",
        "ового",
        "евого",
        "ового",
        "ого",
        "его",
        "ому",
        "ему",
        "ыми",
        "ими",
        "ым",
        "им",
        "ая",
        "яя",
        "ый",
        "ий",
        "ой",
        "ого",
        "его",
    ):
        if normalized.endswith(suffix) and len(normalized) - len(suffix) >= 4:
            return normalized[: -len(suffix)]
    return normalized


@beartype
def candidate_aliases(name: str, maker: str) -> set[str]:
    source = f"{name} {maker}"
    aliases: set[str] = set()
    for token in re.findall(r"[а-яёa-z0-9]+", source.lower()):
        normalized = normalize_alias_token(token)
        if len(normalized) >= 4:
            aliases.add(normalized)
    for chunk in re.findall(r"\(([^)]+)\)", maker.lower()):
        normalized = normalize_alias_token(chunk)
        if len(normalized) >= 4:
            aliases.add(normalized)
    return aliases


FOLLOWUP_STOPWORDS = {
    "а",
    "ну",
    "штук",
    "штука",
    "штуки",
    "какой",
    "какая",
    "какое",
    "какие",
    "какого",
    "какую",
    "каком",
    "каком-то",
    "какого-то",
    "производитель",
    "производителя",
    "производителем",
    "поставщик",
    "поставщика",
    "поставщике",
    "брали",
    "берем",
    "берём",
    "берете",
    "берёте",
    "чаще",
    "всего",
    "мы",
    "у",
    "нас",
    "по",
    "и",
    "в",
    "прошлом",
    "месяце",
    "этом",
}

CONTEXT_QUERY_MARKERS = (
    "эту позицию",
    "этой позиции",
    "эту",
    "этой",
    "этот товар",
    "этот препарат",
    "эту позицию",
    "эту штуку",
)


@beartype
def refine_query_with_context(chat_id: int, action: str, query: str) -> str:
    if action not in {"purchase_stats", "resolve_product", "set_inventory", "add_inventory", "subtract_inventory", "delete_inventory", "show_inventory"}:
        return query
    state = get_chat_state(chat_id)
    focus = state.last_product_focus.strip()
    lowered_query = query.lower().strip()
    if focus and any(marker in lowered_query for marker in CONTEXT_QUERY_MARKERS):
        return focus
    candidate_matches: list[dict[str, str]] = []

    tokens = re.findall(r"[а-яёa-z]+|\d+(?:[.,]\d+)?", query.lower())
    if not tokens:
        return query

    meaningful_alpha = [token for token in tokens if re.search(r"[а-яёa-z]", token) and token not in FOLLOWUP_STOPWORDS]
    numeric_tokens = [token for token in tokens if re.fullmatch(r"\d+(?:[.,]\d+)?", token)]
    normalized_alpha = [normalize_alias_token(token) for token in meaningful_alpha if normalize_alias_token(token)]

    if normalized_alpha and not state.recent_candidates and state.recent_queries:
        for recent_query in reversed(state.recent_queries):
            recent_query = recent_query.strip()
            if not recent_query or recent_query.casefold() == query.casefold():
                continue
            fallback_ranked = build_ranked_candidates(recent_query)
            if fallback_ranked:
                remember_candidates(chat_id, fallback_ranked)
                if state.last_product_focus.strip().casefold() == query.casefold():
                    update_chat_focus(chat_id, recent_query, state.last_period or "last_month")
                state = get_chat_state(chat_id)
                break

    if normalized_alpha and state.recent_candidates:
        for candidate in state.recent_candidates:
            aliases = candidate_aliases(candidate.get("name", ""), candidate.get("maker", ""))
            if any(any(alias in token or token in alias for alias in aliases) for token in normalized_alpha):
                candidate_matches.append(candidate)
        if len(candidate_matches) > 1 and numeric_tokens:
            filtered = [
                candidate
                for candidate in candidate_matches
                if name_matches_dose_hints(candidate.get("name", ""), " ".join(numeric_tokens))
            ]
            if filtered:
                candidate_matches = filtered
        if candidate_matches:
            suffix = " ".join(numeric_tokens).strip() if dose_hints_for_query(" ".join(numeric_tokens)) else ""
            base = candidate_matches[0].get("name", "").strip()
            combined = base if not suffix else f"{base} {suffix}"
            return " ".join(combined.split())

    if not focus:
        return query

    focus_words = {token for token in re.findall(r"[а-яёa-z]+", focus.lower()) if token}
    if meaningful_alpha and meaningful_alpha[0] not in focus_words and not candidate_matches:
        return query
    if focus_words & set(meaningful_alpha):
        return query
    if not meaningful_alpha and not numeric_tokens:
        return query

    carry_numbers = numeric_tokens if dose_hints_for_query(" ".join(numeric_tokens)) else []
    suffix = " ".join([*meaningful_alpha, *carry_numbers]).strip()
    combined = focus if not suffix else f"{focus} {suffix}"
    return " ".join(combined.split())


@beartype
def dose_hints_for_query(query: str) -> list[str]:
    lowered = query.lower()
    hints: list[str] = []

    def push(value: str) -> None:
        if value not in hints:
            hints.append(value)

    numeric_tokens = re.findall(r"\d+(?:[.,]\d+)?", lowered)
    if any(token in {"500", "0.5", "0,5"} for token in numeric_tokens):
        push("0.5")
        push("0,5")
        push("500мг")
    if any(token in {"250", "0.25", "0,25"} for token in numeric_tokens):
        push("0.25")
        push("0,25")
        push("250мг")
    if any(token in {"125", "0.125", "0,125"} for token in numeric_tokens):
        push("0.125")
        push("0,125")
        push("125мг")
    return hints


@beartype
def name_matches_dose_hints(name: str, query: str) -> bool:
    hints = dose_hints_for_query(query)
    if not hints:
        return True
    normalized = name.lower().replace(" ", "")
    return any(hint in normalized for hint in hints)


@beartype
def ranking_reasons(item: RankedCandidate) -> list[str]:
    reasons: list[str] = []
    if item.all_time_qty > 0:
        reasons.append(f"история: {int(item.all_time_qty)} шт, {item.all_time_count} закупок")
    if item.month_qty > 0:
        reasons.append(f"прошлый месяц: {int(item.month_qty)} шт")
    if item.top_supplier:
        reasons.append(f"обычно у {item.top_supplier}")
    if item.inventory_qty is not None:
        reasons.append(f"текущий остаток {item.inventory_qty}")
    return reasons


@beartype
def inventory_status_reply(item: RankedCandidate) -> str:
    lines = [
        "По inventory сейчас:",
        product_line(item.candidate),
        f"EAN: {item.candidate.ean}",
        f"Остаток: {item.inventory_qty if item.inventory_qty is not None else 0}",
    ]
    reasons = ranking_reasons(item)
    if reasons:
        lines.append("")
        lines.append("Контекст:")
        lines.extend(f"• {reason}" for reason in reasons[:4])
    return "\n".join(lines)


@beartype
def preview_text(action: PendingAction) -> str:
    item = action.selected
    op_title = {
        "set_inventory": f"Поставлю остаток: {action.qty}",
        "add_inventory": f"Добавлю в остаток: +{action.qty}",
        "subtract_inventory": f"Спишу из остатка: -{action.qty}",
        "delete_inventory": "Удалю позицию из inventory",
        "restore_inventory": f"Верну позицию в inventory: {action.qty}",
    }.get(action.operation, f"Изменю остаток: {action.qty}")
    lines = [
        op_title,
        product_line(item.candidate),
        f"EAN: {item.candidate.ean}",
        f"Сейчас в inventory: {item.inventory_qty if item.inventory_qty is not None else 0}",
    ]
    reasons = ranking_reasons(item)
    if reasons:
        lines.append("")
        lines.append("Почему выбрал:")
        lines.extend(f"• {reason}" for reason in reasons[:4])
    lines.append("")
    lines.append("Подтвердить?")
    return "\n".join(lines)


@beartype
def preview_buttons(token: str, allow_switch: bool) -> list[list[dict[str, str]]]:
    rows = [[{"text": "Подтвердить", "callback_data": f"apply:{token}"}]]
    if allow_switch:
        rows[0].append({"text": "Другой товар", "callback_data": f"choose:{token}"})
    rows.append([{"text": "Отмена", "callback_data": f"cancel:{token}"}])
    return rows


@beartype
def choice_buttons(token: str, action: PendingAction) -> list[list[dict[str, str]]]:
    rows: list[list[dict[str, str]]] = []
    for idx, item in enumerate(action.ranked[:5]):
        label = item.candidate.name[:50]
        rows.append([{"text": label, "callback_data": f"pick:{token}:{idx}"}])
    rows.append([{"text": "Отмена", "callback_data": f"cancel:{token}"}])
    return rows


@beartype
def resolve_candidate_identity(candidate: ProductCandidate) -> tuple[ProductCandidate, str]:
    identity = REFS.resolve_identity(
        ean=candidate.ean,
        id_name=candidate.id_name,
        name=candidate.name,
        maker=candidate.maker,
    )
    if identity:
        return (
            ProductCandidate(
                ean=candidate.ean,
                name=identity.name or candidate.name,
                maker=identity.maker or candidate.maker,
                id_name=identity.id_name if identity.id_name is not None else candidate.id_name,
            ),
            identity.key,
        )
    return candidate, make_identity_key(candidate.id_name, candidate.name, candidate.maker)


@beartype
def summary_identity_map(items: list[HistoryProductSummary]) -> dict[str, HistoryProductSummary]:
    mapped: dict[str, HistoryProductSummary] = {}
    for item in items:
        identity = REFS.resolve_identity(ean=item.ean, name=item.name, maker=item.maker)
        key = identity.key if identity else make_identity_key(None, item.name, item.maker)
        mapped[key] = item
    return mapped


@beartype
def choose_better_candidate(
    current: tuple[ProductCandidate, CatalogProduct | None],
    incoming: tuple[ProductCandidate, CatalogProduct | None],
) -> tuple[ProductCandidate, CatalogProduct | None]:
    current_candidate, current_catalog = current
    incoming_candidate, incoming_catalog = incoming

    def score(candidate: ProductCandidate, catalog: CatalogProduct | None) -> tuple[int, int, int, int, int]:
        return (
            1 if catalog else 0,
            -(catalog.best_priority if catalog else 999),
            catalog.offer_count if catalog else 0,
            1 if candidate.id_name is not None else 0,
            len(candidate.maker or ""),
        )

    return incoming if score(incoming_candidate, incoming_catalog) > score(current_candidate, current_catalog) else current


@beartype
def get_purchase_summary(query: str, period: str = "last_month", limit: int = 5) -> list[HistoryProductSummary]:
    raw_limit = max(limit * 6, 20) if REFS.enabled else limit
    rows: list[HistoryProductSummary] = []
    if HISTORY.enabled:
        try:
            rows = HISTORY.get_purchase_summary(query, period=period, limit=raw_limit)
        except Exception as exc:
            print(f"[ssh-history-summary] {exc}", flush=True)
    if not rows and LOCAL_ANALYTICS.enabled:
        try:
            rows = LOCAL_ANALYTICS.get_purchase_summary(query, period=period, limit=raw_limit)
        except Exception as exc:
            print(f"[local-analytics-summary] {exc}", flush=True)
    if REFS.enabled and rows:
        rows = REFS.aggregate_purchase_summaries(rows)
    return rows[:limit]


@beartype
def get_supplier_breakdown(query: str, period: str = "last_month", limit: int = 6) -> list[SupplierBreakdown]:
    rows: list[SupplierBreakdown] = []
    if HISTORY.enabled:
        try:
            rows = HISTORY.get_supplier_breakdown(query, period=period, limit=limit)
        except Exception as exc:
            print(f"[ssh-history-suppliers] {exc}", flush=True)
    if not rows and LOCAL_ANALYTICS.enabled:
        try:
            rows = LOCAL_ANALYTICS.get_supplier_breakdown(query, period=period, limit=limit)
        except Exception as exc:
            print(f"[local-analytics-suppliers] {exc}", flush=True)
    return rows[:limit]


@beartype
def resolve_catalog_candidates(query: str) -> dict[str, CatalogProduct]:
    merged: dict[str, CatalogProduct] = {}
    if HISTORY.enabled:
        try:
            for row in HISTORY.search_catalog(query, limit=8):
                if not row.ean:
                    continue
                merged[row.ean] = row
        except Exception as exc:
            print(f"[ssh-history-catalog] {exc}", flush=True)
    if not merged and REFS.enabled:
        try:
            for row in REFS.search_catalog(query, limit=8):
                if row.ean:
                    merged[row.ean] = row
        except Exception as exc:
            print(f"[refs-catalog] {exc}", flush=True)
    if not merged and LOCAL_ANALYTICS.enabled:
        try:
            for row in LOCAL_ANALYTICS.search_catalog(query, limit=8):
                if row.ean:
                    merged[row.ean] = row
        except Exception as exc:
            print(f"[local-analytics-catalog] {exc}", flush=True)
    return merged


@beartype
def collect_candidates(query: str) -> list[tuple[ProductCandidate, CatalogProduct | None]]:
    merged: dict[str, tuple[ProductCandidate, CatalogProduct | None]] = {}

    try:
        for candidate in API.search_product(query, limit=6):
            canonical_candidate, identity_key = resolve_candidate_identity(candidate)
            payload = (canonical_candidate, None)
            merged[identity_key] = choose_better_candidate(merged[identity_key], payload) if identity_key in merged else payload
    except Exception:
        pass

    catalog_map = resolve_catalog_candidates(query)
    for row in catalog_map.values():
        canonical_candidate, identity_key = resolve_candidate_identity(
            ProductCandidate(ean=row.ean, name=row.name, maker=row.maker, id_name=row.id_name)
        )
        payload = (canonical_candidate, row)
        merged[identity_key] = choose_better_candidate(merged[identity_key], payload) if identity_key in merged else payload

    if not merged:
        try:
            for item in get_purchase_summary(query, period="all_time", limit=5):
                canonical_candidate, identity_key = resolve_candidate_identity(
                    ProductCandidate(ean=item.ean, name=item.name, maker=item.maker, id_name=None)
                )
                payload = (canonical_candidate, None)
                merged[identity_key] = choose_better_candidate(merged[identity_key], payload) if identity_key in merged else payload
        except Exception:
            pass

    return list(merged.values())


@beartype
def build_ranked_candidates(query: str) -> list[RankedCandidate]:
    month = summary_identity_map(get_purchase_summary(query, period="last_month", limit=8))
    all_time = summary_identity_map(get_purchase_summary(query, period="all_time", limit=8))
    ranked: list[RankedCandidate] = []

    for candidate, catalog in collect_candidates(query):
        candidate, identity_key = resolve_candidate_identity(candidate)
        inventory = API.get_inventory(candidate.ean)
        month_item = month.get(identity_key)
        all_time_item = all_time.get(identity_key)
        score = 0.0
        if query.casefold() in candidate.name.casefold():
            score += 35
        if name_matches_dose_hints(candidate.name, query):
            score += 18
        elif dose_hints_for_query(query):
            score -= 30
        if all_time_item:
            score += 50 + min(25, all_time_item.purchase_count * 3) + min(25, all_time_item.qty_sum / 5)
        if month_item:
            score += 25 + min(20, month_item.qty_sum / 3)
        if inventory and inventory.qty > 0:
            score += 8
        if catalog:
            score += max(0, 8 - min(catalog.best_priority, 8))
            score += min(8, catalog.offer_count)

        ranked.append(
            RankedCandidate(
                candidate=candidate,
                score=score,
                inventory_qty=inventory.qty if inventory else None,
                month_qty=month_item.qty_sum if month_item else 0.0,
                month_count=month_item.purchase_count if month_item else 0,
                all_time_qty=all_time_item.qty_sum if all_time_item else 0.0,
                all_time_count=all_time_item.purchase_count if all_time_item else 0,
                top_supplier=(month_item or all_time_item).top_supplier if (month_item or all_time_item) else "",
                last_date=(month_item or all_time_item).last_date if (month_item or all_time_item) else "",
                offer_count=catalog.offer_count if catalog else 0,
                best_priority=catalog.best_priority if catalog else 999,
            )
        )

    ranked.sort(
        key=lambda item: (
            item.score,
            item.all_time_qty,
            item.month_qty,
            -(item.best_priority or 999),
            item.offer_count,
        ),
        reverse=True,
    )
    return ranked


@beartype
def resolution_reply(query: str, ranked: list[RankedCandidate]) -> str:
    if not ranked:
        return f"По `{query}` в текущем прайсе и истории ничего уверенного не нашёл."
    top = ranked[0]
    lines = [f"Скорее всего у вас это: {product_line(top.candidate)}"]
    reasons = ranking_reasons(top)
    if reasons:
        lines.extend(f"• {reason}" for reason in reasons[:4])
    if len(ranked) > 1:
        lines.append("")
        lines.append("Ещё варианты:")
        for item in ranked[1:4]:
            lines.append(f"• {product_line(item.candidate)}")
    return "\n".join(lines)


@beartype
def purchase_stats_reply(query: str, period: str) -> str:
    rows = get_purchase_summary(query, period=period, limit=5)
    dose_filtered = [item for item in rows if name_matches_dose_hints(item.name, query)]
    if dose_filtered:
        rows = dose_filtered
    if not rows:
        return f"По `{query}` {short_period_label(period)} в истории закупок ничего не нашёл."
    lines = [f"По `{query}` {short_period_label(period)} чаще брали:"]
    for idx, item in enumerate(rows[:3], start=1):
        supplier = f", чаще у {item.top_supplier}" if item.top_supplier else ""
        maker = f"{item.maker} — " if item.maker else ""
        lines.append(
            f"{idx}. {maker}{item.name} | {int(item.qty_sum)} шт | {item.purchase_count} закупок{supplier}"
        )
    return "\n".join(lines)


@beartype
def purchase_stats_fallback_reply(query: str, period: str, rows: list[HistoryProductSummary]) -> str:
    if not rows:
        return f"По {query} {friendly_period_label(period)} ничего в истории закупок не нашёл."
    lines = [f"По {query} {friendly_period_label(period)} чаще брали:"]
    for idx, item in enumerate(rows[:3], start=1):
        suffix = f", чаще у {item.top_supplier}" if item.top_supplier else ""
        maker_prefix = f"{item.maker} — " if item.maker else ""
        lines.append(f"{idx}. {maker_prefix}{item.name} | {int(item.qty_sum)} шт | {item.purchase_count} закупок{suffix}")
    return "\n".join(lines)


@beartype
def compare_suppliers_fallback_reply(query: str, period: str, rows: list[SupplierBreakdown]) -> str:
    if not rows:
        return f"По {query} {friendly_period_label(period)} не нашёл внятного сравнения по поставщикам."
    lines = [f"По {query} {friendly_period_label(period)} по поставщикам картина такая:"]
    for idx, item in enumerate(rows[:4], start=1):
        lines.append(f"{idx}. {item.supplier} | {int(item.qty_sum)} шт | {item.purchase_count} закупок")
    leader = rows[0]
    lines.append("")
    lines.append(f"Лидер: {leader.supplier}")
    return "\n".join(lines)


@beartype
def compare_periods_fallback_reply(
    query: str,
    period: str,
    compare_period: str,
    current_rows: list[HistoryProductSummary],
    compare_rows: list[HistoryProductSummary],
) -> str:
    current_qty = int(sum(item.qty_sum for item in current_rows))
    compare_qty = int(sum(item.qty_sum for item in compare_rows))
    delta = current_qty - compare_qty
    if not current_rows and not compare_rows:
        return f"По {query} не нашёл истории ни за {friendly_period_label(period)}, ни за {friendly_period_label(compare_period)}."
    direction = "без изменений"
    if delta > 0:
        direction = f"рост на {delta} шт"
    elif delta < 0:
        direction = f"падение на {abs(delta)} шт"
    return (
        f"По {query}: {friendly_period_label(period)} было {current_qty} шт, "
        f"а {friendly_period_label(compare_period)} было {compare_qty} шт. Итог: {direction}."
    )


@beartype
def resolution_fallback_reply(query: str, ranked: list[RankedCandidate]) -> str:
    if not ranked:
        return f"По {query} ничего уверенного не нашёл."
    top = ranked[0]
    lines = [f"Скорее всего ты имеешь в виду: {product_line(top.candidate)}"]
    reasons = ranking_reasons(top)
    if reasons:
        lines.extend(f"• {reason}" for reason in reasons[:3])
    if len(ranked) > 1:
        lines.append("")
        lines.append("Ещё варианты:")
        for item in ranked[1:4]:
            lines.append(f"• {product_line(item.candidate)}")
    return "\n".join(lines)


@beartype
def download_voice(client: httpx.Client, file_id: str) -> Path:
    response = client.get(api_url("getFile"), params={"file_id": file_id}, timeout=30)
    response.raise_for_status()
    file_path = response.json()["result"]["file_path"]
    voice_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    content = client.get(voice_url, timeout=60).content
    suffix = Path(file_path).suffix or ".ogg"
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    handle.write(content)
    handle.close()
    return Path(handle.name)


@beartype
def handle_readonly_action(
    client: httpx.Client,
    chat_id: int,
    source_text: str,
    intent: ParsedIntent,
    state: ChatState,
    *,
    allow_plan: bool = True,
) -> bool:
    if intent.action in {"chat", "unknown"}:
        if allow_plan:
            planned = PARSER.plan_readonly(source_text, context=chat_context_summary(state))
            planned.query = refine_query_with_context(chat_id, planned.action, planned.query)
            if not planned.query and planned.action in {"purchase_stats", "compare_suppliers", "compare_periods", "resolve_product", "show_inventory"} and state.last_product_focus:
                planned.query = state.last_product_focus
            if planned.action not in {"chat", "unknown"}:
                remember_chat_turn(chat_id, f"agent:{planned.action}", source_text)
                return handle_readonly_action(client, chat_id, source_text, planned, get_chat_state(chat_id), allow_plan=False)
        send_message(client, chat_id, PARSER.chat_reply(source_text, context=chat_reply_context()))
        return True

    if intent.action == "show_inventory":
        if not intent.query:
            send_message(client, chat_id, "Не добрал товар. Скажи, например: покажи остаток по этой позиции")
            return True
        ranked = build_ranked_candidates(intent.query)
        if not ranked:
            send_message(client, chat_id, f"По {intent.query} кандидатов не нашёл.")
            return True
        update_chat_focus(chat_id, ranked[0].candidate.name, intent.period or "last_month")
        remember_candidates(chat_id, ranked)
        payload = {
            "query": intent.query,
            "selected": serialize_ranked_item(ranked[0]),
            "reasons": ranking_reasons(ranked[0]),
        }
        send_message(
            client,
            chat_id,
            grounded_readonly_reply(
                user_message=source_text,
                state=get_chat_state(chat_id),
                tool_name="show_inventory",
                tool_payload=payload,
                fallback_text=inventory_status_reply(ranked[0]),
            ),
        )
        return True

    if intent.action == "resolve_product":
        update_chat_focus(chat_id, intent.query, intent.period or "last_month")
        ranked = build_ranked_candidates(intent.query)
        remember_candidates(chat_id, ranked)
        payload = {
            "query": intent.query,
            "top": serialize_ranked_item(ranked[0]) if ranked else None,
            "alternatives": [serialize_ranked_item(item) for item in ranked[1:4]],
            "reasons": ranking_reasons(ranked[0]) if ranked else [],
        }
        send_message(
            client,
            chat_id,
            grounded_readonly_reply(
                user_message=source_text,
                state=get_chat_state(chat_id),
                tool_name="resolve_product",
                tool_payload=payload,
                fallback_text=resolution_fallback_reply(intent.query, ranked),
            ),
        )
        return True

    if intent.action == "purchase_stats":
        update_chat_focus(chat_id, intent.query, intent.period or "last_month")
        ranked = build_ranked_candidates(intent.query)
        remember_candidates(chat_id, ranked)
        rows = get_purchase_summary(intent.query, period=intent.period, limit=5)
        dose_filtered = [item for item in rows if name_matches_dose_hints(item.name, intent.query)]
        if dose_filtered:
            rows = dose_filtered
        payload = {
            "query": intent.query,
            "period": intent.period,
            "period_label": friendly_period_label(intent.period or "last_month"),
            "rows": [
                {
                    "ean": item.ean,
                    "name": item.name,
                    "maker": item.maker,
                    "qty_sum": int(item.qty_sum),
                    "purchase_count": item.purchase_count,
                    "last_date": item.last_date,
                    "top_supplier": item.top_supplier,
                }
                for item in rows[:5]
            ],
        }
        send_message(
            client,
            chat_id,
            grounded_readonly_reply(
                user_message=source_text,
                state=get_chat_state(chat_id),
                tool_name="purchase_stats",
                tool_payload=payload,
                fallback_text=purchase_stats_fallback_reply(intent.query, intent.period or "last_month", rows),
            ),
        )
        return True

    if intent.action == "compare_suppliers":
        update_chat_focus(chat_id, intent.query, intent.period or "last_month")
        remember_candidates(chat_id, build_ranked_candidates(intent.query))
        rows = get_supplier_breakdown(intent.query, period=intent.period or "last_month", limit=6)
        payload = {
            "query": intent.query,
            "period": intent.period,
            "period_label": friendly_period_label(intent.period or "last_month"),
            "suppliers": [
                {
                    "supplier": item.supplier,
                    "qty_sum": int(item.qty_sum),
                    "purchase_count": item.purchase_count,
                    "last_date": item.last_date,
                }
                for item in rows
            ],
        }
        send_message(
            client,
            chat_id,
            grounded_readonly_reply(
                user_message=source_text,
                state=get_chat_state(chat_id),
                tool_name="compare_suppliers",
                tool_payload=payload,
                fallback_text=compare_suppliers_fallback_reply(intent.query, intent.period or "last_month", rows),
            ),
        )
        return True

    if intent.action == "compare_periods":
        primary_period = intent.period or "last_month"
        compare_period = intent.compare_period or "last_month"
        update_chat_focus(chat_id, intent.query, primary_period)
        remember_candidates(chat_id, build_ranked_candidates(intent.query))
        current_rows = get_purchase_summary(intent.query, period=primary_period, limit=5)
        compare_rows = get_purchase_summary(intent.query, period=compare_period, limit=5)
        payload = {
            "query": intent.query,
            "period": primary_period,
            "period_label": friendly_period_label(primary_period),
            "compare_period": compare_period,
            "compare_period_label": friendly_period_label(compare_period),
            "current_rows": [
                {
                    "name": item.name,
                    "maker": item.maker,
                    "qty_sum": int(item.qty_sum),
                    "purchase_count": item.purchase_count,
                    "top_supplier": item.top_supplier,
                }
                for item in current_rows
            ],
            "compare_rows": [
                {
                    "name": item.name,
                    "maker": item.maker,
                    "qty_sum": int(item.qty_sum),
                    "purchase_count": item.purchase_count,
                    "top_supplier": item.top_supplier,
                }
                for item in compare_rows
            ],
        }
        send_message(
            client,
            chat_id,
            grounded_readonly_reply(
                user_message=source_text,
                state=get_chat_state(chat_id),
                tool_name="compare_periods",
                tool_payload=payload,
                fallback_text=compare_periods_fallback_reply(intent.query, primary_period, compare_period, current_rows, compare_rows),
            ),
        )
        return True

    return False


@beartype
def handle_intent(client: httpx.Client, chat_id: int, source_text: str, intent: ParsedIntent) -> None:
    intent.query = refine_query_with_context(chat_id, intent.action, intent.query)
    remember_chat_turn(chat_id, intent.action, source_text)
    state = get_chat_state(chat_id)
    print(
        f"[intent] chat={chat_id} action={intent.action} query={intent.query!r} "
        f"focus={state.last_product_focus!r} candidates={len(state.recent_candidates)}",
        flush=True,
    )

    if handle_readonly_action(client, chat_id, source_text, intent, state):
        return

    if intent.action == "restore_inventory":
        snapshot = get_last_deleted_snapshot(chat_id)
        deleted_item = build_deleted_candidate(chat_id)
        if not snapshot or not deleted_item:
            send_message(client, chat_id, "Нечего возвращать: в этом чате нет последней удалённой позиции.")
            return
        token = make_token()
        pending = PendingAction(
            token=token,
            chat_id=chat_id,
            source_text=source_text,
            operation="restore_inventory",
            query=deleted_item.candidate.name,
            qty=int(snapshot.get("qty", 0) or 0),
            ranked=[deleted_item],
        )
        put_pending(pending)
        send_message(client, chat_id, preview_text(pending), preview_buttons(token, False))
        return

    if intent.action == "show_inventory":
        if not intent.query:
            send_message(client, chat_id, "Не добрал товар. Скажи, например: покажи остаток по этой позиции")
            return
        ranked = build_ranked_candidates(intent.query)
        if not ranked:
            send_message(client, chat_id, f"По `{intent.query}` кандидатов не нашёл.")
            return
        update_chat_focus(chat_id, ranked[0].candidate.name, intent.period or "last_month")
        remember_candidates(chat_id, ranked)
        send_message(client, chat_id, inventory_status_reply(ranked[0]))
        return

    if intent.action in {"set_inventory", "add_inventory", "subtract_inventory", "delete_inventory"}:
        if not intent.query or (intent.action != "delete_inventory" and intent.qty is None):
            send_message(client, chat_id, "Не добрал товар или количество. Скажи, например: поставь остаток азитромицина 5 штук")
            return
        ranked = build_ranked_candidates(intent.query)
        if not ranked:
            send_message(client, chat_id, f"По `{intent.query}` кандидатов не нашёл.")
            return
        update_chat_focus(chat_id, ranked[0].candidate.name, intent.period or "last_month")
        remember_candidates(chat_id, ranked)
        print(
            f"[inventory-preview] chat={chat_id} resolved={ranked[0].candidate.name!r} "
            f"maker={ranked[0].candidate.maker!r} ranked={len(ranked)}",
            flush=True,
        )
        token = make_token()
        pending = PendingAction(
            token=token,
            chat_id=chat_id,
            source_text=source_text,
            operation=intent.action,
            query=intent.query,
            qty=intent.qty or 0,
            ranked=ranked,
        )
        put_pending(pending)
        send_message(client, chat_id, preview_text(pending), preview_buttons(token, len(ranked) > 1))
        return

    if intent.action == "resolve_product":
        update_chat_focus(chat_id, intent.query, intent.period or "last_month")
        ranked = build_ranked_candidates(intent.query)
        remember_candidates(chat_id, ranked)
        send_message(client, chat_id, resolution_reply(intent.query, ranked))
        return

    if intent.action == "purchase_stats":
        update_chat_focus(chat_id, intent.query, intent.period or "last_month")
        remember_candidates(chat_id, build_ranked_candidates(intent.query))
        send_message(client, chat_id, purchase_stats_reply(intent.query, intent.period))
        return

    state = get_chat_state(chat_id)
    context = (
        "Ты привязан к PharmOrder. Лучше помогай по остаткам, товарам и истории закупок. "
        "Если пользователь просто общается, не тащи в ответ прошлый товар без запроса."
    )
    send_message(client, chat_id, PARSER.chat_reply(source_text, context=context))


@beartype
def handle_message(client: httpx.Client, message: dict[str, Any]) -> None:
    chat_id = int(message["chat"]["id"])
    user_id = int(message.get("from", {}).get("id", 0) or 0)
    if user_id not in ALLOWED_CHAT_IDS:
        return

    if text := str(message.get("text") or "").strip():
        if text in {"/start", "/help"}:
            send_message(client, chat_id, "Умею говорить по товарам, истории закупок и готовить изменение остатка через confirm. Примеры: `поставь остаток азитромицина 5`, `добавь 5 штук промедовского в остатки`, `какой у нас азитромицин?`")
            return
        handle_intent(client, chat_id, text, PARSER.parse(text))
        return

    voice = message.get("voice") or message.get("audio")
    if voice and voice.get("file_id"):
        tmp_path = download_voice(client, str(voice["file_id"]))
        try:
            transcript = PARSER.transcribe_voice(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
        if not transcript:
            send_message(client, chat_id, "Голос не расшифровал. Лучше повтори текстом.")
            return
        send_message(client, chat_id, f"Расслышал так: {transcript}")
        handle_intent(client, chat_id, transcript, PARSER.parse(transcript))


@beartype
def handle_callback(client: httpx.Client, callback: dict[str, Any]) -> None:
    callback_id = str(callback["id"])
    message = callback.get("message") or {}
    chat_id = int(message.get("chat", {}).get("id", 0) or 0)
    message_id = int(message.get("message_id", 0) or 0)
    data = str(callback.get("data") or "")

    if data.startswith("cancel:"):
        token = data.split(":", 1)[1]
        delete_pending(token)
        edit_message(client, chat_id, message_id, "Ок, отменил.")
        answer_callback(client, callback_id)
        return

    if data.startswith("choose:"):
        token = data.split(":", 1)[1]
        action = get_pending(token)
        if not action:
            answer_callback(client, callback_id, "Это подтверждение уже протухло.")
            return
        lines = [f"Выбери товар для `{action.query}`:"]
        for idx, item in enumerate(action.ranked[:5], start=1):
            lines.append(f"{idx}. {product_line(item.candidate)}")
        edit_message(client, chat_id, message_id, "\n".join(lines), choice_buttons(token, action))
        answer_callback(client, callback_id)
        return

    if data.startswith("pick:"):
        _, token, raw_idx = data.split(":", 2)
        action = get_pending(token)
        if not action:
            answer_callback(client, callback_id, "Этот выбор уже протух.")
            return
        action.selected_index = max(0, min(int(raw_idx), len(action.ranked) - 1))
        edit_message(client, chat_id, message_id, preview_text(action), preview_buttons(token, len(action.ranked) > 1))
        answer_callback(client, callback_id)
        return

    if data.startswith("apply:"):
        token = data.split(":", 1)[1]
        action = pop_pending(token)
        if not action:
            answer_callback(client, callback_id, "Это подтверждение уже использовано.")
            return
        item = action.selected
        if action.operation == "add_inventory":
            updated = API.add_inventory(
                ean=item.candidate.ean,
                name=item.candidate.name,
                maker=item.candidate.maker,
                qty=action.qty,
            )
        elif action.operation == "subtract_inventory":
            updated = API.subtract_inventory(
                ean=item.candidate.ean,
                name=item.candidate.name,
                maker=item.candidate.maker,
                qty=action.qty,
            )
        elif action.operation == "delete_inventory":
            deleted = API.delete_inventory(item.candidate.ean)
            if not deleted:
                edit_message(client, chat_id, message_id, f"Не нашёл в inventory:\n{product_line(item.candidate)}")
                answer_callback(client, callback_id, "Не нашёл.")
                return
            remember_last_deleted(chat_id, item)
            update_chat_focus(chat_id, item.candidate.name, "last_month")
            remember_candidates(chat_id, action.ranked)
            audit({
                "event": action.operation,
                "chat_id": chat_id,
                "query": action.query,
                "source_text": action.source_text,
                "ean": item.candidate.ean,
                "name": item.candidate.name,
                "old_qty": item.inventory_qty if item.inventory_qty is not None else 0,
                "new_qty": None,
            })
            edit_message(
                client,
                chat_id,
                message_id,
                f"Удалил из inventory.\n{product_line(item.candidate)}\nБыло: {item.inventory_qty if item.inventory_qty is not None else 0}",
            )
            answer_callback(client, callback_id, "Удалил.")
            return
        elif action.operation == "restore_inventory":
            updated = API.set_inventory(
                ean=item.candidate.ean,
                name=item.candidate.name,
                maker=item.candidate.maker,
                qty=action.qty,
            )
        else:
            updated = API.set_inventory(
                ean=item.candidate.ean,
                name=item.candidate.name,
                maker=item.candidate.maker,
                qty=action.qty,
            )
        update_chat_focus(chat_id, item.candidate.name, "last_month")
        remember_candidates(chat_id, action.ranked)
        audit({
            "event": action.operation,
            "chat_id": chat_id,
            "query": action.query,
            "source_text": action.source_text,
            "ean": updated.ean,
            "name": updated.name,
            "old_qty": item.inventory_qty if item.inventory_qty is not None else 0,
            "new_qty": updated.qty,
        })
        edit_message(
            client,
            chat_id,
            message_id,
            f"Готово.\n{product_line(item.candidate)}\nБыло: {item.inventory_qty if item.inventory_qty is not None else 0}\nСтало: {updated.qty}",
        )
        answer_callback(client, callback_id, "Применил.")


def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("Telegram bot token not set")
    if not GEMINI_API_KEY:
        raise SystemExit("GOOGLE_API_KEY not set")
    print(
        f"tg-pharma started | build={BOT_BUILD} | file={__file__} | "
        f"api={API_BASE} | allowed={sorted(ALLOWED_CHAT_IDS)} | model={GEMINI_MODEL} | "
        f"refs={'on' if REFS.enabled else 'off'} | refs_db={REFS_DB} | "
        f"local_analytics_fallback={'on' if LOCAL_ANALYTICS.enabled else 'off'}",
        flush=True,
    )
    offset = 0
    last_pending_cleanup = 0.0
    allowed_updates = json.dumps(["message", "callback_query"])
    with httpx.Client(timeout=40) as client:
        flush = client.get(api_url("getUpdates"), params={"offset": -1, "allowed_updates": allowed_updates}, timeout=20)
        flush.raise_for_status()
        updates = flush.json().get("result") or []
        if updates:
            offset = int(updates[-1]["update_id"]) + 1
        while True:
            try:
                now = time.time()
                if now - last_pending_cleanup >= PENDING_CLEANUP_INTERVAL_SECONDS:
                    with PENDING_LOCK:
                        cleanup_pending_locked(now)
                    last_pending_cleanup = now
                response = client.get(
                    api_url("getUpdates"),
                    params={"offset": offset, "timeout": 30, "allowed_updates": allowed_updates},
                    timeout=40,
                )
                response.raise_for_status()
                for update in response.json().get("result") or []:
                    offset = int(update["update_id"]) + 1
                    if update.get("message"):
                        handle_message(client, update["message"])
                    elif update.get("callback_query"):
                        handle_callback(client, update["callback_query"])
            except httpx.ReadTimeout:
                continue
            except KeyboardInterrupt:
                print("stopped", flush=True)
                break
            except PharmOrderError as exc:
                print(f"pharmorder error: {exc}", flush=True)
                time.sleep(2)
            except Exception as exc:
                print(f"loop error: {exc}", flush=True)
                time.sleep(2)


if __name__ == "__main__":
    main()
