import { state } from './state.js';
import { fmtRub } from './utils.js';
import { openModal } from './modal.js';

export function initSearch() {
  const searchInput = document.getElementById('searchInput');
  const searchResults = document.getElementById('searchResults');

  searchInput.addEventListener('input', () => {
    clearTimeout(state.searchTimeout);
    state.searchTimeout = setTimeout(() => doSearch(searchInput, searchResults), 200);
  });

  searchInput.addEventListener('focus', () => {
    if (searchResults.children.length) searchResults.classList.add('active');
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-section')) searchResults.classList.remove('active');
  });

  // Delegated click on search results
  searchResults.addEventListener('click', (e) => {
    const row = e.target.closest('.search-result');
    if (!row) return;
    const idx = parseInt(row.getAttribute('data-search-idx'));
    const results = searchResults._results || [];
    if (results[idx]) openModal(results[idx]);
  });
}

async function doSearch(searchInput, searchResults) {
  const q = searchInput.value.trim();
  if (q.length < 2) {
    searchResults.classList.remove('active');
    return;
  }

  try {
    const r = await fetch('/api/search?q=' + encodeURIComponent(q));
    const d = await r.json();
    const results = d.results || [];

    if (!results.length) {
      searchResults.innerHTML = '<div style="padding:16px;color:var(--text-dim);text-align:center">Nothing found</div>';
      searchResults.classList.add('active');
      return;
    }

    searchResults.innerHTML = '<div class="sr-grid">' + results.map((item, i) => {
      const showName = item.name_ru || item.name;
      const img = item.image
        ? '<img class="sr-img" src="' + item.image + '" loading="lazy" alt="">'
        : '<div class="sr-img sr-img-empty"></div>';
      const priceText = item.price_rub != null ? fmtRub(item.price_rub) : '<span class="sr-na">\u043D\u0435\u0442 \u043D\u0430 lis-skins</span>';
      const typeText = item.type_ru ? '<div class="sr-type">' + item.type_ru + '</div>' : '';
      const countText = item.count ? item.count + ' \u0448\u0442' : '';
      const colorStyle = item.name_color ? 'border-bottom:2px solid #' + item.name_color : '';
      return '<div class="search-result" data-search-idx="' + i + '" style="' + colorStyle + '">' +
        img +
        '<div class="sr-info">' +
          '<div class="sr-name">' + showName + '</div>' +
          typeText +
          '<div class="sr-bottom">' +
            '<span class="sr-price">' + priceText + '</span>' +
            '<span class="sr-count">' + countText + '</span>' +
          '</div>' +
        '</div>' +
      '</div>';
    }).join('') + '</div>';

    searchResults._results = results;
    searchResults.classList.add('active');
  } catch (e) { console.error('doSearch:', e); }
}
