import { state } from './state.js';
import { fmtRub, fmtDelta } from './utils.js';
import { events } from './events.js';

export async function loadWatchlist() {
  try {
    const r = await fetch('/api/watchlist');
    const d = await r.json();
    state.usdRub = d.usd_rub || 0;

    // Update header stats
    document.getElementById('usdRate').textContent = state.usdRub ? state.usdRub.toFixed(2) : '--';
    document.getElementById('totalItems').textContent = d.total_items_lis ? d.total_items_lis.toLocaleString() + ' \u0448\u0442' : '--';
    document.getElementById('lastUpdate').textContent = d.updated_at ? new Date(d.updated_at).toLocaleTimeString('ru') : '--';

    const area = document.getElementById('watchlistArea');
    const sell = d.sell || [];
    const buy = d.buy || [];

    if (!sell.length && !buy.length) {
      area.innerHTML = '<div class="empty-state">Watchlist is empty</div>';
      return;
    }

    let html = '';
    if (sell.length) {
      html += '<div class="section-title">\u041F\u0440\u043E\u0434\u0430\u0436\u0430 <span class="badge">' + sell.length + '</span></div>';
      html += renderTable(sell);
    }
    if (buy.length) {
      html += '<div class="section-title">\u041F\u043E\u043A\u0443\u043F\u043A\u0430 <span class="badge">' + buy.length + '</span></div>';
      html += renderTable(buy);
    }
    area.innerHTML = html;
  } catch (e) { console.error('loadWatchlist:', e); }
}

function renderTable(entries) {
  let html = '<div class="wl-grid">';

  for (const entry of entries) {
    const d = fmtDelta(entry.delta_pct);
    const safeName = (entry.name || '').replace(/"/g, '&quot;');
    const showName = entry.display_name || entry.name;
    const catBadge = entry.category ? '<span class="wl-cat">' + entry.category + '</span>' : '';
    const lisUrl = entry.url || '#';
    const steamUrl = entry.steam_url || '#';

    const trend = entry.trend || {};
    let trendHtml = '';
    if (trend.direction === 'up') {
      trendHtml = '<span class="trend trend-up">\u25B2 +' + trend.pct + '%</span>';
    } else if (trend.direction === 'down') {
      trendHtml = '<span class="trend trend-down">\u25BC ' + trend.pct + '%</span>';
    } else {
      trendHtml = '<span class="trend trend-flat">\u2014 0%</span>';
    }

    const entryPrice = entry.added_price_rub ? fmtRub(entry.added_price_rub) : '\u2014';
    const currentPrice = entry.current_price_rub ? fmtRub(entry.current_price_rub) : '\u2014';
    const targetRub = Math.round(entry.target_rub || 0).toLocaleString() + '\u20BD';
    const typeIcon = entry.type === 'sell' ? '\u2265' : '\u2264';

    const rarityColor = entry.rarity_color || '#b0c3d9';
    const imgHtml = entry.image_url
      ? '<img class="wl-card-img" src="' + entry.image_url + '" loading="lazy" alt="">'
      : '';

    html += '<div class="wl-card" data-item-name="' + safeName + '" style="border-top:3px solid ' + rarityColor + '">' +
      '<div class="wl-card-header">' +
        imgHtml +
        '<div class="wl-card-meta">' +
          '<div class="wl-card-name">' + showName + '</div>' +
          '<div class="wl-card-tags">' + catBadge + trendHtml + '</div>' +
        '</div>' +
      '</div>' +
      '<div class="wl-card-prices">' +
        '<div class="price-block price-entry"><div class="price-label">\u0412\u0445\u043E\u0434</div><div class="price-val">' + entryPrice + '</div></div>' +
        '<div class="price-block price-current"><div class="price-label">\u0421\u0435\u0439\u0447\u0430\u0441</div><div class="price-val">' + currentPrice + '</div></div>' +
        '<div class="price-block price-target"><div class="price-label">' + typeIcon + ' \u0426\u0435\u043B\u044C</div><div class="price-val price-target-val">' + targetRub + '</div></div>' +
      '</div>' +
      '<div class="wl-card-footer">' +
        '<span class="wl-delta ' + d.cls + '">' + d.text + '</span>' +
        '<span class="wl-card-count">' + (entry.count || '?') + ' \u0448\u0442</span>' +
        '<span class="wl-card-qty">\u00D7' + (entry.qty || 1) + '</span>' +
        '<div class="wl-card-links">' +
          '<a href="' + lisUrl + '" target="_blank" class="wl-link" title="Lis-Skins">LS</a>' +
          '<a href="' + steamUrl + '" target="_blank" class="wl-link wl-link-steam" title="Steam Market">ST</a>' +
        '</div>' +
        '<button class="wl-remove" data-name="' + safeName + '">\u2715</button>' +
      '</div>' +
    '</div>';
  }

  html += '</div>';
  return html;
}

async function removeItem(name) {
  try {
    const r = await fetch('/api/watchlist/' + encodeURIComponent(name), { method: 'DELETE' });
    if (r.ok) { events.emit('watchlist:changed'); }
  } catch (e) { console.error('removeItem:', e); }
}

export function initWatchlist() {
  // Delegated click on delete buttons
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.wl-remove');
    if (btn) {
      e.stopPropagation();
      const name = btn.getAttribute('data-name');
      if (name) removeItem(name);
    }
  });
}
