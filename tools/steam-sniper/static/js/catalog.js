// Catalog tab: browse full lis-skins catalog with pagination, sidebar, sort, search
import { fmtRub } from './utils.js';
import { events } from './events.js';
import { cacheCatalogItems } from './lists.js';

// Module state
let _category = '';      // '' means all
let _sort = 'name_asc';
let _state = 'all';      // all | normal | stattrak | souvenir
let _model = '';
let _query = '';
let _offset = 0;
const _limit = 50;
let _searchTimeout = null;
let _loaded = false;     // lazy load: only fetch when tab first activated

const CAT_LABELS = {
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
  other: 'Другое'
};

const MODEL_FILTER_CATEGORIES = new Set(['rifle', 'pistol', 'smg', 'shotgun', 'machinegun', 'knife']);

// Category emoji placeholders (lis-skins JSON has no images)
const CAT_EMOJI = {
  rifle: '🔫', smg: '🔫', pistol: '🔫', shotgun: '🔫', machinegun: '🔫',
  knife: '🔪', gloves: '🧤', agent: '🕵️', sticker: '🏷️',
  case: '📦', key: '🔑', graffiti: '🎨', music_kit: '🎵',
  patch: '🎖️', other: '❓',
};

// --- Fetch + render ---

export async function loadCatalog() {
  try {
    const params = new URLSearchParams({
      limit: String(_limit),
      offset: String(_offset),
      sort: _sort
    });
    if (_category) params.set('category', _category);
    if (_state && _state !== 'all') params.set('state', _state);
    if (_model && MODEL_FILTER_CATEGORIES.has(_category)) params.set('model', _model);
    if (_query) params.set('q', _query);

    const r = await fetch('/api/catalog?' + params);
    const d = await r.json();

    renderSidebar(d.categories, d.total);
    renderModelFilter(d.models || []);
    renderGrid(d.items);
    cacheCatalogItems(d.items);
    renderPagination(d.total, d.offset, d.limit);

    events.emit('catalog:loaded', { total: d.total });
  } catch (e) {
    console.error('loadCatalog:', e);
  }
}

function renderSidebar(categories, total) {
  const sidebar = document.getElementById('catalogSidebar');
  if (!sidebar) return;

  // Update "All" count
  const allCount = document.getElementById('catCountAll');
  if (allCount) allCount.textContent = total.toLocaleString();

  // Remove old dynamic buttons (keep title + All button)
  const existing = sidebar.querySelectorAll('.sidebar-item[data-category]:not([data-category=""])');
  existing.forEach(el => el.remove());

  // Sort categories by count descending
  const sorted = Object.entries(categories)
    .sort((a, b) => b[1] - a[1]);

  for (const [cat, count] of sorted) {
    const label = CAT_LABELS[cat] || cat;
    const btn = document.createElement('button');
    btn.className = 'sidebar-item' + (_category === cat ? ' active' : '');
    btn.dataset.category = cat;
    btn.innerHTML = '<span class="sidebar-name">' + label + '</span>' +
      '<span class="sidebar-count">' + count.toLocaleString() + '</span>';
    sidebar.appendChild(btn);
  }

  // Update active state on All button
  const allBtn = sidebar.querySelector('[data-category=""]');
  if (allBtn) {
    allBtn.classList.toggle('active', _category === '');
  }
}

function renderGrid(items) {
  const grid = document.getElementById('catalogGrid');
  if (!grid) return;

  if (!items || items.length === 0) {
    grid.innerHTML = '<div class="empty-state">Ничего не найдено</div>';
    return;
  }

  let html = '';
  for (const item of items) {
    const emoji = CAT_EMOJI[item.category] || '❓';
    const imgHtml = item.image
      ? '<img class="cat-card-img" src="' + item.image + '" loading="lazy" alt="">'
      : '<div class="cat-card-img-placeholder">' + emoji + '</div>';
    const countCls = item.count > 0 ? '' : ' unavailable';
    const safeName = (item.name || '').replace(/"/g, '&quot;');

    html += '<div class="cat-card" data-item-name="' + safeName + '">' +
      '<div class="cat-card-actions">' +
        '<button class="list-toggle" data-list="favorite" data-name="' + safeName + '" title="Favorite">&#9825;</button>' +
        '<button class="list-toggle" data-list="wishlist" data-name="' + safeName + '" title="Wishlist">&#9734;</button>' +
      '</div>' +
      imgHtml +
      '<div class="cat-card-name">' + item.name + '</div>' +
      '<div class="cat-card-bottom">' +
        '<div class="cat-card-price">' + fmtRub(item.price_rub) + '</div>' +
        '<div class="cat-card-meta">' +
          '<div class="cat-card-category">' + (CAT_LABELS[item.category] || item.category) + '</div>' +
          '<div class="cat-card-count' + countCls + '">' + item.count + ' шт.</div>' +
        '</div>' +
      '</div>' +
    '</div>';
  }

  grid.innerHTML = html;
}

function renderPagination(total, offset, limit) {
  const container = document.getElementById('catalogPagination');
  if (!container) return;

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  if (totalPages <= 1) {
    container.innerHTML = '';
    return;
  }

  let html = '';

  // Prev button
  html += '<button class="cat-page-btn" data-page="' + (currentPage - 1) + '"' +
    (currentPage <= 1 ? ' disabled' : '') + '>&laquo;</button>';

  // Page buttons: first, ... , current-2..current+2, ... , last
  const pages = _buildPageRange(currentPage, totalPages);
  for (const p of pages) {
    if (p === '...') {
      html += '<span class="cat-page-info">...</span>';
    } else {
      html += '<button class="cat-page-btn' + (p === currentPage ? ' active' : '') +
        '" data-page="' + p + '">' + p + '</button>';
    }
  }

  // Info
  const from = offset + 1;
  const to = Math.min(offset + limit, total);
  html += '<span class="cat-page-info">' + from + '-' + to + ' of ' + total.toLocaleString() + '</span>';

  // Next button
  html += '<button class="cat-page-btn" data-page="' + (currentPage + 1) + '"' +
    (currentPage >= totalPages ? ' disabled' : '') + '>&raquo;</button>';

  container.innerHTML = html;
}

function _buildPageRange(current, total) {
  const pages = [];
  const show = new Set();

  // Always show first and last
  show.add(1);
  show.add(total);

  // Show 2 around current
  for (let i = current - 2; i <= current + 2; i++) {
    if (i >= 1 && i <= total) show.add(i);
  }

  const sorted = [...show].sort((a, b) => a - b);
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) {
      pages.push('...');
    }
    pages.push(sorted[i]);
  }

  return pages;
}

function renderModelFilter(models) {
  const select = document.getElementById('catalogModel');
  if (!select) return;

  const enabled = MODEL_FILTER_CATEGORIES.has(_category) && models.length > 0;
  select.disabled = !enabled;
  select.parentElement?.classList.toggle('is-disabled', !enabled);

  const currentExists = models.some(model => model.name === _model);
  if (_model && !currentExists) {
    _model = '';
  }

  const options = ['<option value="">Все модели</option>'];
  for (const model of models) {
    options.push('<option value="' + model.name + '">' + model.name + ' · ' + model.count + '</option>');
  }
  select.innerHTML = options.join('');
  select.value = _model;
}

// --- Init: event listeners ---

export function initCatalog() {
  // Sidebar click delegation
  const sidebar = document.getElementById('catalogSidebar');
  if (sidebar) {
    sidebar.addEventListener('click', (e) => {
      const btn = e.target.closest('.sidebar-item');
      if (!btn) return;
      const cat = btn.dataset.category;
      if (cat === undefined) return;
      _category = cat;
      _model = '';
      _offset = 0;
      // Update active class
      sidebar.querySelectorAll('.sidebar-item').forEach(el => {
        el.classList.toggle('active', el.dataset.category === cat);
      });
      loadCatalog();
    });
  }

  // Pagination click delegation
  const pagination = document.getElementById('catalogPagination');
  if (pagination) {
    pagination.addEventListener('click', (e) => {
      const btn = e.target.closest('.cat-page-btn');
      if (!btn || btn.disabled) return;
      const page = parseInt(btn.dataset.page, 10);
      if (isNaN(page) || page < 1) return;
      _offset = (page - 1) * _limit;
      loadCatalog();
      const grid = document.getElementById('catalogGrid');
      if (grid) grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  // Sort dropdown
  const sortSelect = document.getElementById('catalogSort');
  if (sortSelect) {
    sortSelect.addEventListener('change', () => {
      _sort = sortSelect.value;
      _offset = 0;
      loadCatalog();
    });
  }

  // State dropdown (StatTrak / Souvenir / Normal)
  const stateSelect = document.getElementById('catalogState');
  if (stateSelect) {
    stateSelect.addEventListener('change', () => {
      _state = stateSelect.value;
      _offset = 0;
      loadCatalog();
    });
  }

  const modelSelect = document.getElementById('catalogModel');
  if (modelSelect) {
    modelSelect.addEventListener('change', () => {
      _model = modelSelect.value;
      _offset = 0;
      loadCatalog();
    });
  }

  // Search input (debounced 400ms)
  const searchInput = document.getElementById('catalogSearch');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      clearTimeout(_searchTimeout);
      _searchTimeout = setTimeout(() => {
        _query = searchInput.value.trim();
        _offset = 0;
        loadCatalog();
      }, 400);
    });
  }

  // Lazy load on tab activation
  window.addEventListener('hashchange', () => {
    if (location.hash === '#catalog' && !_loaded) {
      _loaded = true;
      loadCatalog();
    }
  });

  // Check on init if already on catalog tab
  if (location.hash === '#catalog') {
    _loaded = true;
    loadCatalog();
  }
}
