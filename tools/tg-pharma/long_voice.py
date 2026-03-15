from __future__ import annotations

import time
from typing import Any, Callable

import httpx
from beartype import beartype

from segment_actions import (
    VoiceDraft,
    clear_draft,
    extract_actions,
    load_draft,
    resolve_actions,
    save_draft,
)

LONG_VOICE_THRESHOLD_SECONDS = 60
SHORT_VOICE_MULTI_ACTION_MIN = 2

_KIND_LABEL: dict[str, str] = {
    "inventory_set": "Установить =",
    "inventory_add": "Добавить +",
    "inventory_subtract": "Убрать -",
    "inventory_delete": "Удалить",
}


def _tg_send(client: httpx.Client, bot_token: str, chat_id: int, text: str) -> int | None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = client.post(url, json={"chat_id": chat_id, "text": text[:4000]}, timeout=30)
        if resp.is_success:
            return int(resp.json().get("result", {}).get("message_id", 0)) or None
    except Exception:
        pass
    return None


@beartype
def _status(
    client: httpx.Client,
    bot_token: str,
    chat_id: int,
    message_id: int | None,
    edit_fn: Callable[..., Any],
    text: str,
    buttons: list[list[dict[str, str]]] | None = None,
) -> None:
    if message_id:
        try:
            edit_fn(client, chat_id, message_id, text, buttons)
            return
        except Exception:
            pass
    _tg_send(client, bot_token, chat_id, text[:4000])


@beartype
def process_transcript_to_draft(
    client: httpx.Client,
    chat_id: int,
    transcript: str,
    bot_token: str,
    resolve_fn: Callable[..., Any],
    edit_fn: Callable[..., Any],
    api_key: str,
    model: str,
    status_mid: int | None = None,
) -> VoiceDraft | None:
    _status(
        client,
        bot_token,
        chat_id,
        status_mid,
        edit_fn,
        f"🎙 Расшифровал ({len(transcript)} симв.). Ищу команды...",
    )

    try:
        actions = extract_actions(transcript, api_key, model)
    except Exception as e:
        _status(
            client,
            bot_token,
            chat_id,
            status_mid,
            edit_fn,
            f"🎙 Расшифровал:\n{transcript[:500]}\n\nОшибка извлечения команд: {e}",
        )
        return None

    if not actions:
        _status(
            client,
            bot_token,
            chat_id,
            status_mid,
            edit_fn,
            f"🎙 Расшифровал:\n{transcript[:400]}\n\nКоманд по остаткам не нашёл.",
        )
        return None

    resolved, ambiguous, not_found = resolve_actions(actions, resolve_fn)
    draft = VoiceDraft(
        chat_id=chat_id,
        created_at=time.time(),
        transcript=transcript,
        message_id=status_mid,
        resolved=resolved,
        ambiguous=ambiguous,
        not_found=not_found,
    )
    save_draft(draft)
    text, buttons = render_draft_summary(draft)
    _status(client, bot_token, chat_id, status_mid, edit_fn, text, buttons)
    return draft


@beartype
def maybe_process_short_voice_as_draft(
    client: httpx.Client,
    chat_id: int,
    transcript: str,
    bot_token: str,
    resolve_fn: Callable[..., Any],
    edit_fn: Callable[..., Any],
    api_key: str,
    model: str,
) -> bool:
    try:
        actions = extract_actions(transcript, api_key, model)
    except Exception:
        return False
    if len(actions) < SHORT_VOICE_MULTI_ACTION_MIN:
        return False
    process_transcript_to_draft(
        client=client,
        chat_id=chat_id,
        transcript=transcript,
        bot_token=bot_token,
        resolve_fn=resolve_fn,
        edit_fn=edit_fn,
        api_key=api_key,
        model=model,
        status_mid=None,
    )
    return True


@beartype
def handle_long_voice(
    client: httpx.Client,
    chat_id: int,
    voice: dict[str, Any],
    bot_token: str,
    download_fn: Callable[..., Any],
    transcribe_fn: Callable[..., Any],
    resolve_fn: Callable[..., Any],
    edit_fn: Callable[..., Any],
    send_fn: Callable[..., Any],
    api_key: str,
    model: str,
    audit_fn: Callable[..., Any],
    api: Any,
) -> None:
    file_id = str(voice["file_id"])
    duration = int(voice.get("duration", 0))
    status_mid = _tg_send(client, bot_token, chat_id, f"🎙 Голосовое {duration}с — расшифровываю...")

    tmp_path = download_fn(client, file_id)
    try:
        transcript = transcribe_fn(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    if not transcript:
        _status(
            client,
            bot_token,
            chat_id,
            status_mid,
            edit_fn,
            "Не смог расшифровать голосовое. Попробуй ещё раз.",
        )
        return

    process_transcript_to_draft(
        client=client,
        chat_id=chat_id,
        transcript=transcript,
        bot_token=bot_token,
        resolve_fn=resolve_fn,
        edit_fn=edit_fn,
        api_key=api_key,
        model=model,
        status_mid=status_mid,
    )


@beartype
def render_draft_summary(draft: VoiceDraft) -> tuple[str, list[list[dict[str, str]]]]:
    n_res = len(draft.resolved)
    n_amb = len(draft.ambiguous)
    n_nf = len(draft.not_found)
    total = n_res + n_amb + n_nf
    cid = draft.chat_id
    transcript_preview = draft.transcript.strip()
    if len(transcript_preview) > 1200:
        transcript_preview = transcript_preview[:1200].rstrip() + "..."

    lines = [
        f"📝 Расслышал так:\n{transcript_preview}\n",
        f"🎙 Голосовой черновик — {total} команд(ы)\n",
    ]

    if n_res:
        lines.append(f"✅ Готово к применению ({n_res}):")
        for r in draft.resolved[:5]:
            a = r["action"]
            label = _KIND_LABEL.get(a["kind"], a["kind"])
            qty_str = f" {a['qty']}" if a["kind"] != "inventory_delete" else ""
            lines.append(f"  • {r['name']} -> {label}{qty_str}")
        if n_res > 5:
            lines.append(f"  … и ещё {n_res - 5}")

    if n_amb:
        lines.append(f"\n❓ Неоднозначно ({n_amb}):")
        for entry in draft.ambiguous[:3]:
            a = entry["action"]
            lines.append(f"  • «{a['query']}» — {len(entry['candidates'])} варианта")

    if n_nf:
        lines.append(f"\n❌ Не найдено ({n_nf}):")
        for entry in draft.not_found[:3]:
            lines.append(f"  • «{entry['query']}»")

    buttons: list[list[dict[str, str]]] = []
    row1: list[dict[str, str]] = []
    if n_res:
        row1.append({"text": f"✅ Готовые ({n_res})", "callback_data": f"lv_show:resolved:{cid}"})
    if n_amb:
        row1.append({"text": f"❓ Неясные ({n_amb})", "callback_data": f"lv_show:ambiguous:{cid}"})
    if row1:
        buttons.append(row1)

    if n_nf:
        buttons.append([{"text": f"❌ Не найдено ({n_nf})", "callback_data": f"lv_show:notfound:{cid}"}])

    row_action: list[dict[str, str]] = []
    if n_res and draft.apply_status == "pending":
        row_action.append({"text": "🚀 Применить готовые", "callback_data": f"lv_apply:{cid}"})
    row_action.append({"text": "🗑 Очистить", "callback_data": f"lv_clear:{cid}"})
    buttons.append(row_action)

    return "\n".join(lines), buttons


@beartype
def handle_lv_callback(
    client: httpx.Client,
    chat_id: int,
    message_id: int,
    callback_id: str,
    data: str,
    answer_fn: Callable[..., Any],
    edit_fn: Callable[..., Any],
    api: Any,
    audit_fn: Callable[..., Any],
) -> None:
    parts = data.split(":")
    verb = parts[0]

    if verb == "lv_show":
        section = parts[1] if len(parts) > 1 else ""
        draft = load_draft(chat_id)
        if not draft:
            answer_fn(client, callback_id, "Черновик не найден или устарел.")
            return
        if section == "resolved":
            text = _render_resolved_full(draft)
        elif section == "ambiguous":
            text = _render_ambiguous_full(draft)
        elif section == "notfound":
            text = _render_notfound_full(draft)
        else:
            text = "Неизвестная секция."
        _, back_buttons = render_draft_summary(draft)
        edit_fn(client, chat_id, message_id, text, back_buttons)
        answer_fn(client, callback_id)
        return

    if verb == "lv_apply":
        draft = load_draft(chat_id)
        if not draft:
            answer_fn(client, callback_id, "Черновик не найден.")
            return
        if draft.apply_status == "done":
            answer_fn(client, callback_id, "Уже применено.")
            return
        if not draft.resolved:
            answer_fn(client, callback_id, "Нечего применять.")
            return
        ok, failed = _apply_resolved_partial(draft, api, audit_fn)
        draft.apply_status = "partial" if failed else "done"
        draft.apply_log = [r for r, _ in ok] + [r for r, _ in failed]
        failed_eans = {ean for _, ean in failed}
        draft.resolved = [r for r in draft.resolved if r["ean"] in failed_eans]
        save_draft(draft)
        lines: list[str] = []
        if ok:
            lines.append(f"✅ Применено ({len(ok)}):")
            lines.extend(f"  {r}" for r, _ in ok)
        if failed:
            lines.append(f"\n⚠ Ошибки ({len(failed)}) — остались в черновике:")
            lines.extend(f"  {r}" for r, _ in failed)
        edit_fn(client, chat_id, message_id, "\n".join(lines))
        answer_fn(client, callback_id, f"ok={len(ok)} err={len(failed)}")
        return

    if verb == "lv_clear":
        clear_draft(chat_id)
        edit_fn(client, chat_id, message_id, "Черновик очищен.")
        answer_fn(client, callback_id, "Очищено.")
        return

    answer_fn(client, callback_id, "Неизвестная команда.")


def _render_resolved_full(draft: VoiceDraft) -> str:
    if not draft.resolved:
        return "Нет готовых к применению команд."
    status = " (уже применено)" if draft.apply_status == "done" else ""
    lines = [f"✅ Готово к применению ({len(draft.resolved)}){status}:"]
    for r in draft.resolved:
        a = r["action"]
        label = _KIND_LABEL.get(a["kind"], a["kind"])
        qty_str = f" {a['qty']}" if a["kind"] != "inventory_delete" else ""
        lines.append(f"\n• {r['name']} ({r['maker']})")
        lines.append(f"  EAN: {r['ean']}")
        lines.append(f"  Операция: {label}{qty_str}")
        lines.append(f"  Из: «{a['raw']}»")
    return "\n".join(lines)


def _render_ambiguous_full(draft: VoiceDraft) -> str:
    if not draft.ambiguous:
        return "Нет неоднозначных команд."
    lines = [f"❓ Неоднозначно ({len(draft.ambiguous)}):"]
    for entry in draft.ambiguous:
        a = entry["action"]
        label = _KIND_LABEL.get(a["kind"], a["kind"])
        qty_str = f" {a['qty']}" if a["kind"] != "inventory_delete" else ""
        lines.append(f"\n• «{a['query']}» — {label}{qty_str}")
        lines.append("  Варианты:")
        for c in entry["candidates"]:
            lines.append(f"    {c['name']} ({c['maker']}) — EAN {c['ean']}")
        lines.append("  -> Уточни название в тексте или отдельным голосовым.")
    return "\n".join(lines)


def _render_notfound_full(draft: VoiceDraft) -> str:
    if not draft.not_found:
        return "Всё найдено."
    lines = [f"❌ Не найдено ({len(draft.not_found)}):"]
    for entry in draft.not_found:
        label = _KIND_LABEL.get(entry["kind"], entry["kind"])
        qty_str = f" {entry['qty']}" if entry["kind"] != "inventory_delete" else ""
        lines.append(f"• «{entry['query']}» — {label}{qty_str}")
        lines.append(f"  Из: «{entry['raw']}»")
    lines.append("\nПопробуй уточнить название.")
    return "\n".join(lines)


def _apply_resolved_partial(
    draft: VoiceDraft,
    api: Any,
    audit_fn: Callable[..., Any],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    ok: list[tuple[str, str]] = []
    failed: list[tuple[str, str]] = []
    for r in draft.resolved:
        a = r["action"]
        ean: str = r["ean"]
        name: str = r["name"]
        maker: str = r["maker"]
        kind: str = a["kind"]
        qty: int = int(a["qty"])
        try:
            if kind == "inventory_set":
                api.set_inventory(ean=ean, name=name, maker=maker, qty=qty)
                msg = f"✓ {name}: = {qty}"
            elif kind == "inventory_add":
                api.add_inventory(ean=ean, name=name, maker=maker, qty=qty)
                msg = f"✓ {name}: +{qty}"
            elif kind == "inventory_subtract":
                api.subtract_inventory(ean=ean, name=name, maker=maker, qty=qty)
                msg = f"✓ {name}: -{qty}"
            elif kind == "inventory_delete":
                deleted = api.delete_inventory(ean=ean)
                msg = f"✓ {name}: удалено" if deleted else f"⚠ {name}: не было"
            else:
                msg = f"⚠ {name}: неизвестная операция {kind}"
            ok.append((msg, ean))
        except Exception as e:
            msg = f"✗ {name}: {e}"
            failed.append((msg, ean))
        audit_fn(
            {
                "event": f"long_voice_{kind}",
                "chat_id": draft.chat_id,
                "ean": ean,
                "name": name,
                "qty": qty,
                "result": msg,
            }
        )
    return ok, failed
