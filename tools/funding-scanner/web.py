from __future__ import annotations

import time

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from config import COINS
from db import get_connection, get_stats

app = FastAPI(title="Funding Scanner")

COINS_BY_CAP: list[str] = [
    "BTC", "ETH", "XRP", "SOL", "DOGE",
    "ADA", "TRX", "LINK", "SUI", "AVAX",
    "BCH", "DOT", "NEAR", "APT", "FIL",
    "OP", "ARB", "XLM", "TON", "HYPE", "PAXG",
]

PERIODS = [
    ("1d", 86400),
    ("2d", 86400 * 2),
    ("3d", 86400 * 3),
    ("7d", 86400 * 7),
    ("14d", 86400 * 14),
    ("21d", 86400 * 21),
    ("30d", 86400 * 30),
]

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Funding Scanner</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0b0e11; --surface: #12161c; --surface2: #181d25; --border: #1e2530;
    --text: #eaecef; --dim: #848e9c; --dim2: #5e6673;
    --green: #0ecb81; --green-bg: rgba(14,203,129,.08);
    --red: #f6465d; --red-bg: rgba(246,70,93,.08);
    --blue: #1e80ff; --yellow: #fcd535;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Inter', -apple-system, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }

  .header { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--border); }
  .header h1 { font-size: 16px; font-weight: 700; letter-spacing: .5px; display: flex; align-items: center; gap: 8px; }
  .header h1 .dot { width: 8px; height: 8px; border-radius: 50%%; background: var(--green); animation: pulse 2s infinite; }
  @keyframes pulse { 0%%,100%% { opacity: 1; } 50%% { opacity: .4; } }
  .header-right { display: flex; gap: 20px; font-size: 12px; color: var(--dim); font-family: 'JetBrains Mono', monospace; }
  .header-right .val { color: var(--text); font-weight: 500; }

  .filter-bar { display: flex; align-items: center; gap: 16px; padding: 12px 24px; border-bottom: 1px solid var(--border); }
  .filter-group { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--dim); cursor: pointer; }
  .filter-group svg { width: 14px; height: 14px; fill: var(--dim); }
  .search-box { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 6px 12px; color: var(--text); font-size: 13px; font-family: inherit; outline: none; width: 180px; margin-left: auto; }
  .search-box:focus { border-color: var(--blue); }
  .search-box::placeholder { color: var(--dim2); }

  .coin-selector { display: flex; flex-wrap: wrap; gap: 6px; padding: 12px 24px; border-bottom: 1px solid var(--border); }
  .coin-chip { background: var(--surface); border: 1px solid var(--border); color: var(--dim); padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all .15s; font-family: inherit; display: inline-flex; align-items: center; gap: 6px; }
  .coin-chip:hover { border-color: var(--dim2); color: var(--text); }
  .coin-chip.active { background: var(--blue); border-color: var(--blue); color: #fff; }
  .coin-chip img { width: 16px; height: 16px; border-radius: 50%%; }

  .selected-coin { display: flex; align-items: center; gap: 10px; padding: 10px 24px; font-size: 13px; border-bottom: 1px solid var(--border); }
  .selected-coin img { width: 24px; height: 24px; border-radius: 50%%; }
  .selected-coin .name { font-weight: 700; font-size: 16px; }
  .selected-coin .fullname { color: var(--dim); font-size: 13px; }
  .selected-coin .spread-info { margin-left: 16px; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--dim); }
  .selected-coin .spread-val { font-weight: 600; }
  .spread-high { color: var(--green); }
  .spread-med { color: var(--yellow); }
  .spread-low { color: var(--dim); }

  .table-wrap { overflow-x: auto; }
  table { width: 100%%; border-collapse: collapse; }
  thead th { position: sticky; top: 0; background: var(--surface); padding: 12px 16px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--dim); border-bottom: 1px solid var(--border); white-space: nowrap; letter-spacing: .5px; }
  thead th.right { text-align: right; }
  thead th.sortable { cursor: pointer; user-select: none; }
  thead th.sortable:hover { color: var(--text); }
  thead th.sorted { color: var(--blue); }
  thead th .arrow { font-size: 10px; margin-left: 3px; }
  tbody tr { border-bottom: 1px solid var(--border); transition: background .12s; }
  tbody tr:hover { background: var(--surface2); }
  td { padding: 12px 16px; white-space: nowrap; }
  td.right { text-align: right; }

  .ex-cell { display: flex; align-items: center; gap: 10px; }
  .ex-logo { width: 24px; height: 24px; border-radius: 50%%; flex-shrink: 0; }
  .ex-fallback { width: 24px; height: 24px; border-radius: 50%%; align-items: center; justify-content: center; font-size: 9px; font-weight: 700; flex-shrink: 0; background: var(--surface2); border: 1px solid var(--border); }
  .ex-fallback:not([hidden]) { display: flex; }
  .ex-fallback.cex { color: var(--yellow); border-color: rgba(252,213,53,.2); }
  .ex-fallback.dex { color: var(--blue); border-color: rgba(30,128,255,.2); }
  .ex-badge { background: var(--surface2); border: 1px solid var(--border); padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; letter-spacing: .3px; }

  .rate-cell { font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 500; }
  .rate-pos { color: var(--green); }
  .rate-neg { color: var(--red); }
  .rate-zero { color: var(--dim2); }

  .footer { padding: 12px 24px; border-top: 1px solid var(--border); color: var(--dim2); font-size: 11px; font-family: 'JetBrains Mono', monospace; display: flex; justify-content: space-between; align-items: center; }
  .pagination { display: flex; align-items: center; gap: 8px; }
  .page-btn { background: var(--surface); border: 1px solid var(--border); color: var(--dim); padding: 4px 10px; border-radius: 4px; font-size: 12px; cursor: pointer; }
  .page-btn:hover { color: var(--text); border-color: var(--dim2); }
  .page-num { font-size: 12px; color: var(--text); font-weight: 600; min-width: 20px; text-align: center; }

  .no-data { text-align: center; padding: 60px 24px; color: var(--dim2); font-size: 14px; }
</style>
</head>
<body>

<div class="header">
  <h1><span class="dot"></span>FUNDING SCANNER</h1>
  <div class="header-right" id="stats"></div>
</div>

<div class="filter-bar">
  <div class="filter-group">
    <svg viewBox="0 0 24 24"><path d="M10 18h4v-2h-4v2zM3 6v2h18V6H3zm3 7h12v-2H6v2z"/></svg>
    <span>Exchanges: All</span>
  </div>
  <div class="filter-group">
    <svg viewBox="0 0 24 24"><path d="M3 18h6v-2H3v2zM3 6v2h18V6H3zm0 7h12v-2H3v2z"/></svg>
    <span>Filter: All</span>
  </div>
  <input class="search-box" id="search" type="text" placeholder="Search coin...">
</div>

<div class="coin-selector" id="coins"></div>
<div class="selected-coin" id="selected" style="display:none"></div>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th style="width:220px">Exchange</th>
        <th class="right sortable" data-col="0">1d<span class="arrow"></span></th>
        <th class="right sortable" data-col="1">2d<span class="arrow"></span></th>
        <th class="right sortable" data-col="2">3d<span class="arrow"></span></th>
        <th class="right sortable" data-col="3">7d<span class="arrow"></span></th>
        <th class="right sortable" data-col="4">14d<span class="arrow"></span></th>
        <th class="right sortable" data-col="5">21d<span class="arrow"></span></th>
        <th class="right sortable" data-col="6">30d<span class="arrow"></span></th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
</div>

<div class="footer">
  <span id="footer-info"></span>
  <div class="pagination">
    <span class="page-btn" id="prev-page">&lt;</span>
    <span class="page-num" id="page-num">1</span>
    <span class="page-btn" id="next-page">&gt;</span>
  </div>
</div>

<script>
const COINS = %s;
const CEX = ['BINANCE','BYBIT','OKX','KUCOIN','BITGET','GATE','MEXC'];

// CoinMarketCap coin IDs
const CMC_COIN = {
  BTC:1, ETH:1027, XRP:52, SOL:5426, DOGE:74, ADA:2010, TRX:1958,
  LINK:1975, SUI:20947, AVAX:5805, BCH:1831, DOT:6636, NEAR:6535,
  APT:21794, FIL:2280, OP:11840, ARB:11841, XLM:512, TON:11419, HYPE:32196,
  PAXG:4705
};
// CoinMarketCap exchange IDs (CEX)
const CMC_EX = {
  BINANCE:270, BYBIT:521, OKX:294, KUCOIN:311, BITGET:513, GATE:302, MEXC:544
};
// Direct logo URLs for DEX
const DEX_LOGOS = {
  HYPERLIQUID: 'https://app.hyperliquid.xyz/favicon-32x32.png',
  PARADEX: 'https://app.paradex.trade/favicon.png',
  EDGEX: 'https://www.edgex.exchange/logo.svg',
  PACIFICA: 'https://app.pacifica.fi/favicon.ico',
  EXTENDED: 'https://app.extended.exchange/assets/logo/extended-long.svg'
};
// Full coin names
const COIN_NAMES = {
  BTC:'Bitcoin', ETH:'Ethereum', XRP:'Ripple', SOL:'Solana', DOGE:'Dogecoin',
  ADA:'Cardano', TRX:'Tron', LINK:'Chainlink', SUI:'Sui', AVAX:'Avalanche',
  BCH:'Bitcoin Cash', DOT:'Polkadot', NEAR:'NEAR Protocol', APT:'Aptos',
  FIL:'Filecoin', OP:'Optimism', ARB:'Arbitrum', XLM:'Stellar', TON:'Toncoin',
  HYPE:'Hyperliquid', PAXG:'Pax Gold'
};

function coinImg(symbol, size) {
  const id = CMC_COIN[symbol];
  if (!id) return '';
  return '<img src="https://s2.coinmarketcap.com/static/img/coins/64x64/' + id + '.png" ' +
    'width="' + size + '" height="' + size + '" style="border-radius:50%%" ' +
    'onerror="this.hidden=1" alt="">';
}

function exIcon(name) {
  const cmcId = CMC_EX[name];
  const dexUrl = DEX_LOGOS[name];
  if (cmcId) {
    return '<img class="ex-logo" src="https://s2.coinmarketcap.com/static/img/exchanges/64x64/' + cmcId + '.png" ' +
      'onerror="this.hidden=1" alt="">';
  }
  if (dexUrl) {
    return '<img class="ex-logo" src="' + dexUrl + '" onerror="this.hidden=1" alt="">';
  }
  const isCex = CEX.includes(name);
  return '<div class="ex-fallback ' + (isCex ? 'cex' : 'dex') + '">' + name.slice(0,2) + '</div>';
}

let data = null;
let selectedCoin = COINS[0];
let sortCol = 0;
let sortAsc = true;

function renderCoins() {
  const el = document.getElementById('coins');
  const search = document.getElementById('search').value.toUpperCase();
  const filtered = search ? COINS.filter(c => c.includes(search)) : COINS;
  el.innerHTML = filtered.map(c =>
    '<button class="coin-chip' + (c === selectedCoin ? ' active' : '') + '" data-coin="' + c + '">' +
    coinImg(c, 16) + c + '</button>'
  ).join('');
  el.querySelectorAll('.coin-chip').forEach(btn => {
    btn.addEventListener('click', () => { selectedCoin = btn.dataset.coin; render(); });
  });
}

document.getElementById('search').addEventListener('input', renderCoins);

document.querySelectorAll('th.sortable').forEach(th => {
  th.addEventListener('click', () => {
    const col = parseInt(th.dataset.col);
    if (sortCol === col) sortAsc = !sortAsc;
    else { sortCol = col; sortAsc = true; }
    render();
  });
});

function render() {
  if (!data) return;
  renderCoins();

  const selEl = document.getElementById('selected');
  const coinSpread = data.spreads.find(s => s.coin === selectedCoin);
  if (coinSpread) {
    const cls = coinSpread.spread > 30 ? 'spread-high' : coinSpread.spread > 15 ? 'spread-med' : 'spread-low';
    selEl.style.display = 'flex';
    selEl.innerHTML =
      coinImg(selectedCoin, 24) +
      '<span class="name">' + selectedCoin + '</span>' +
      '<span class="fullname">' + (COIN_NAMES[selectedCoin] || '') + '</span>' +
      '<span class="spread-info">Spread: <span class="spread-val ' + cls + '">' + coinSpread.spread.toFixed(1) + '%%/yr</span>' +
      ' | Long: ' + coinSpread.long_exchange + ' (' + coinSpread.long_rate.toFixed(1) + '%%)' +
      ' | Short: ' + coinSpread.short_exchange + ' (+' + coinSpread.short_rate.toFixed(1) + '%%)</span>';
  } else {
    selEl.style.display = 'none';
  }

  document.querySelectorAll('th.sortable').forEach(th => {
    const col = parseInt(th.dataset.col);
    const arrow = th.querySelector('.arrow');
    th.classList.toggle('sorted', col === sortCol);
    arrow.textContent = col === sortCol ? (sortAsc ? ' \\u2191' : ' \\u2193') : '';
  });

  const coinRates = data.exchange_rates[selectedCoin] || {};
  let exchanges = Object.keys(coinRates);
  exchanges.sort((a, b) => {
    const va = coinRates[a][sortCol];
    const vb = coinRates[b][sortCol];
    if (va === null && vb === null) return 0;
    if (va === null) return 1;
    if (vb === null) return -1;
    return sortAsc ? va - vb : vb - va;
  });

  const tbody = document.getElementById('tbody');
  if (exchanges.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="no-data">No data for ' + selectedCoin + '</td></tr>';
    return;
  }

  tbody.innerHTML = exchanges.map(ex => {
    const vals = coinRates[ex];
    const cells = vals.map(v => {
      if (v === null) return '<td class="right rate-cell rate-zero">-</td>';
      const cls = v > 0 ? 'rate-pos' : v < 0 ? 'rate-neg' : 'rate-zero';
      const sign = v > 0 ? '+' : '';
      return '<td class="right rate-cell ' + cls + '">' + sign + v.toFixed(1) + '%%</td>';
    }).join('');
    return '<tr>' +
      '<td><div class="ex-cell">' +
        exIcon(ex) +
        '<span class="ex-badge">' + ex + '</span>' +
      '</div></td>' +
      cells +
    '</tr>';
  }).join('');
}

async function load() {
  const r = await fetch('/api/data');
  data = await r.json();

  document.getElementById('stats').innerHTML =
    '<span>Exchanges: <span class="val">' + data.active_exchanges + '</span></span>' +
    '<span>Snapshots: <span class="val">' + data.snapshots + '</span></span>' +
    '<span>Last: <span class="val">' + data.last_scan_ago + '</span></span>' +
    '<span>Scan: <span class="val">every 5m</span></span>';

  document.getElementById('footer-info').textContent =
    data.total_rates + ' rates total';

  render();
}

load();
setInterval(load, 10000);
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    import json
    return HTML_TEMPLATE % json.dumps(COINS_BY_CAP)


@app.get("/api/data")
async def api_data() -> dict:  # type: ignore[type-arg]
    conn = get_connection()
    try:
        stats = get_stats()

        row = conn.execute("SELECT MAX(ts) FROM rates").fetchone()
        last_ts = row[0] if row and row[0] else 0
        ago = int(time.time()) - last_ts
        if ago < 60:
            ago_str = f"{ago}s ago"
        elif ago < 3600:
            ago_str = f"{ago // 60}m ago"
        else:
            ago_str = f"{ago // 3600}h {(ago % 3600) // 60}m ago"

        ex_row = conn.execute(
            "SELECT COUNT(DISTINCT exchange) FROM rates WHERE ts = (SELECT MAX(ts) FROM rates)"
        ).fetchone()
        active_ex = ex_row[0] if ex_row else 0

        # Latest spreads
        latest_spreads = conn.execute("""
            SELECT coin, long_exchange, short_exchange, long_rate, short_rate, spread
            FROM spreads WHERE ts = (SELECT MAX(ts) FROM spreads)
            ORDER BY spread DESC
        """).fetchall()
        spreads_data = [{
            "coin": r[0], "long_exchange": r[1], "short_exchange": r[2],
            "long_rate": r[3], "short_rate": r[4], "spread": r[5],
        } for r in latest_spreads]

        # Exchange rates per coin per period — simple average of settled rates.
        # Settled rates come from backfill (exact settlement timestamps);
        # predicted rates from 5-min scans have non-zero offsets and are excluded.
        now = int(time.time())
        exchange_rates: dict[str, dict[str, list[float | None]]] = {}

        for coin in COINS:
            exchange_rates[coin] = {}
            rows = conn.execute("""
                SELECT exchange, ts, rate_ann, interval_h FROM rates
                WHERE coin = ? AND ts >= ?
                ORDER BY exchange, ts
            """, (coin, now - 86400 * 30)).fetchall()

            by_ex: dict[str, list[tuple[int, float, int]]] = {}
            for r in rows:
                by_ex.setdefault(r[0], []).append((r[1], r[2], r[3]))

            for ex, points in by_ex.items():
                # Determine settlement interval (most common in data)
                interval_counts: dict[int, int] = {}
                for _, _, ih in points:
                    interval_counts[ih] = interval_counts.get(ih, 0) + 1
                interval_h = max(interval_counts, key=lambda k: interval_counts[k])
                bucket_secs = interval_h * 3600

                # Filter to settled rates only: backfill timestamps land
                # on exact hour boundaries (offset 0s from any :00:00);
                # scan entries arrive at arbitrary times (:55:13, :40:30, etc).
                # Use ts % 3600 (not bucket_secs) because exchanges settle at
                # different offsets (Binance 0/8/16, KuCoin 4/12/20 UTC).
                settled = [(ts, rate) for ts, rate, _ in points
                           if ts % 3600 < 10]

                # Include the latest predicted rate for the current unsettled
                # period — most aggregators mix settled + current predicted.
                latest = max(points, key=lambda p: p[0])
                if latest[0] % 3600 >= 10:  # it's a scanner (predicted) rate
                    settled.append((latest[0], latest[1]))

                # Fallback to all points if no settled data found
                use_pts = settled if settled else [(ts, rate) for ts, rate, _ in points]

                avgs: list[float | None] = []
                for _, secs in PERIODS:
                    cutoff = now - secs
                    vals = [rate for ts, rate in use_pts if ts >= cutoff]
                    if vals:
                        avgs.append(round(sum(vals) / len(vals), 1))
                    else:
                        avgs.append(None)
                exchange_rates[coin][ex] = avgs

        return {
            "active_exchanges": active_ex,
            "total_rates": stats["rates"],
            "snapshots": stats["snapshots"],
            "last_scan_ago": ago_str,
            "spreads": spreads_data,
            "exchange_rates": exchange_rates,
        }
    finally:
        conn.close()
