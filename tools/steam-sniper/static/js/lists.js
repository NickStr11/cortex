// Lists module: favorites + wishlist state, toggle logic, tab rendering, indicator sync
import { fmtRub } from './utils.js';
import { events } from './events.js';

// Hardcoded user (2-person app, no auth)
const USER = 'lesha';

// In-memory sets for O(1) lookup
let _favorites = new Set();
let _wishlist = new Set();
let _favoriteItems = [];
let _wishlistItems = [];

// Price cache: populated by catalog.js after each loadCatalog
let _priceCache = new Map(); // name -> { price_rub, url, category, count, name }

// --- Exports ---

/**
 * Check if item is in a list. Synchronous O(1).
 */
export function isInList(itemName, listType) {
  if (listType === 'favorite') return _favorites.has(itemName);
  if (listType === 'wishlist') return _wishlist.has(itemName);
  return false;
}

/**
 * Cache catalog items for list tab rendering (called by catalog.js).
 */
export function cacheCatalogItems(items) {
  for (const it of items) {
    _priceCache.set(it.name, it);
  }
}

/**
 * Load both lists from API. Rebuilds in-memory sets.
 */
export async function loadUserLists() {
  try {
    const [favRes, wishRes] = await Promise.all([
      fetch(`/api/lists?user=${USER}&type=favorite`),
      fetch(`/api/lists?user=${USER}&type=wishlist`),
    ]);
    const favData = await favRes.json();
    const wishData = await wishRes.json();

    _favorites = new Set(favData.items.map(i => i.item_name));
    _wishlist = new Set(wishData.items.map(i => i.item_name));
    _favoriteItems = favData.items || [];
    _wishlistItems = wishData.items || [];

    events.emit('lists:loaded');
  } catch (e) {
    console.error('loadUserLists:', e);
  }
}

/**
 * Update all .list-toggle buttons in the DOM to reflect current list state.
 */
export function updateCardIndicators() {
  const buttons = document.querySelectorAll('.list-toggle');
  for (const btn of buttons) {
    const listType = btn.dataset.list;
    const name = btn.dataset.name;
    if (!listType || !name) continue;

    const inList = isInList(name, listType);

    if (listType === 'favorite') {
      btn.classList.toggle('active-fav', inList);
      btn.innerHTML = inList ? '\u2665' : '\u2661';
    } else if (listType === 'wishlist') {
      btn.classList.toggle('active-wish', inList);
      btn.innerHTML = inList ? '\u2605' : '\u2606';
    }
  }
}

// --- Internal ---

async function toggleListItem(itemName, listType) {
  const inList = isInList(itemName, listType);

  // Optimistic UI: update set + DOM immediately
  const set = listType === 'favorite' ? _favorites : _wishlist;
  if (inList) {
    set.delete(itemName);
  } else {
    set.add(itemName);
  }

  // Update all matching buttons (may exist in catalog + list tab)
  const selector = `.list-toggle[data-list="${listType}"][data-name="${CSS.escape(itemName)}"]`;
  const buttons = document.querySelectorAll(selector);
  for (const btn of buttons) {
    if (listType === 'favorite') {
      btn.classList.toggle('active-fav', !inList);
      btn.innerHTML = !inList ? '\u2665' : '\u2661';
    } else {
      btn.classList.toggle('active-wish', !inList);
      btn.innerHTML = !inList ? '\u2605' : '\u2606';
    }
  }

  // API call
  try {
    if (inList) {
      await fetch('/api/lists', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user: USER, item_name: itemName, list_type: listType }),
      });
    } else {
      await fetch('/api/lists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user: USER, item_name: itemName, list_type: listType }),
      });
    }
    await loadUserLists();
  } catch (e) {
    // Revert on error
    console.error('toggleListItem:', e);
    if (inList) {
      set.add(itemName);
    } else {
      set.delete(itemName);
    }
    updateCardIndicators();
    return;
  }

  events.emit('lists:changed', { itemName, listType, action: inList ? 'removed' : 'added' });
}

function renderListTab(listType, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const items = listType === 'favorite' ? _favoriteItems : _wishlistItems;

  if (items.length === 0) {
    const msg = listType === 'favorite'
      ? 'No favorites yet -- click \u2661 on catalog cards'
      : 'Wishlist is empty -- click \u2606 on catalog cards';
    container.innerHTML = `<div class="empty-state">${msg}</div>`;
    return;
  }

  const title = listType === 'favorite' ? 'Favorites' : 'Wishlist';
  let html = `<div class="list-tab-header"><span class="section-title">${title} <span class="badge">${items.length}</span></span></div>`;
  html += '<div class="list-tab-grid">';

  for (const item of items) {
    const name = item.item_name;
    const cached = _priceCache.get(name);
    const merged = cached ? { ...item, ...cached } : item;
    const imgSrc = merged.image || '';
    const imgHtml = imgSrc
      ? `<img class="cat-card-img" src="${imgSrc}" loading="lazy" alt="">`
      : '<div class="cat-card-img-empty"></div>';
    const price = merged.price_rub != null ? fmtRub(merged.price_rub) : '--';
    const catBadge = merged.category || '';
    const count = merged.count ?? '?';
    const safeName = name.replace(/"/g, '&quot;');

    html += `<div class="cat-card" data-item-name="${safeName}">
      <div class="cat-card-actions">
        <button class="list-toggle ${listType === 'favorite' ? 'active-fav' : 'active-wish'}"
          data-list="${listType}" data-name="${safeName}"
          title="Remove">${listType === 'favorite' ? '\u2665' : '\u2605'}</button>
      </div>
      ${imgHtml}
      <div class="cat-card-name">${name}</div>
      <div class="cat-card-bottom">
        <div class="cat-card-price">${price}</div>
        <div class="cat-card-meta">
          ${catBadge ? `<div class="cat-card-category">${catBadge}</div>` : ''}
          <div class="cat-card-count">${count} qty</div>
        </div>
      </div>
    </div>`;
  }

  html += '</div>';
  container.innerHTML = html;
}

// --- Init ---

export function initLists() {
  // Event delegation for .list-toggle clicks
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.list-toggle');
    if (!btn) return;
    e.stopPropagation();
    const name = btn.dataset.name;
    const listType = btn.dataset.list;
    if (name && listType) toggleListItem(name, listType);
  });

  // Re-render active list tab on lists:changed
  events.on('lists:changed', () => {
    if (location.hash === '#favorites') renderListTab('favorite', 'favoritesGrid');
    if (location.hash === '#wishlist') renderListTab('wishlist', 'wishlistGrid');
  });

  // Render list tab on hashchange
  window.addEventListener('hashchange', () => {
    if (location.hash === '#favorites') renderListTab('favorite', 'favoritesGrid');
    if (location.hash === '#wishlist') renderListTab('wishlist', 'wishlistGrid');
  });
}
