import { fmtRub, fmtUsd } from './utils.js';

const ENDPOINT = '/api/item/';

function esc(s) {
  return (s == null ? '' : String(s))
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function fmtFloat(v) {
  if (v == null) return '—';
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(6) : '—';
}

function fmtTs(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return esc(ts);
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function wearFromFloat(f) {
  if (f == null) return '';
  const n = Number(f);
  if (!Number.isFinite(n)) return '';
  if (n < 0.07) return 'FN';
  if (n < 0.15) return 'MW';
  if (n < 0.38) return 'FT';
  if (n < 0.45) return 'WW';
  return 'BS';
}

function fmtUnlock(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return '';
  if (d.getTime() <= Date.now()) return '';
  return 'трейдлок до ' + d.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' });
}

function extractStateFlags(name) {
  const flags = [];
  if (!name) return flags;
  if (name.includes('StatTrak')) flags.push({ label: 'StatTrak™', cls: 'state-stattrak' });
  if (name.startsWith('Souvenir ') || name.includes(' Souvenir ')) {
    flags.push({ label: 'Souvenir', cls: 'state-souvenir' });
  }
  if (name.startsWith('★')) flags.push({ label: '★', cls: 'state-knife' });
  return flags;
}

function renderStickers(stickers) {
  if (!stickers || !stickers.length) return '';
  return '<div class="detail-stickers">' + stickers.map(st => {
    const wearNum = Number(st.wear);
    const wearPct = Number.isFinite(wearNum) && wearNum > 0 ? Math.round(wearNum * 100) : null;
    const title = esc((st.name || '') + (wearPct != null ? ' · wear ' + wearPct + '%' : ''));
    const img = st.image
      ? '<img src="' + esc(st.image) + '" alt="" loading="lazy">'
      : '<span class="sticker-ph">?</span>';
    const wearBadge = wearPct != null
      ? '<span class="detail-sticker-wear">' + wearPct + '</span>'
      : '';
    return '<span class="detail-sticker" title="' + title + '">' + img + wearBadge + '</span>';
  }).join('') + '</div>';
}

function renderListingRow(lst) {
  const fl = lst.float;
  const wear = wearFromFloat(fl);
  const unlock = fmtUnlock(lst.unlock_at);
  const paint = (lst.paint_index != null || lst.paint_seed != null)
    ? '<span class="detail-paint" title="Paint index / seed">P ' + (lst.paint_index ?? '—') + '/' + (lst.paint_seed ?? '—') + '</span>'
    : '';
  const inspect = lst.item_link
    ? '<a class="detail-inspect" href="' + esc(lst.item_link) + '" title="Steam inspect">inspect</a>'
    : '';
  const nameTag = lst.name_tag
    ? '<span class="detail-nametag" title="Именная бирка">' + esc(lst.name_tag) + '</span>'
    : '';
  const wearBadge = wear
    ? '<span class="detail-wear detail-wear-' + wear.toLowerCase() + '">' + wear + '</span>'
    : '';

  return '<div class="detail-listing">' +
    '<div class="detail-listing-price">' +
      '<span class="price-rub">' + fmtRub(lst.price_rub) + '</span>' +
      '<span class="price-usd">' + fmtUsd(lst.price_usd) + '</span>' +
    '</div>' +
    '<div class="detail-listing-meta">' +
      wearBadge +
      (fl != null ? '<span class="detail-float" title="Float value">' + fmtFloat(fl) + '</span>' : '') +
      paint +
      nameTag +
      (unlock ? '<span class="detail-unlock">' + esc(unlock) + '</span>' : '') +
    '</div>' +
    renderStickers(lst.stickers) +
    '<div class="detail-listing-actions">' + inspect + '</div>' +
  '</div>';
}

function renderSnapshotMeta(data) {
  if (!data.snapshot_available) {
    return '<div class="detail-empty">Локальный snapshot листингов ещё не собран на сервере.</div>';
  }
  if (data.snapshot_built_at) {
    return '<div class="detail-section-title detail-section-title-empty">Snapshot: ' + esc(fmtTs(data.snapshot_built_at)) + '</div>';
  }
  return '';
}

function renderModal(data) {
  const s = data.summary || {};
  const listings = data.listings || [];
  const total = data.listings_total || 0;
  const hasListings = listings.length > 0;

  const imgHtml = s.image
    ? '<img class="detail-img" src="' + esc(s.image) + '" alt="" loading="lazy">'
    : '<div class="detail-img detail-img-placeholder">?</div>';

  const priceBlock = s.price_rub != null
    ? '<div class="detail-price"><span class="detail-price-rub">' + fmtRub(s.price_rub) + '</span><span class="detail-price-usd">' + fmtUsd(s.price_usd) + '</span></div>'
    : '<div class="detail-price detail-price-none">нет предложений</div>';

  const openLis = s.url
    ? '<a class="detail-open-lis" href="' + esc(s.url) + '" target="_blank" rel="noopener">открыть на lis-skins →</a>'
    : '';

  const stateFlags = extractStateFlags(s.name);
  const stateHtml = stateFlags.length
    ? '<div class="detail-state-flags">' +
        stateFlags.map(f => '<span class="detail-state ' + f.cls + '">' + esc(f.label) + '</span>').join('') +
      '</div>'
    : '';

  let listingsHeader = '<div class="detail-section-title">Листинги</div>';
  if (hasListings) {
    const suffix = data.listings_updated ? ' · обновлён ' + esc(fmtTs(data.listings_updated)) : '';
    listingsHeader = '<div class="detail-section-title">Листинги — ' + listings.length + ' из ' + total + suffix + '</div>';
  }

  let listingsBody;
  if (hasListings) {
    listingsBody = listings.map(renderListingRow).join('');
  } else if (!data.snapshot_available) {
    listingsBody = '<div class="detail-empty">Snapshot листингов пока не загружен на VPS. Сначала собери и залей `listings_snapshot.db`.</div>';
  } else if (s.count === 0) {
    listingsBody = '<div class="detail-empty">Сейчас нет предложений на lis-skins.</div>';
  } else {
    listingsBody = '<div class="detail-empty">В текущем snapshot нет листингов для этого предмета.</div>';
  }

  return '<div class="detail-header" style="border-left: 3px solid ' + esc(s.rarity_color || '#b0c3d9') + '">' +
      imgHtml +
      '<div class="detail-header-info">' +
        '<div class="detail-category">' + esc(s.category || '') + '</div>' +
        stateHtml +
        '<h2 class="detail-name">' + esc(s.name || '') + '</h2>' +
        priceBlock +
        '<div class="detail-count">' + (s.count || 0) + ' на маркете</div>' +
        openLis +
      '</div>' +
    '</div>' +
    '<div class="detail-listings">' +
      renderSnapshotMeta(data) +
      listingsHeader +
      listingsBody +
    '</div>';
}

let _currentName = null;
let _overlay = null;
let _body = null;
let _closeBtn = null;

function ensureModalNode() {
  if (_overlay) return;
  _overlay = document.getElementById('itemDetailOverlay');
  _body = document.getElementById('itemDetailBody');
  _closeBtn = document.getElementById('itemDetailClose');
}

function closeModal() {
  if (!_overlay) return;
  _overlay.classList.remove('open');
  _currentName = null;
}

async function fetchDetail(name) {
  const resp = await fetch(ENDPOINT + encodeURIComponent(name));
  if (!resp.ok) throw new Error('HTTP ' + resp.status);
  return resp.json();
}

async function openItemDetail(name) {
  if (!name) return;
  ensureModalNode();
  if (!_overlay || !_body) return;
  _currentName = name;
  _body.innerHTML = '<div class="detail-loading"><div class="spinner"></div><div>Грузим…</div></div>';
  _overlay.classList.add('open');
  try {
    const data = await fetchDetail(name);
    if (_currentName !== name) return;
    _body.innerHTML = renderModal(data);
  } catch (err) {
    console.error('item detail fetch failed:', err);
    if (_currentName !== name) return;
    _body.innerHTML = '<div class="detail-empty">Не получилось загрузить детали: ' + esc(err.message || err) + '</div>';
  }
}

function onGridClick(e) {
  if (e.target.closest('button, a, input, select, textarea')) return;
  const card = e.target.closest('.cat-card');
  if (!card) return;
  const name = card.dataset.itemName;
  if (!name) return;
  openItemDetail(name);
}

export function initItemDetail() {
  ensureModalNode();

  ['catalogGrid', 'casesGrid', 'favoritesGrid', 'wishlistGrid'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('click', onGridClick);
  });

  if (_closeBtn) _closeBtn.addEventListener('click', closeModal);
  if (_overlay) {
    _overlay.addEventListener('click', (e) => {
      if (e.target === _overlay) closeModal();
    });
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && _overlay && _overlay.classList.contains('open')) {
      closeModal();
    }
  });
}
