"""Steam Sniper — CS2 skin price alert bot for Telegram.

Monitors lis-skins.com public JSON for price changes.
Two watchlists: BUY (alert when below target) and SELL (alert when above target).

Usage:
    cd tools/steam-sniper && uv sync && uv run python main.py
"""
from __future__ import annotations

import json
import logging
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import db

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("sniper")

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
LISSKINS_URL = "https://lis-skins.com/market_export_json/csgo.json"
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CHECK_INTERVAL_S = 2 * 60 * 60  # 2 hours
CBR_URL = "https://www.cbr-xml-daily.ru/daily_json.js"

_usd_rub_rate: float = 0.0
_usd_rub_updated: float = 0.0

_prices_cache: tuple[float, dict[str, dict]] | None = None
_CACHE_TTL = 240  # 4 minutes


def _get_usd_rub() -> float:
    """Get USD/RUB rate, cached for 1 hour. Persists to DB."""
    global _usd_rub_rate, _usd_rub_updated
    # Cold start: try loading from DB
    if _usd_rub_rate == 0:
        cached = db.get_cached_rate("USD")
        if cached:
            _usd_rub_rate = cached
            logger.info(f"USD/RUB rate from DB cache: {_usd_rub_rate:.2f}")
    if _usd_rub_rate > 0 and (time.time() - _usd_rub_updated) < 3600:
        return _usd_rub_rate
    try:
        req = urllib.request.Request(CBR_URL, headers={"User-Agent": "SteamSniper/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        _usd_rub_rate = float(data["Valute"]["USD"]["Value"])
        _usd_rub_updated = time.time()
        db.save_rate("USD", _usd_rub_rate)
        logger.info(f"USD/RUB rate: {_usd_rub_rate:.2f}")
    except Exception as e:
        logger.warning(f"Failed to fetch USD/RUB rate: {e}")
        if _usd_rub_rate == 0:
            _usd_rub_rate = 80.0  # fallback
    return _usd_rub_rate


def _p(usd: float) -> str:
    """Format price: show both RUB and USD."""
    rate = _get_usd_rub()
    rub = usd * rate
    return f"{rub:.0f}₽ (${usd:.2f})"


# --- Price cache ---


def _get_prices_cached() -> dict[str, dict]:
    """Return cached prices if fresh (< 4 min), otherwise re-fetch."""
    global _prices_cache
    now = time.time()
    if _prices_cache and (now - _prices_cache[0]) < _CACHE_TTL:
        return _prices_cache[1]
    prices = fetch_prices()
    _prices_cache = (now, prices)
    return prices


# --- Lis-Skins fetch ---

def fetch_prices() -> dict[str, dict]:
    """Fetch all CS2 items from lis-skins. Returns {name_lower: {name, price, url, count}}."""
    req = urllib.request.Request(LISSKINS_URL, headers={"User-Agent": "SteamSniper/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        items = json.loads(resp.read().decode("utf-8"))
    return {item["name"].lower(): item for item in items}


def _build_url_index(prices: dict[str, dict]) -> dict[str, dict]:
    """Build slug→item index from URLs for fast link lookup."""
    index = {}
    for item in prices.values():
        url = item.get("url", "")
        if url:
            # Extract slug: .../market/csgo/kilowatt-case/ -> kilowatt-case
            match = re.search(r"/market/csgo/([^/?]+)", url)
            if match:
                index[match.group(1)] = item
    return index


_LIS_SKINS_LINK_RE = re.compile(r"lis-skins\.com/(?:\w+/)?market/csgo/([^/?\s]+)")


def find_item(prices: dict[str, dict], query: str) -> list[dict]:
    """Fuzzy-ish search: find items containing all query words."""
    words = query.lower().split()
    results = []
    for name_lower, item in prices.items():
        if all(w in name_lower for w in words):
            results.append(item)
    return sorted(results, key=lambda x: x["price"])[:10]


# --- Alert check ---

def check_alerts(prices: dict[str, dict]) -> list[str]:
    """Check watchlist against current prices, return alert messages."""
    wl = db.get_watchlist()
    alerts = []
    rate = _get_usd_rub()

    for entry in wl.get("buy", []):
        name_lower = entry["name"].lower()
        item = prices.get(name_lower)
        if not item:
            continue
        if item["price"] * rate <= entry["target_rub"]:
            alert_msg = (
                f"📉 КУПИТЬ: {item['name']}\n"
                f"Цена: {_p(item['price'])} (цель: <={entry['target_rub']:.0f}₽)\n"
                f"В наличии: {item.get('count', '?')}\n"
                f"{item.get('url', '')}"
            )
            alerts.append(alert_msg)
            db.log_alert(
                name=item["name"],
                type_="buy",
                price_usd=item["price"],
                target_rub=entry["target_rub"],
                message=alert_msg,
            )

    for entry in wl.get("sell", []):
        name_lower = entry["name"].lower()
        item = prices.get(name_lower)
        if not item:
            continue
        if item["price"] * rate >= entry["target_rub"]:
            alert_msg = (
                f"📈 ПРОДАТЬ: {item['name']}\n"
                f"Цена: {_p(item['price'])} (цель: >={entry['target_rub']:.0f}₽)\n"
                f"В наличии: {item.get('count', '?')}\n"
                f"{item.get('url', '')}"
            )
            alerts.append(alert_msg)
            db.log_alert(
                name=item["name"],
                type_="sell",
                price_usd=item["price"],
                target_rub=entry["target_rub"],
                message=alert_msg,
            )

    return alerts


# --- Periodic job ---

async def periodic_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runs every CHECK_INTERVAL_S — fetch prices, check alerts, notify."""
    logger.info("Running periodic price check...")
    try:
        prices = _get_prices_cached()
        logger.info(f"Fetched {len(prices)} items from lis-skins")
    except Exception as e:
        logger.error(f"Failed to fetch prices: {e}")
        return

    alerts = check_alerts(prices)
    if not alerts:
        logger.info("No alerts triggered")
        return

    chat_ids = os.environ.get("ALERT_CHAT_IDS", "").split(",")
    chat_ids = [cid.strip() for cid in chat_ids if cid.strip()]

    if not chat_ids:
        logger.warning("No ALERT_CHAT_IDS configured — alerts have nowhere to go")
        return

    header = f"🔔 Steam Sniper — {datetime.now().strftime('%d.%m %H:%M')}\n\n"
    message = header + "\n\n".join(alerts)

    for cid in chat_ids:
        try:
            await context.bot.send_message(chat_id=int(cid), text=message)
        except Exception as e:
            logger.error(f"Failed to send alert to {cid}: {e}")


async def periodic_snapshot(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Every 5 min: snapshot prices for watched items, prune old data."""
    watched = db.get_watchlist_names()
    if not watched:
        return
    try:
        prices = _get_prices_cached()
    except Exception as e:
        logger.warning(f"Snapshot fetch failed: {e}")
        return
    snapshots = [
        (name, prices[name]["price"])
        for name in watched
        if name in prices
    ]
    if snapshots:
        db.insert_price_snapshots(snapshots)
        logger.info(f"Snapshot: {len(snapshots)} prices recorded")
    db.prune_old_history(days=90)


# --- Bot commands ---

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"🎯 Steam Sniper\n\n"
        f"Твой chat_id: {chat_id}\n"
        f"Добавь его в .env → ALERT_CHAT_IDS\n\n"
        f"Команды:\n"
        f"/buy <название> | <цена в ₽> — алерт когда ниже цены\n"
        f"/sell <название> | <цена в ₽> — алерт когда выше цены\n"
        f"/list — показать watchlist\n"
        f"/remove <название> — удалить из watchlist\n"
        f"/check — проверить цены сейчас\n"
        f"/search <запрос> — найти предмет на lis-skins\n"
    )


async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.replace("/buy", "", 1).strip()
    if "|" not in text:
        await update.message.reply_text("Формат: /buy Название предмета | цена в ₽\nПример: /buy Kilowatt Case | 65")
        return

    name, price_str = text.rsplit("|", 1)
    name = name.strip()
    try:
        target_input = float(price_str.strip())
    except ValueError:
        await update.message.reply_text("Цена должна быть числом в рублях. Пример: /buy Kilowatt Case | 65")
        return

    # Fetch current price to record added_price (USD)
    added_price = 0.0
    try:
        prices = fetch_prices()
        item = prices.get(name.lower())
        if item:
            added_price = item["price"]
    except Exception:
        pass

    db.upsert_item(
        name=name,
        type_="buy",
        target_rub=target_input,
        added_price_usd=added_price,
        added_at=datetime.now().isoformat(),
        qty=1,
    )

    await update.message.reply_text(
        f"✅ BUY: {name}\n"
        f"Алерт когда цена <= {target_input:.0f}₽\n"
        f"Цена при добавлении: {_p(added_price)}"
    )


async def cmd_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.replace("/sell", "", 1).strip()
    if "|" not in text:
        await update.message.reply_text("Формат: /sell Название предмета | цена в ₽\nПример: /sell AWP | Asiimov (Field-Tested) | 2000")
        return

    name, price_str = text.rsplit("|", 1)
    name = name.strip()
    try:
        target_input = float(price_str.strip())
    except ValueError:
        await update.message.reply_text("Цена должна быть числом в рублях.")
        return

    # Fetch current price to record added_price (USD)
    added_price = 0.0
    try:
        prices = fetch_prices()
        item = prices.get(name.lower())
        if item:
            added_price = item["price"]
    except Exception:
        pass

    db.upsert_item(
        name=name,
        type_="sell",
        target_rub=target_input,
        added_price_usd=added_price,
        added_at=datetime.now().isoformat(),
        qty=1,
    )

    await update.message.reply_text(
        f"✅ SELL: {name}\n"
        f"Алерт когда цена >= {target_input:.0f}₽\n"
        f"Цена при добавлении: {_p(added_price)}"
    )


def _delta_str(current: float, added: float) -> str:
    """Format price change since added: +12.3% or -5.1%."""
    if added <= 0:
        return ""
    pct = ((current - added) / added) * 100
    arrow = "🟢+" if pct > 0 else "🔴" if pct < 0 else "⚪"
    return f" {arrow}{pct:.1f}%"


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    wl = db.get_watchlist()

    if not wl["buy"] and not wl["sell"]:
        await update.message.reply_text("Watchlist пуст. Добавь через /buy или /sell")
        return

    # Fetch current prices for delta
    try:
        prices = fetch_prices()
    except Exception:
        prices = {}

    lines = []
    if wl["buy"]:
        lines.append("📉 BUY (алерт когда ниже):")
        for e in wl["buy"]:
            added = e.get("added_price_usd", 0)
            item = prices.get(e["name"].lower())
            if item and added:
                delta = _delta_str(item["price"], added)
                lines.append(f"  • {e['name']} — сейчас {_p(item['price'])}{delta}\n    цель <={e['target_rub']:.0f}₽")
            else:
                lines.append(f"  • {e['name']} — цель <={e['target_rub']:.0f}₽")

    if wl["sell"]:
        lines.append("\n📈 SELL (алерт когда выше):")
        for e in wl["sell"]:
            added = e.get("added_price_usd", 0)
            item = prices.get(e["name"].lower())
            if item and added:
                delta = _delta_str(item["price"], added)
                lines.append(f"  • {e['name']} — сейчас {_p(item['price'])}{delta}\n    цель >={e['target_rub']:.0f}₽")
            else:
                lines.append(f"  • {e['name']} — цель >={e['target_rub']:.0f}₽")

    await update.message.reply_text("\n".join(lines))


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.message.text.replace("/remove", "", 1).strip()
    if not name:
        await update.message.reply_text("Формат: /remove Название предмета")
        return

    count = db.remove_item(name)
    if count == 0:
        await update.message.reply_text(f"Не нашёл '{name}' в watchlist")
    else:
        await update.message.reply_text(f"🗑 Удалено: {name}")


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.message.text.replace("/search", "", 1).strip()
    if not query:
        await update.message.reply_text("Формат: /search kilowatt case")
        return

    await update.message.reply_text("🔍 Ищу...")
    try:
        prices = fetch_prices()
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")
        return

    results = find_item(prices, query)
    if not results:
        await update.message.reply_text(f"Ничего не нашёл по '{query}'")
        return

    lines = [f"Результаты по '{query}':\n"]
    for item in results:
        lines.append(f"• {item['name']} — {_p(item['price'])} ({item.get('count', '?')} шт)")
    await update.message.reply_text("\n".join(lines))


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔄 Проверяю цены...")
    try:
        prices = fetch_prices()
    except Exception as e:
        await update.message.reply_text(f"Ошибка загрузки: {e}")
        return

    wl = db.get_watchlist()
    if not wl["buy"] and not wl["sell"]:
        await update.message.reply_text(f"Загружено {len(prices)} предметов, но watchlist пуст.")
        return

    alerts = check_alerts(prices)
    rate = _get_usd_rub()

    # Also show current prices for all tracked items
    lines = [f"📊 Загружено {len(prices)} предметов\n"]

    if wl["buy"]:
        lines.append("📉 BUY watchlist:")
        for e in wl["buy"]:
            item = prices.get(e["name"].lower())
            if item:
                status = "🟢" if item["price"] * rate <= e["target_rub"] else "⚪"
                added = e.get("added_price_usd", 0)
                delta = _delta_str(item["price"], added) if added else ""
                lines.append(f"  {status} {e['name']} — {_p(item['price'])}{delta}\n     цель <={e['target_rub']:.0f}₽")
            else:
                lines.append(f"  ❓ {e['name']} — не найден на lis-skins")

    if wl["sell"]:
        lines.append("\n📈 SELL watchlist:")
        for e in wl["sell"]:
            item = prices.get(e["name"].lower())
            if item:
                status = "🟢" if item["price"] * rate >= e["target_rub"] else "⚪"
                added = e.get("added_price_usd", 0)
                delta = _delta_str(item["price"], added) if added else ""
                lines.append(f"  {status} {e['name']} — {_p(item['price'])}{delta}\n     цель >={e['target_rub']:.0f}₽")
            else:
                lines.append(f"  ❓ {e['name']} — не найден на lis-skins")

    if alerts:
        lines.append(f"\n🔔 Сработало алертов: {len(alerts)}")
    else:
        lines.append("\n— Алертов нет")

    await update.message.reply_text("\n".join(lines))


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle lis-skins.com links — find item, show price, offer to add."""
    text = update.message.text or ""
    match = _LIS_SKINS_LINK_RE.search(text)
    if not match:
        return

    slug = match.group(1)
    await update.message.reply_text("🔍 Ищу предмет...")

    try:
        prices = fetch_prices()
    except Exception as e:
        await update.message.reply_text(f"Ошибка загрузки: {e}")
        return

    url_index = _build_url_index(prices)
    item = url_index.get(slug)

    if not item:
        # Try partial match on slug
        slug_words = slug.replace("-", " ")
        results = find_item(prices, slug_words)
        if results:
            item = results[0]

    if not item:
        await update.message.reply_text(f"Не нашёл предмет по ссылке. Попробуй /search")
        return

    name = item["name"]
    price = item["price"]
    count = item.get("count", "?")

    # Remember item for quick price reply
    context.user_data["pending_item"] = {"name": name, "price": price}

    await update.message.reply_text(
        f"🎯 {name}\n"
        f"💰 Цена: {_p(price)}\n"
        f"📦 В наличии: {count}\n\n"
        f"Напиши цену в рублях — бот сам определит:\n"
        f"  ниже текущей → алерт на покупку\n"
        f"  выше текущей → алерт на продажу"
    )


async def handle_price_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a plain number after a link — auto-detect buy/sell."""
    text = (update.message.text or "").strip()

    # Skip if it's a command or a link
    if text.startswith("/") or "lis-skins.com" in text:
        return

    # Try to parse as number
    try:
        target_input = float(text.replace(",", "."))
    except ValueError:
        return  # Not a number, ignore

    pending = context.user_data.get("pending_item")
    if not pending:
        return  # No item context

    name = pending["name"]
    current_price = pending["price"]  # USD
    context.user_data.pop("pending_item", None)

    # User inputs in RUB — store as RUB directly
    rate = _get_usd_rub()
    current_price_rub = current_price * rate

    now = datetime.now().isoformat()
    if target_input < current_price_rub:
        # Buy alert — target below current price
        db.upsert_item(
            name=name,
            type_="buy",
            target_rub=target_input,
            added_price_usd=current_price,
            added_at=now,
            qty=1,
        )
        await update.message.reply_text(
            f"📉 BUY: {name}\n"
            f"Алерт когда цена <= {target_input:.0f}₽\n"
            f"Сейчас: {_p(current_price)}"
        )
    elif target_input > current_price_rub:
        # Sell alert — target above current price
        db.upsert_item(
            name=name,
            type_="sell",
            target_rub=target_input,
            added_price_usd=current_price,
            added_at=now,
            qty=1,
        )
        await update.message.reply_text(
            f"📈 SELL: {name}\n"
            f"Алерт когда цена >= {target_input:.0f}₽\n"
            f"Сейчас: {_p(current_price)}"
        )
    else:
        await update.message.reply_text(
            f"Цена совпадает с текущей ({_p(current_price)}). "
            f"Укажи выше или ниже."
        )


def main() -> None:
    # Initialize SQLite database
    db.init_db()

    # Migrate JSON watchlist on first run
    json_path = DATA_DIR / "watchlist.json"
    if json_path.exists():
        rate = _get_usd_rub()
        count = db.migrate_json_to_sqlite(json_path, rate)
        if count > 0:
            logger.info(f"Migrated {count} items from watchlist.json")
            # Rename to .bak to prevent re-migration
            json_path.rename(json_path.with_suffix(".json.bak"))

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("buy", cmd_buy))
    app.add_handler(CommandHandler("sell", cmd_sell))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(_LIS_SKINS_LINK_RE), handle_link))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_reply))

    # Periodic price check
    app.job_queue.run_repeating(
        periodic_check,
        interval=CHECK_INTERVAL_S,
        first=10,  # first check 10 sec after start
    )

    # Periodic price snapshot (5 min)
    app.job_queue.run_repeating(
        periodic_snapshot,
        interval=300,  # 5 minutes
        first=30,
    )

    logger.info(f"Steam Sniper starting (check every {CHECK_INTERVAL_S // 3600}h)")
    app.run_polling()


if __name__ == "__main__":
    main()
