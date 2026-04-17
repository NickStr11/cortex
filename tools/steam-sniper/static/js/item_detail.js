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

function renderStickers(stickers) {
  if (!stickers || !stickers.length) return '';
  return '<div class="detail-stickers">' + stickers.map(st => {
    const wear = st.wear && st.wear > 0 ? Math.round(st.wear * 100) + '%' : '';
    const title = esc((st.name || '') + (wear ? ' · wear ' + wear : ''));
    const img = st.image
      ? '<img src="' + esc(st.image) + '" alt="" loading="lazy">'
      : '<span class="sticker-ph">?</span>';
    return '<span class="detail-sticker" title="' + title + '">' + img + '</span>';
  }).join('') + '</div>';
}

function renderListingRow(lst) {
  const fl = lst.float;
  const wear = wearFromFloat(fl);
  const unlock = fmtUnlock(lst.unlock_at);
  const paint = (lst.paint_index != null || lst.paint_seed != null)
    ? '<span class="detail-paint">P ' + (lst.paint_index ?? '—') + '/' + (lst.paint_seed ?? '—') + '</span>'
    : '';
  const inspect = lst.item_link
    ? '<a class="detail-inspect" href="' + esc(lst.item_link) + '" title="Steam inspect">inspect</a>'
    : '';
  return '<div class="detail-listing">' +
    '<div class="detail-listing-price">' +
      '<span class="price-rub">' + fmtRub(lst.price_rub) + '</span>' +
      '<span class="price-usd">' + fmtUsd(lst.price_usd) + '</span>' +
    '</div>' +
    '<div class="detail-listing-meta">' +
      (fl != null ? '<span class="detail-float" title="Float value">' + fmtFloat(fl) + (wear ? ' · ' + wear : '') + '</span>' : '') +
      paint +
      (unlock ? '<span class="detail-unlock">' + esc(unlock) + '</span>' : '') +
    '</div>' +
    renderStickers(lst.stickers) +
    '<div class="detail-listing-actions">' + inspect + '</div>' +
  '</div>';
}

function renderModal(data) {
  const s = data.summary || {};
  const listings = data.listings || [];
  const total = data.listings_total || 0;

  const imgHtml = s.image
    ? '<img class="detail-img" src="' + esc(s.image) + '" alt="" loading="lazy">'
    : '<div class="detail-img detail-img-placeholder">?</div>';

  const priceBlock = s.price_rub != null
    ? '<div class="detail-price"><span class="detail-price-rub">' + fmtRub(s.price_rub) + '</span><span class="detail-price-usd">' + fmtUsd(s.price_usd) + '</span></div>'
    : '<div class="detail-price detail-price-none">нет предложений</div>';

  const openLis = s.url
    ? '<a class="detail-open-lis" href="' + esc(s.url) + '" target="_blank" rel="noopener">открыть на lis-skins →</a>'
    : '';

  const listingsHeader = listings.length
    ? '<div class="detail-section-title">Листинги — ' + listings.length + ' из ' + total + '</div>'
    : '<div class="detail-section-title detail-section-title-empty">Листинги ещё подгружаются…</div>';

  const listingsBody = listings.length
    ? listings.map(renderListingRow).join('')
    : '<div class="detail-empty">Индекс листингов обновляется раз в 15 минут. Если только что стартовали — подожди пару минут и обнови.</div>';

  return '<div class="detail-header" style="border-left: 3px solid ' + esc(s.rarity_color || '#b0c3d9') + '">' +
      imgHtml +
      '<div class="detail-header-info">' +
        '<div class="detail-category">' + esc(s.category || '') + '</div>' +
        '<h2 class="detail-name">' + esc(s.name || '') + '</h2>' +
        priceBlock +
        '<div class="detail-count">' + (s.count || 0) + ' на маркете</div>' +
        openLis +
      '</div>' +
    '</div>' +
    '<div class="detail-listings">' +
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

async function openItemDetail(name) {
  if (!name) return;
  ensureModalNode();
  if (!_overlay || !_body) return;
  _currentName = name;
  _body.innerHTML = '<div class="detail-loading">Грузим…</div>';
  _overlay.classList.add('open');
  try {
    const resp = await fetch(ENDPOINT + encodeURIComponent(name));
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();
    if (_currentName !== name) return; // user clicked another card while we waited
    _body.innerHTML = renderModal(data);
  } catch (err) {
    console.error('item detail fetch failed:', err);
    if (_currentName !== name) return;
    _body.innerHTML = '<div class="detail-empty">Не получилось загрузить детали: ' + esc(err.message || err) + '</div>';
  }
}

function onGridClick(e) {
  // Ignore clicks on existing buttons/links inside the card (favorite, wishlist,
  // inline links), which should keep their original behavior.
  if (e.target.closest('button, a, input, select, textarea')) return;
  const card = e.target.closest('.cat-card');
  if (!card) return;
  const name = card.dataset.itemName;
  if (!name) return;
  openItemDetail(name);
}

export function initItemDetail() {
  ensureModalNode();

  // Delegate click handling for every grid that renders catalog-style cards.
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
