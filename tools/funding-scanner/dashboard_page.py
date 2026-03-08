from __future__ import annotations

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Funding Scanner</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #091019;
    --surface: #101823;
    --surface2: #16212e;
    --border: #243246;
    --text: #eaf1f7;
    --dim: #8ea0b5;
    --dim2: #607287;
    --green: #35d07f;
    --green-bg: rgba(53, 208, 127, .12);
    --red: #ff6b6b;
    --red-bg: rgba(255, 107, 107, .10);
    --yellow: #ffc857;
    --yellow-bg: rgba(255, 200, 87, .12);
    --blue: #56a7ff;
    --blue-bg: rgba(86, 167, 255, .12);
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: 'Inter', sans-serif;
    color: var(--text);
    background:
      radial-gradient(circle at top right, rgba(86, 167, 255, .14), transparent 24%),
      radial-gradient(circle at top left, rgba(53, 208, 127, .10), transparent 22%),
      linear-gradient(180deg, #081018 0%, #091019 100%);
    min-height: 100vh;
  }
  .page {
    max-width: 1440px;
    margin: 0 auto;
    padding: 24px;
  }
  .hero {
    display: grid;
    gap: 18px;
    grid-template-columns: minmax(0, 1.6fr) minmax(320px, .9fr);
    margin-bottom: 20px;
  }
  .hero-card, .summary-card, .panel, .table-card {
    background: linear-gradient(180deg, rgba(16,24,35,.98), rgba(12,19,28,.96));
    border: 1px solid var(--border);
    border-radius: 18px;
    box-shadow: 0 18px 80px rgba(0, 0, 0, .22);
  }
  .hero-card {
    padding: 22px 24px;
  }
  .eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: var(--dim);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    margin-bottom: 14px;
  }
  .eyebrow .dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 18px rgba(53,208,127,.45);
  }
  .hero-title {
    font-size: clamp(28px, 4vw, 46px);
    line-height: .98;
    font-weight: 800;
    letter-spacing: -.04em;
    margin: 0 0 10px;
  }
  .hero-subtitle {
    color: var(--dim);
    max-width: 62ch;
    line-height: 1.45;
    font-size: 14px;
  }
  .hero-meta {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-top: 22px;
  }
  .metric {
    background: rgba(22,33,46,.76);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px 16px;
  }
  .metric-label {
    color: var(--dim2);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .12em;
    margin-bottom: 6px;
  }
  .metric-value {
    font-size: 18px;
    font-weight: 700;
  }
  .summary-card {
    padding: 22px 24px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .summary-card h2, .section-header h2 {
    margin: 0;
    font-size: 18px;
    letter-spacing: -.03em;
  }
  .summary-note {
    color: var(--dim);
    font-size: 13px;
    line-height: 1.45;
  }
  .spread-big {
    font-family: 'JetBrains Mono', monospace;
    font-size: 34px;
    font-weight: 700;
    letter-spacing: -.03em;
  }
  .pill-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border-radius: 999px;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 700;
    background: rgba(22,33,46,.82);
    border: 1px solid var(--border);
    color: var(--text);
  }
  .panel {
    padding: 18px;
  }
  .section-header {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
  }
  .section-copy {
    color: var(--dim);
    font-size: 13px;
    line-height: 1.4;
  }
  .toolbar {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
    margin-bottom: 14px;
  }
  .search-box {
    margin-left: auto;
    min-width: 220px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 12px;
    color: var(--text);
    padding: 10px 12px;
    font: inherit;
    outline: none;
  }
  .search-box:focus {
    border-color: var(--blue);
  }
  .toggle {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 6px;
  }
  .toggle button, .coin-chip {
    border: 0;
    background: transparent;
    color: var(--dim);
    font: inherit;
    cursor: pointer;
  }
  .toggle button {
    padding: 8px 12px;
    border-radius: 9px;
    font-size: 12px;
    font-weight: 700;
  }
  .toggle button.active {
    background: var(--blue);
    color: #fff;
  }
  .coin-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .coin-chip {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 8px 12px;
    color: var(--dim);
    font-size: 12px;
    font-weight: 700;
  }
  .coin-chip.active {
    background: var(--green-bg);
    border-color: rgba(53,208,127,.35);
    color: var(--green);
  }
  .two-col {
    display: grid;
    gap: 18px;
    grid-template-columns: minmax(0, 1.2fr) minmax(300px, .8fr);
    margin-bottom: 18px;
  }
  .table-card {
    overflow: hidden;
  }
  .table-wrap {
    overflow-x: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th, td {
    padding: 14px 16px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    text-align: left;
  }
  th {
    background: rgba(18, 29, 41, .98);
    color: var(--dim);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .12em;
    position: sticky;
    top: 0;
    z-index: 1;
  }
  td {
    font-size: 13px;
  }
  tr:hover td {
    background: rgba(22,33,46,.35);
  }
  .mono {
    font-family: 'JetBrains Mono', monospace;
  }
  .value-pos { color: var(--green); }
  .value-neg { color: var(--red); }
  .muted { color: var(--dim); }
  .split-line {
    display: grid;
    gap: 6px;
  }
  .split-line strong {
    font-size: 12px;
  }
  .empty {
    color: var(--dim2);
    padding: 32px 18px;
    text-align: center;
  }
  @media (max-width: 980px) {
    .hero, .two-col {
      grid-template-columns: 1fr;
    }
    .hero-meta {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .search-box {
      min-width: 100%;
      margin-left: 0;
    }
  }
</style>
</head>
<body>
<div class="page">
  <section class="hero">
    <div class="hero-card">
      <div class="eyebrow"><span class="dot"></span>Funding Scanner</div>
      <h1 class="hero-title">Funding arbitrage, split cleanly into live and closed history.</h1>
      <div class="hero-subtitle">Top block = current funding, next payment, mark price. Historical APR below is cut at the latest UTC midnight, so current predictions never pollute completed windows.</div>
      <div class="hero-meta" id="hero-meta"></div>
    </div>
    <aside class="summary-card">
      <h2 id="summary-title">Best funding pair</h2>
      <div class="summary-note" id="summary-note">Choose a ticker and wait for data.</div>
      <div class="spread-big mono" id="summary-spread">--</div>
      <div class="pill-row" id="summary-pills"></div>
    </aside>
  </section>
  <section class="panel">
    <div class="section-header">
      <div>
        <h2>Context</h2>
        <div class="section-copy" id="history-window-copy">Historical data is loading.</div>
      </div>
    </div>
    <div class="toolbar">
      <div class="coin-strip" id="coin-strip"></div>
      <input class="search-box" id="search" type="text" placeholder="Search ticker...">
    </div>
  </section>
  <section class="two-col">
    <div class="panel">
      <div class="section-header">
        <div>
          <h2>Current Funding</h2>
          <div class="section-copy">Selected ticker, sorted from most negative to most positive. Live APR, per-payment rate, cadence, and countdown to the next funding.</div>
        </div>
      </div>
      <div class="table-card">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Exchange</th>
                <th>Price</th>
                <th>Funding</th>
                <th>Payments</th>
                <th>Next funding</th>
              </tr>
            </thead>
            <tbody id="live-tbody"></tbody>
          </table>
        </div>
      </div>
    </div>
    <div class="panel">
      <div class="section-header">
        <div>
          <h2>Best Pair</h2>
          <div class="section-copy">Best live funding pair inside the selected ticker based on the current snapshot.</div>
        </div>
      </div>
      <div id="pair-card-body" class="split-line"></div>
    </div>
  </section>
  <section class="panel">
    <div class="section-header">
      <div>
        <h2>Historical APR</h2>
        <div class="section-copy">Closed historical windows only. No current predicted rate mixed in.</div>
      </div>
    </div>
    <div class="table-card">
      <div class="table-wrap">
        <table>
          <thead id="historical-head"></thead>
          <tbody id="historical-tbody"></tbody>
        </table>
      </div>
    </div>
  </section>
  <section class="panel">
    <div class="section-header">
      <div>
        <h2>Pair Scanner</h2>
        <div class="section-copy">Scanner of live funding pairs. Sort by funding edge or by price spread.</div>
      </div>
    </div>
    <div class="toolbar">
      <div class="toggle" id="pair-sort">
        <button data-sort="funding" class="active">Funding</button>
        <button data-sort="price">Price</button>
      </div>
      <div class="toggle" id="pair-scope">
        <button data-scope="all" class="active">All pairs</button>
        <button data-scope="selected">Selected only</button>
      </div>
    </div>
    <div class="table-card">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Long / Short</th>
              <th>Price</th>
              <th>Funding, %/yr</th>
              <th>Price spread</th>
              <th>Funding spread</th>
              <th>Break-even</th>
              <th>Next payment</th>
            </tr>
          </thead>
          <tbody id="pairs-tbody"></tbody>
        </table>
      </div>
    </div>
  </section>
</div>
<script>
const COINS = __COINS_JSON__;
const STATE = {
  selectedCoin: COINS[0],
  search: '',
  pairSort: 'funding',
  pairScope: 'all',
  historical: null,
  live: null,
};
const CMC_COIN={BTC:1,ETH:1027,XRP:52,SOL:5426,DOGE:74,ADA:2010,TRX:1958,LINK:1975,SUI:20947,AVAX:5805,BCH:1831,DOT:6636,NEAR:6535,APT:21794,FIL:2280,OP:11840,ARB:11841,XLM:512,TON:11419,HYPE:32196,PAXG:4705};
const CMC_EX={BINANCE:270,BYBIT:521,OKX:294,KUCOIN:311,BITGET:513,GATE:302,MEXC:544};
const DEX_LOGOS={HYPERLIQUID:'https://app.hyperliquid.xyz/favicon-32x32.png',PARADEX:'https://app.paradex.trade/favicon.png',EDGEX:'https://www.edgex.exchange/logo.svg',PACIFICA:'https://app.pacifica.fi/favicon.ico',EXTENDED:'https://app.extended.exchange/assets/logo/extended-long.svg'};
function coinIcon(symbol,size=16){const id=CMC_COIN[symbol]; return id?`<img src="https://s2.coinmarketcap.com/static/img/coins/64x64/${id}.png" width="${size}" height="${size}" style="border-radius:50%;vertical-align:-3px;margin-right:8px" onerror="this.hidden=1" alt="">`:'';}
function exIcon(name,size=18){const url=CMC_EX[name]?`https://s2.coinmarketcap.com/static/img/exchanges/64x64/${CMC_EX[name]}.png`:DEX_LOGOS[name]; return url?`<img src="${url}" width="${size}" height="${size}" style="border-radius:50%;vertical-align:-4px;margin-right:8px;object-fit:cover;background:#101823" onerror="this.hidden=1" alt="">`:'';}
function pctClass(value) {
  if (value == null) return 'muted';
  if (value > 0) return 'value-pos';
  if (value < 0) return 'value-neg';
  return 'muted';
}
function fmtPct(value, digits = 1) {
  if (value == null) return '--';
  const sign = value > 0 ? '+' : '';
  return sign + value.toFixed(digits) + '%';
}

function fmtPrice(value) {
  if (value == null) return '--';
  const n = Number(value);
  if (!Number.isFinite(n)) return '--';
  if (Math.abs(n) >= 1000) return n.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  if (Math.abs(n) >= 100) return n.toLocaleString('en-US', { maximumFractionDigits: 2 });
  if (Math.abs(n) >= 1) return n.toLocaleString('en-US', { maximumFractionDigits: 4 });
  return n.toLocaleString('en-US', { maximumFractionDigits: 6 });
}

function fmtCountdown(ts) {
  if (!ts) return '--';
  let delta = Math.max(0, Math.floor((ts - Date.now()) / 1000));
  const hours = Math.floor(delta / 3600);
  delta -= hours * 3600;
  const mins = Math.floor(delta / 60);
  const secs = delta % 60;
  return [hours, mins, secs].map(v => String(v).padStart(2, '0')).join(':');
}

const selectedCoinLive = () => STATE.live ? STATE.live.coins.find(item => item.ticker === STATE.selectedCoin) || null : null;
const selectedCoinHistorical = () => STATE.historical ? STATE.historical.coins.find(item => item.ticker === STATE.selectedCoin) || null : null;
const setActiveButtons = (containerId, attr, value) => document.querySelectorAll(`#${containerId} button`).forEach(btn => btn.classList.toggle('active', btn.dataset[attr] === value));
function renderHero() {
  const meta = document.getElementById('hero-meta');
  const live = STATE.live;
  const hist = STATE.historical;
  const windowDate = hist ? new Date(hist.window_until_ms).toISOString().slice(0, 10) : '--';
  meta.innerHTML = [
    ['Exchanges', live ? live.active_exchanges : '--'],
    ['Snapshots', live ? live.snapshots : '--'],
    ['Live Scan', live ? live.scan_interval : '--'],
    ['History Cutoff', windowDate + ' UTC'],
  ].map(([label, value]) =>
    '<div class="metric"><div class="metric-label">' + label + '</div><div class="metric-value mono">' + value + '</div></div>'
  ).join('');

  const pair = selectedCoinLive()?.best_pair || null;
  document.getElementById('summary-title').textContent = pair ? `${pair.ticker} funding edge` : 'Best funding pair';
  document.getElementById('summary-note').textContent = pair
    ? `${pair.long_exchange} -> ${pair.short_exchange}. Live funding edge stays separate from historical APR.`
    : 'Choose a ticker and wait for data.';
  document.getElementById('summary-spread').textContent = pair ? fmtPct(pair.funding_spread_apr_pct, 2) : '--';
  document.getElementById('summary-pills').innerHTML = pair ? [
    `<span class="pill">Price spread: ${fmtPct(pair.price_spread_pct, 3)}</span>`,
    `<span class="pill">Long: ${pair.long_exchange}</span>`,
    `<span class="pill">Short: ${pair.short_exchange}</span>`,
    `<span class="pill">Break-even: ${pair.break_even_days != null ? pair.break_even_days + 'd' : '--'}</span>`,
  ].join('') : '';
}

function renderCoinStrip() {
  const filtered = STATE.search
    ? COINS.filter(coin => coin.includes(STATE.search.toUpperCase()))
    : COINS;
  const strip = document.getElementById('coin-strip');
  strip.innerHTML = filtered.map(coin => `<button class="coin-chip ${coin === STATE.selectedCoin ? 'active' : ''}" data-coin="${coin}">${coinIcon(coin)}${coin}</button>`).join('');
  strip.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', () => {
      STATE.selectedCoin = btn.dataset.coin;
      renderAll();
    });
  });
}

function renderHistoryWindowCopy() {
  const hist = STATE.historical;
  if (!hist) {
    document.getElementById('history-window-copy').textContent = 'Historical data is loading.';
    return;
  }
  const windowDate = new Date(hist.window_until_ms).toISOString().slice(0, 10);
  document.getElementById('history-window-copy').textContent =
    `Historical APR uses only closed days through ${windowDate} UTC. Live snapshot refreshes separately every 10 seconds from the local database.`;
}

function renderCurrentFunding() {
  const tbody = document.getElementById('live-tbody');
  const coin = selectedCoinLive();
  if (!coin) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty">No live data for this ticker.</td></tr>';
    return;
  }
  const pair = coin.best_pair || null;
  tbody.innerHTML = coin.exchanges.map(row => `
    <tr>
      <td>${exIcon(row.exchange)}<strong>${row.exchange}</strong>${pair && row.exchange === pair.long_exchange ? ' <span class="pill">LONG</span>' : ''}${pair && row.exchange === pair.short_exchange ? ' <span class="pill">SHORT</span>' : ''}<div class="muted">${row.exchange_type} | ${row.interval_h}h cadence</div></td>
      <td class="mono">${fmtPrice(row.price)}</td>
      <td class="mono"><div class="${pctClass(row.funding_apr_pct)}">${fmtPct(row.funding_apr_pct, 2)}</div><div class="muted">${fmtPct(row.funding_period_pct, 4)} / payment</div></td>
      <td class="mono">${row.payments}x/day</td>
      <td class="mono"><div>${fmtCountdown(row.next_funding_ts)}</div><div class="muted">${new Date(row.next_funding_ts).toISOString().slice(11, 16)} UTC</div></td>
    </tr>
  `).join('');
}

function renderPairCard() {
  const body = document.getElementById('pair-card-body');
  const pair = selectedCoinLive()?.best_pair || null;
  if (!pair) {
    body.innerHTML = '<div class="empty">No funding pair for this ticker.</div>';
    return;
  }
  body.innerHTML = `
    <div>${coinIcon(pair.ticker, 18)}<strong>${pair.ticker}</strong> | long <span class="value-neg">${pair.long_exchange}</span> | short <span class="value-pos">${pair.short_exchange}</span></div>
    <div class="mono">Funding spread: <span class="${pctClass(pair.funding_spread_apr_pct)}">${fmtPct(pair.funding_spread_apr_pct, 2)}</span></div>
    <div class="mono">Price spread: <span class="${pctClass(pair.price_spread_pct)}">${fmtPct(pair.price_spread_pct, 3)}</span> (${pair.price_spread_abs != null ? pair.price_spread_abs : '--'})</div>
    <div class="mono">Long price / short price: ${fmtPrice(pair.long_price)} / ${fmtPrice(pair.short_price)}</div>
    <div class="mono">Cadence: ${pair.long_payments}x/day vs ${pair.short_payments}x/day</div>
    <div class="mono">Next funding: ${fmtCountdown(pair.long_next_funding_ts)} / ${fmtCountdown(pair.short_next_funding_ts)}</div>
    <div class="mono">Break-even: ${pair.break_even_days != null ? pair.break_even_days + ' days' : '--'}</div>
  `;
}

function renderHistorical() {
  const hist = STATE.historical;
  const coin = selectedCoinHistorical();
  const head = document.getElementById('historical-head');
  const body = document.getElementById('historical-tbody');
  if (!hist) {
    head.innerHTML = '';
    body.innerHTML = '<tr><td class="empty">Historical data is loading.</td></tr>';
    return;
  }
  head.innerHTML = '<tr><th>Exchange</th>' + hist.periods.map(label => `<th>${label}</th>`).join('') + '</tr>';
  if (!coin) {
    body.innerHTML = `<tr><td colspan="${hist.periods.length + 1}" class="empty">No historical data for this ticker.</td></tr>`;
    return;
  }
  body.innerHTML = coin.exchanges.map(row => `
    <tr>
      <td>${exIcon(row.exchange_code.split('-')[0], 16)}<strong>${row.exchange_code}</strong></td>
      ${row.apr.map(value => `<td class="mono ${pctClass(value)}">${fmtPct(value, 1)}</td>`).join('')}
    </tr>
  `).join('');
}

function renderPairs() {
  const tbody = document.getElementById('pairs-tbody');
  if (!STATE.live) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty">Live pairs are loading.</td></tr>';
    return;
  }

  let pairs = STATE.live.pairs.slice();
  if (STATE.pairScope === 'selected') {
    pairs = pairs.filter(pair => pair.ticker === STATE.selectedCoin);
  }
  pairs.sort((a, b) => {
    if (STATE.pairSort === 'price') {
      return (b.price_spread_pct ?? -999999) - (a.price_spread_pct ?? -999999);
    }
    return (b.funding_spread_apr_pct ?? -999999) - (a.funding_spread_apr_pct ?? -999999);
  });
  if (!pairs.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty">No pairs match the current filter.</td></tr>';
    return;
  }

  tbody.innerHTML = pairs.map(pair => `
    <tr>
      <td>${coinIcon(pair.ticker, 18)}<strong>${pair.ticker}</strong></td>
      <td>
        <div class="split-line">
          <span><strong>Long:</strong> ${exIcon(pair.long_exchange, 14)}${pair.long_exchange}</span>
          <span><strong>Short:</strong> ${exIcon(pair.short_exchange, 14)}${pair.short_exchange}</span>
        </div>
      </td>
      <td class="mono">
        <div class="split-line">
          <span>${fmtPrice(pair.long_price)}</span>
          <span>${fmtPrice(pair.short_price)}</span>
        </div>
      </td>
      <td class="mono">
        <div class="split-line">
          <span class="${pctClass(pair.long_funding_apr_pct)}">${fmtPct(pair.long_funding_apr_pct, 2)}</span>
          <span class="${pctClass(pair.short_funding_apr_pct)}">${fmtPct(pair.short_funding_apr_pct, 2)}</span>
        </div>
      </td>
      <td class="mono ${pctClass(pair.price_spread_pct)}">${fmtPct(pair.price_spread_pct, 3)}</td>
      <td class="mono ${pctClass(pair.funding_spread_apr_pct)}">${fmtPct(pair.funding_spread_apr_pct, 2)}</td>
      <td class="mono">${pair.break_even_days != null ? pair.break_even_days + 'd' : '--'}</td>
      <td class="mono">
        <div class="split-line">
          <span>${fmtCountdown(pair.long_next_funding_ts)}</span>
          <span>${fmtCountdown(pair.short_next_funding_ts)}</span>
        </div>
      </td>
    </tr>
  `).join('');
}

function renderAll() {
  renderHero();
  renderCoinStrip();
  renderHistoryWindowCopy();
  renderCurrentFunding();
  renderPairCard();
  renderHistorical();
  renderPairs();
}
async function loadHistorical() {
  const res = await fetch('/api/historical/apr');
  STATE.historical = await res.json();
  renderAll();
}
async function loadLive() {
  const res = await fetch('/api/arbitrage/snapshot?ts=' + Date.now());
  STATE.live = await res.json();
  renderAll();
}

document.getElementById('search').addEventListener('input', (event) => {
  STATE.search = event.target.value;
  renderCoinStrip();
});
document.querySelectorAll('#pair-sort button').forEach(btn => {
  btn.addEventListener('click', () => {
    STATE.pairSort = btn.dataset.sort;
    setActiveButtons('pair-sort', 'sort', STATE.pairSort);
    renderPairs();
  });
});
document.querySelectorAll('#pair-scope button').forEach(btn => {
  btn.addEventListener('click', () => {
    STATE.pairScope = btn.dataset.scope;
    setActiveButtons('pair-scope', 'scope', STATE.pairScope);
    renderPairs();
  });
});

loadHistorical();
loadLive();
setInterval(loadLive, 10000);
setInterval(loadHistorical, 300000);
</script>
</body>
</html>
"""
