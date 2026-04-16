import { state } from './state.js';
import { fmtRub, timeAgo } from './utils.js';

export async function loadAlerts() {
  try {
    const r = await fetch('/api/alerts');
    const d = await r.json();
    const container = document.getElementById('alertsList');
    const alerts = d.alerts || [];

    if (!alerts.length) {
      container.innerHTML = '<div class="empty-state">No alerts yet</div>';
      return;
    }

    container.innerHTML = alerts.map(a => {
      const icon = a.type === 'buy' ? '\uD83D\uDCC9' : '\uD83D\uDCC8';
      const action = a.type === 'buy' ? '\u041A\u0423\u041F\u0418\u0422\u042C' : '\u041F\u0420\u041E\u0414\u0410\u0422\u042C';
      const typeClass = a.type === 'buy' ? 'alert-buy' : 'alert-sell';
      const priceRub = a.price_usd ? fmtRub(a.price_usd * state.usdRub) : '\u2014';
      const targetRub = a.target_rub ? Math.round(a.target_rub).toLocaleString() + '\u20BD' : '\u2014';
      return '<div class="alert-item">' +
        '<span class="alert-icon">' + icon + '</span>' +
        '<div class="alert-body">' +
          '<span class="alert-action ' + typeClass + '">' + action + '</span> ' +
          '<span class="alert-name">' + a.name + '</span>' +
          '<div class="alert-prices">' + priceRub + ' \u2192 \u0446\u0435\u043B\u044C ' + targetRub + '</div>' +
        '</div>' +
        '<span class="alert-time">' + timeAgo(a.ts) + '</span>' +
      '</div>';
    }).join('');
  } catch (e) { console.error('loadAlerts:', e); }
}
