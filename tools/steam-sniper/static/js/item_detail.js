import { getListEntries, saveListTargets } from './lists.js';
import { fmtRub, fmtUsd } from './utils.js';
import { events } from './events.js';

const ENDPOINT = '/api/item/';
const DEFAULT_FILTERS = {
  floatMin: '',
  floatMax: '',
  hasStickers: 'all',
  hasKeychains: 'all',
  sort: 'price_asc',
};

const CATEGORY_LABELS = {
  knife: 'Ножи',
  gloves: 'Перчатки',
  rifle: 'Винтовки',
  pistol: 'Пистолеты',
  smg: 'ПП',
  shotgun: 'Дробовики',
  machinegun: 'Пулемёты',
  sticker: 'Наклейки',
  case: 'Кейсы',
  graffiti: 'Граффити',
  music_kit: 'Музыка',
  patch: 'Нашивки',
  key: 'Ключи',
  agent: 'Агенты',
  other: 'Другое',
};

let _currentName = null;
let _currentFilters = { ...DEFAULT_FILTERS };
let _overlay = null;
let _body = null;
let _closeBtn = null;
let _filterTimer = null;

function esc(s) {
  return (s == null ? '' : String(s))
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function fmtFloat(v) {
  if (v == null || v === '') return '—';
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

function deliveryLabel(ts) {
  return fmtUnlock(ts) || 'Мгновенно';
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

function hasActiveFilters() {
  return Boolean(
    _currentFilters.floatMin ||
    _currentFilters.floatMax ||
    _currentFilters.hasStickers !== 'all' ||
    _currentFilters.hasKeychains !== 'all'
  );
}

function buildQuery(name) {
  const params = new URLSearchParams();
  params.set('limit', '40');
  params.set('sort', _currentFilters.sort);
  if (_currentFilters.floatMin !== '') params.set('float_min', _currentFilters.floatMin);
  if (_currentFilters.floatMax !== '') params.set('float_max', _currentFilters.floatMax);
  if (_currentFilters.hasStickers !== 'all') params.set('has_stickers', _currentFilters.hasStickers);
  if (_currentFilters.hasKeychains !== 'all') params.set('has_keychains', _currentFilters.hasKeychains);
  return ENDPOINT + encodeURIComponent(name) + '?' + params.toString();
}

function sortArrow(field) {
  const active = _currentFilters.sort.startsWith(field);
  if (!active) return '<span class="detail-sort-arrow">↕</span>';
  return _currentFilters.sort.endsWith('asc')
    ? '<span class="detail-sort-arrow active">↑</span>'
    : '<span class="detail-sort-arrow active">↓</span>';
}

function toggleSort(field) {
  const current = _currentFilters.sort;
  if (current.startsWith(field)) {
    _currentFilters.sort = current.endsWith('asc') ? field + '_desc' : field + '_asc';
  } else {
    _currentFilters.sort = field + '_asc';
  }
}

function renderFloatMeter(value) {
  if (value == null || value === '') {
    return '<div class="detail-float-meter is-empty"><span>—</span></div>';
  }
  const n = Number(value);
  const pct = Number.isFinite(n) ? Math.max(0, Math.min(100, n * 100)) : 0;
  return `
    <div class="detail-float-meter">
      <div class="detail-float-meter-value">${fmtFloat(value)}</div>
      <div class="detail-float-meter-bar">
        <span class="detail-float-meter-fill"></span>
        <span class="detail-float-meter-pin" style="left:${pct}%"></span>
      </div>
    </div>
  `;
}

function renderAttachments(items, kind) {
  if (!items || !items.length) {
    return '<div class="detail-attachments-empty">—</div>';
  }
  return `
    <div class="detail-attachments detail-attachments-${kind}">
      ${items.map((item) => {
        const wearNum = Number(item.wear);
        const wearPct = Number.isFinite(wearNum) && wearNum > 0 ? Math.round(wearNum * 100) : null;
        const wearBadge = wearPct != null ? `<span class="detail-attachment-wear">${wearPct}</span>` : '';
        const img = item.image
          ? `<img src="${esc(item.image)}" alt="" loading="lazy">`
          : '<span class="detail-attachment-placeholder">?</span>';
        const title = `${esc(item.name || '')}${wearPct != null ? ` · wear ${wearPct}%` : ''}`;
        return `<span class="detail-attachment" title="${title}">${img}${wearBadge}</span>`;
      }).join('')}
    </div>
  `;
}

function renderRarity(summary) {
  if (!summary.rarity_label) return '';
  const emphasis = summary.rarity_emphasis ? ' detail-rarity-emphasis' : '';
  const style = summary.rarity_color ? ` style="--rarity-color:${esc(summary.rarity_color)}"` : '';
  return `<span class="detail-rarity-badge${emphasis}"${style}>${esc(summary.rarity_label)}</span>`;
}

function renderStateFlags(summary) {
  const stateFlags = extractStateFlags(summary.name);
  const all = [...stateFlags];
  if (summary.wear_label) {
    all.push({ label: summary.wear_label, cls: 'state-wear' });
  }
  if (!all.length) return '';
  return `
    <div class="detail-state-flags">
      ${all.map(flag => `<span class="detail-state ${flag.cls}">${esc(flag.label)}</span>`).join('')}
      ${renderRarity(summary)}
    </div>
  `;
}

function renderPriceCompare(summary) {
  if (summary.steam_price_rub == null) return '';
  const discount = summary.discount_pct != null
    ? `<span class="detail-price-chip">${summary.discount_pct > 0 ? '-' : ''}${summary.discount_pct}%</span>`
    : '';
  return `
    <div class="detail-price-compare">
      ${discount}
      <span class="detail-price-steam">Steam: ${fmtRub(summary.steam_price_rub)}</span>
    </div>
  `;
}

function fmtAlertInputValue(value) {
  if (value == null || value === '') return '';
  const n = Number(value);
  if (!Number.isFinite(n)) return '';
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, '');
}

function parseAlertInputValue(raw) {
  const cleaned = String(raw ?? '').trim().replace(',', '.');
  if (!cleaned) return { ok: true, value: null };
  const value = Number(cleaned);
  if (!Number.isFinite(value) || value <= 0) {
    return { ok: false, value: null };
  }
  return { ok: true, value: Math.round(value * 100) / 100 };
}

function alertListLabel(listType) {
  return listType === 'favorite' ? 'Избранное' : 'Хотелки';
}

function renderAlertStatus(entry) {
  const chips = [];
  if (entry.alert_below_triggered) {
    chips.push('<span class="detail-alert-chip is-below">below hit</span>');
  }
  if (entry.alert_above_triggered) {
    chips.push('<span class="detail-alert-chip is-above">above hit</span>');
  }
  if (!chips.length && (entry.target_below_rub != null || entry.target_above_rub != null)) {
    chips.push('<span class="detail-alert-chip is-armed">armed</span>');
  }
  return chips.join('');
}

function renderAlertSettings(summary) {
  const name = summary.name || _currentName || '';
  const entries = getListEntries(name);
  if (!entries.length) {
    return `
      <section class="detail-panel detail-alerts-panel detail-alerts-empty">
        <div class="detail-panel-title">Telegram alerts</div>
        <div class="detail-alerts-empty-msg">
          Добавь предмет в <b>Избранное</b> или <b>Хотелки</b> — и тут появятся поля 🔴 <i>ниже</i> / 🟢 <i>выше</i>.
          Когда цена пересечёт порог, придёт уведомление в Telegram.
        </div>
        <div class="detail-alerts-empty-actions">
          <button type="button" class="list-toggle detail-alert-add-btn is-favorite"
            data-list="favorite" data-name="${esc(name)}">♡ В Избранное</button>
          <button type="button" class="list-toggle detail-alert-add-btn is-wishlist"
            data-list="wishlist" data-name="${esc(name)}">☆ В Хотелки</button>
        </div>
      </section>
    `;
  }
  return `
    <section class="detail-panel detail-alerts-panel">
      <div class="detail-panel-title">Telegram alerts</div>
      <div class="detail-alerts-grid">
        ${entries.map((entry) => `
          <div
            class="detail-alert-card"
            data-alert-card
            data-item-name="${esc(entry.item_name)}"
            data-list-type="${esc(entry.list_type)}"
          >
            <div class="detail-alert-card-head">
              <div class="detail-alert-card-title">
                <span class="detail-alert-list-badge ${esc(entry.list_type)}">${alertListLabel(entry.list_type)}</span>
                ${summary.price_rub != null ? `<span class="detail-alert-current">Сейчас ${fmtRub(summary.price_rub)}</span>` : ''}
              </div>
              <div class="detail-alert-status">${renderAlertStatus(entry)}</div>
            </div>
            <div class="detail-alert-fields">
              <label class="detail-alert-field is-below">
                <span>Alert below</span>
                <input
                  type="number"
                  inputmode="decimal"
                  min="0"
                  step="0.01"
                  placeholder="off"
                  value="${esc(fmtAlertInputValue(entry.target_below_rub))}"
                  data-alert-field="below"
                >
              </label>
              <label class="detail-alert-field is-above">
                <span>Alert above</span>
                <input
                  type="number"
                  inputmode="decimal"
                  min="0"
                  step="0.01"
                  placeholder="off"
                  value="${esc(fmtAlertInputValue(entry.target_above_rub))}"
                  data-alert-field="above"
                >
              </label>
            </div>
            <div class="detail-alert-hint">Введи число и нажми <b>Enter</b> (или кликни вне поля) — сохранится автоматически. Уведомление придёт в Telegram когда цена пересечёт порог.</div>
            <div class="detail-alert-message" data-alert-message></div>
          </div>
        `).join('')}
      </div>
    </section>
  `;
}

function renderWearTabs(wearTiers) {
  if (!wearTiers || wearTiers.length < 2) return '';
  return `
    <section class="detail-panel detail-wear-panel">
      <div class="detail-panel-title">Состояния</div>
      <div class="detail-wear-tabs">
        ${wearTiers.map(tier => `
          <button
            type="button"
            class="detail-wear-tab${tier.active ? ' active' : ''}"
            data-tier-name="${esc(tier.name)}"
          >
            <span class="detail-wear-tab-code">${tier.wear}</span>
            <span class="detail-wear-tab-label">${esc(tier.label)}</span>
            <span class="detail-wear-tab-count">${tier.count} шт.</span>
            <span class="detail-wear-tab-price">${tier.min_price_rub != null ? fmtRub(tier.min_price_rub) : '—'}</span>
          </button>
        `).join('')}
      </div>
    </section>
  `;
}

function renderFilters() {
  return `
    <section class="detail-panel detail-filters-panel">
      <div class="detail-panel-title">Фильтры</div>
      <div class="detail-filters-grid">
        <label class="detail-filter">
          <span>Float от</span>
          <input type="number" min="0" max="1" step="0.001" value="${esc(_currentFilters.floatMin)}" data-filter="floatMin" placeholder="0.000">
        </label>
        <label class="detail-filter">
          <span>Float до</span>
          <input type="number" min="0" max="1" step="0.001" value="${esc(_currentFilters.floatMax)}" data-filter="floatMax" placeholder="1.000">
        </label>
        <label class="detail-filter">
          <span>Стикеры</span>
          <select data-filter="hasStickers">
            <option value="all"${_currentFilters.hasStickers === 'all' ? ' selected' : ''}>Все</option>
            <option value="yes"${_currentFilters.hasStickers === 'yes' ? ' selected' : ''}>Только со стикерами</option>
            <option value="no"${_currentFilters.hasStickers === 'no' ? ' selected' : ''}>Без стикеров</option>
          </select>
        </label>
        <label class="detail-filter">
          <span>Брелоки</span>
          <select data-filter="hasKeychains">
            <option value="all"${_currentFilters.hasKeychains === 'all' ? ' selected' : ''}>Все</option>
            <option value="yes"${_currentFilters.hasKeychains === 'yes' ? ' selected' : ''}>Только с брелоком</option>
            <option value="no"${_currentFilters.hasKeychains === 'no' ? ' selected' : ''}>Без брелока</option>
          </select>
        </label>
      </div>
    </section>
  `;
}

function renderListingHeader() {
  return `
    <div class="detail-table-head">
      <div class="detail-head-cell">Доставка</div>
      <button class="detail-head-cell detail-head-button" type="button" data-sort-field="float">
        Float ${sortArrow('float')}
      </button>
      <div class="detail-head-cell">Nametag</div>
      <div class="detail-head-cell">Стикеры</div>
      <div class="detail-head-cell">Брелок</div>
      <button class="detail-head-cell detail-head-button align-right" type="button" data-sort-field="price">
        Цена ${sortArrow('price')}
      </button>
      <div class="detail-head-cell align-right">Действие</div>
    </div>
  `;
}

function renderListingRow(lst) {
  const unlock = fmtUnlock(lst.unlock_at);
  const deliveryCls = unlock ? 'is-locked' : 'is-ready';
  return `
    <div class="detail-table-row">
      <div class="detail-cell">
        <span class="detail-delivery-badge ${deliveryCls}">${esc(deliveryLabel(lst.unlock_at))}</span>
      </div>
      <div class="detail-cell">
        ${renderFloatMeter(lst.float)}
      </div>
      <div class="detail-cell">
        ${lst.name_tag ? `<span class="detail-nametag">${esc(lst.name_tag)}</span>` : '<span class="detail-cell-empty">—</span>'}
      </div>
      <div class="detail-cell">
        ${renderAttachments(lst.stickers || [], 'stickers')}
      </div>
      <div class="detail-cell">
        ${renderAttachments(lst.keychains || [], 'keychains')}
      </div>
      <div class="detail-cell align-right">
        <div class="detail-row-price">
          <span class="detail-row-price-rub">${fmtRub(lst.price_rub)}</span>
          <span class="detail-row-price-usd">${fmtUsd(lst.price_usd)}</span>
        </div>
      </div>
      <div class="detail-cell align-right">
        ${lst.item_link
          ? `<a class="detail-action-btn" href="${esc(lst.item_link)}" title="Осмотреть в игре">Осмотреть в игре</a>`
          : '<span class="detail-cell-empty">—</span>'}
      </div>
    </div>
  `;
}

function renderTable(data) {
  const listings = data.listings || [];
  if (!listings.length) {
    if (!data.snapshot_available) {
      return '<div class="detail-empty">Snapshot листингов пока не загружен на сервер.</div>';
    }
    if (hasActiveFilters()) {
      return '<div class="detail-empty">Под текущие фильтры ничего не нашлось.</div>';
    }
    if ((data.summary?.count || 0) === 0) {
      return '<div class="detail-empty">Сейчас нет предложений на lis-skins.</div>';
    }
    return '<div class="detail-empty">Для этого предмета в snapshot сейчас нет листингов.</div>';
  }

  return `
    <section class="detail-panel detail-table-panel">
      <div class="detail-table-meta">
        <div class="detail-panel-title">Листинги</div>
        <div class="detail-table-meta-right">
          <span>${data.listings_total} найдено</span>
          ${data.listings_updated ? `<span>snapshot: ${esc(fmtTs(data.listings_updated))}</span>` : ''}
        </div>
      </div>
      <div class="detail-table">
        ${renderListingHeader()}
        <div class="detail-table-body">
          ${listings.map(renderListingRow).join('')}
        </div>
      </div>
    </section>
  `;
}

function renderSnapshotMeta(data) {
  if (!data.snapshot_available) {
    return '<div class="detail-snapshot-banner detail-snapshot-missing">Локальный snapshot ещё не собран. Деталка работает, но листинги недоступны.</div>';
  }
  return `
    <div class="detail-snapshot-banner">
      <span>Snapshot: ${data.snapshot_built_at ? esc(fmtTs(data.snapshot_built_at)) : '—'}</span>
      <span>${Math.round((data.snapshot_size_bytes || 0) / (1024 * 1024))} MB</span>
    </div>
  `;
}

function renderModal(data) {
  const summary = data.summary || {};
  const imgHtml = summary.image
    ? `<img class="detail-hero-image" src="${esc(summary.image)}" alt="" loading="lazy">`
    : '<div class="detail-hero-image detail-hero-image-placeholder">нет фото</div>';

  return `
    <div class="detail-shell">
      <section class="detail-hero" style="--hero-accent:${esc(summary.rarity_color || '#b0c3d9')}">
        <div class="detail-hero-media">
          ${imgHtml}
        </div>
        <div class="detail-hero-content">
          <div class="detail-kicker">${esc(CATEGORY_LABELS[summary.category] || summary.category || 'Предмет')}</div>
          <h2 class="detail-hero-title">${esc(summary.name || '')}</h2>
          <div class="detail-hero-subline">
            ${summary.weapon_model ? `<span>${esc(summary.weapon_model)}</span>` : ''}
            ${summary.count != null ? `<span>${summary.count} на маркете</span>` : ''}
          </div>
          ${renderStateFlags(summary)}
          <div class="detail-price-row">
            <div class="detail-price-block">
              <span class="detail-price-rub">${summary.price_rub != null ? fmtRub(summary.price_rub) : '—'}</span>
              <span class="detail-price-usd">${summary.price_usd != null ? fmtUsd(summary.price_usd) : ''}</span>
            </div>
            ${renderPriceCompare(summary)}
          </div>
          <div class="detail-hero-actions">
            ${summary.url ? `<a class="detail-primary-link" href="${esc(summary.url)}" target="_blank" rel="noopener">Открыть на lis-skins →</a>` : ''}
          </div>
        </div>
      </section>

      ${renderSnapshotMeta(data)}
      ${renderAlertSettings(summary)}
      ${renderWearTabs(data.wear_tiers || [])}
      ${renderFilters()}
      ${renderTable(data)}
    </div>
  `;
}

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
  const resp = await fetch(buildQuery(name));
  if (!resp.ok) throw new Error('HTTP ' + resp.status);
  return resp.json();
}

async function refreshCurrentDetail() {
  if (!_currentName || !_body) return;
  const name = _currentName;
  _body.innerHTML = '<div class="detail-loading"><div class="spinner"></div><div>Грузим детальку…</div></div>';
  try {
    const data = await fetchDetail(name);
    if (_currentName !== name) return;
    _body.innerHTML = renderModal(data);
  } catch (err) {
    console.error('item detail fetch failed:', err);
    if (_currentName !== name) return;
    _body.innerHTML = `<div class="detail-empty">Не получилось загрузить детали: ${esc(err.message || err)}</div>`;
  }
}

async function openItemDetail(name, { preserveFilters = false } = {}) {
  if (!name) return;
  ensureModalNode();
  if (!_overlay || !_body) return;
  _currentName = name;
  if (!preserveFilters) {
    _currentFilters = { ...DEFAULT_FILTERS };
  }
  _overlay.classList.add('open');
  _body.innerHTML = '<div class="detail-loading"><div class="spinner"></div><div>Грузим детальку…</div></div>';
  await refreshCurrentDetail();
}

function scheduleFilterRefresh() {
  clearTimeout(_filterTimer);
  _filterTimer = setTimeout(() => {
    refreshCurrentDetail();
  }, 220);
}

function onModalClick(e) {
  const tierBtn = e.target.closest('[data-tier-name]');
  if (tierBtn) {
    openItemDetail(tierBtn.dataset.tierName, { preserveFilters: true });
    return;
  }

  const sortBtn = e.target.closest('[data-sort-field]');
  if (sortBtn) {
    toggleSort(sortBtn.dataset.sortField);
    refreshCurrentDetail();
  }
}

function onModalInput(e) {
  const field = e.target.dataset.filter;
  if (field) {
    _currentFilters[field] = e.target.value;
    scheduleFilterRefresh();
    return;
  }

  if (e.target.matches('input[data-alert-field]')) {
    const card = e.target.closest('[data-alert-card]');
    if (card) {
      const message = card.querySelector('[data-alert-message]');
      if (message) message.textContent = '';
      updateAlertValidation(card);
    }
  }
}

function updateAlertValidation(card) {
  let isValid = true;
  card.querySelectorAll('input[data-alert-field]').forEach((input) => {
    const parsed = parseAlertInputValue(input.value);
    input.classList.toggle('is-invalid', !parsed.ok);
    if (!parsed.ok) isValid = false;
  });
  return isValid;
}

async function commitAlertCard(card) {
  if (!card || card.dataset.saving === '1') return;
  const message = card.querySelector('[data-alert-message]');
  const belowInput = card.querySelector('input[data-alert-field="below"]');
  const aboveInput = card.querySelector('input[data-alert-field="above"]');
  if (!belowInput || !aboveInput) return;
  if (!updateAlertValidation(card)) {
    if (message) message.textContent = 'Введите число больше нуля или оставь поле пустым.';
    return;
  }

  const below = parseAlertInputValue(belowInput.value).value;
  const above = parseAlertInputValue(aboveInput.value).value;
  card.dataset.saving = '1';
  card.classList.add('is-saving');
  if (message) message.textContent = 'Сохраняю…';
  try {
    await saveListTargets(card.dataset.itemName || _currentName || '', card.dataset.listType || '', {
      targetBelowRub: below,
      targetAboveRub: above,
    });
    await refreshCurrentDetail();
  } catch (err) {
    console.error('save list targets failed:', err);
    if (message) message.textContent = err.message || 'Не получилось сохранить.';
  } finally {
    delete card.dataset.saving;
    card.classList.remove('is-saving');
  }
}

function onModalKeydown(e) {
  const input = e.target.closest('input[data-alert-field]');
  if (!input || e.key !== 'Enter') return;
  e.preventDefault();
  const card = input.closest('[data-alert-card]');
  if (card) commitAlertCard(card);
}

function onModalFocusOut(e) {
  const input = e.target.closest('input[data-alert-field]');
  if (!input) return;
  const card = input.closest('[data-alert-card]');
  if (!card) return;
  setTimeout(() => {
    if (!card.contains(document.activeElement)) {
      commitAlertCard(card);
    }
  }, 0);
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

  ['catalogGrid', 'casesGrid', 'favoritesGrid', 'wishlistGrid'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('click', onGridClick);
  });

  if (_closeBtn) _closeBtn.addEventListener('click', closeModal);
  if (_overlay) {
    _overlay.addEventListener('click', (e) => {
      if (e.target === _overlay) closeModal();
    });
  }
  if (_body) {
    _body.addEventListener('click', onModalClick);
    _body.addEventListener('input', onModalInput);
    _body.addEventListener('change', onModalInput);
    _body.addEventListener('keydown', onModalKeydown);
    _body.addEventListener('focusout', onModalFocusOut);
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && _overlay && _overlay.classList.contains('open')) {
      closeModal();
    }
  });

  events.on('lists:changed', () => {
    if (_overlay && _overlay.classList.contains('open')) {
      refreshCurrentDetail();
    }
  });
}
