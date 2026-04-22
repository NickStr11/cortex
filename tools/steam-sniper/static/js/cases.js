// Cases tab: browse CS2 cases with price trends, pagination, sort, search
import { fmtRub } from './utils.js';
import { events } from './events.js';
import { cacheCatalogItems } from './lists.js';

// Module state
let _sort = 'name_asc';
let _query = '';
let _offset = 0;
const _limit = 50;
let _searchTimeout = null;
let _loaded = false;

// --- Fetch + render ---

export async function loadCases() {
  try {
    const params = new URLSearchParams({
      limit: String(_limit),
      offset: String(_offset),
      sort: _sort,
      category: 'case'
    });
    if (_query) params.set('q', _query);

    const r = await fetch('/api/catalog?' + params);
    const d = await r.json();

    renderCasesGrid(d.items);
    cacheCatalogItems(d.items);
    renderCasesPagination(d.total, d.offset, d.limit);

    events.emit('cases:loaded', { total: d.total });
  } catch (e) {
    console.error('loadCases:', e);
  }
}

function renderCasesGrid(items) {
  const grid = document.getElementById('casesGrid');
  if (!grid) return;

  if (!items || items.length === 0) {
    grid.innerHTML = '<div class="empty-state">No cases found</div>';
    return;
  }

  let html = '';
  for (const item of items) {
    const imgHtml = item.image
      ? '<img class="cat-card-img" src="' + item.image + '" loading="lazy" alt="">'
      : '<div class="cat-card-img-empty">\ud83d\udce6</div>';
    const countCls = item.count > 0 ? '' : ' unavailable';
    const safeName = (item.name || '').replace(/"/g, '&quot;');

    // Trend badge
    let trendHtml = '';
    if (item.trend) {
      const dir = item.trend.direction;
      const pct = item.trend.pct;
      let arrow = '';
      let pctText = '';
      if (dir === 'up') {
        arrow = '\u2191';
        pctText = '+' + pct.toFixed(1) + '%';
      } else if (dir === 'down') {
        arrow = '\u2193';
        pctText = pct.toFixed(1) + '%';
      } else {
        arrow = '\u2194';
        pctText = '0.0%';
      }
      trendHtml = '<div class="cat-card-trend">' +
        '<span class="trend trend-' + dir + '">' + arrow + ' ' + pctText + '</span>' +
        '</div>';
    }

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
          '<div class="cat-card-count' + countCls + '">' + item.count + ' qty</div>' +
        '</div>' +
      '</div>' +
      trendHtml +
    '</div>';
  }

  grid.innerHTML = html;
}

function renderCasesPagination(total, offset, limit) {
  const container = document.getElementById('casesPagination');
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

  // Page buttons
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

  show.add(1);
  show.add(total);

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

// --- Init: event listeners ---

export function initCases() {
  // Pagination click delegation
  const pagination = document.getElementById('casesPagination');
  if (pagination) {
    pagination.addEventListener('click', (e) => {
      const btn = e.target.closest('.cat-page-btn');
      if (!btn || btn.disabled) return;
      const page = parseInt(btn.dataset.page, 10);
      if (isNaN(page) || page < 1) return;
      _offset = (page - 1) * _limit;
      loadCases();
      const grid = document.getElementById('casesGrid');
      if (grid) grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  // Sort dropdown
  const sortSelect = document.getElementById('casesSort');
  if (sortSelect) {
    sortSelect.addEventListener('change', () => {
      _sort = sortSelect.value;
      _offset = 0;
      loadCases();
    });
  }

  // Search input (debounced 400ms)
  const searchInput = document.getElementById('casesSearch');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      clearTimeout(_searchTimeout);
      _searchTimeout = setTimeout(() => {
        _query = searchInput.value.trim();
        _offset = 0;
        loadCases();
      }, 400);
    });
  }

  // Lazy load on tab activation
  window.addEventListener('hashchange', () => {
    if (location.hash === '#cases' && !_loaded) {
      _loaded = true;
      loadCases();
    }
  });

  // Check on init if already on cases tab
  if (location.hash === '#cases') {
    _loaded = true;
    loadCases();
  }
}
