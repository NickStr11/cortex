// Hash-based tab router
// Tabs: watchlist (default), catalog, favorites, wishlist, cases
// Future phases add content to tab panels -- router just shows/hides them

const TABS = ['watchlist', 'catalog', 'favorites', 'wishlist', 'cases'];
const DEFAULT_TAB = 'watchlist';

function getTabFromHash() {
  const hash = window.location.hash.slice(1); // remove #
  return TABS.includes(hash) ? hash : DEFAULT_TAB;
}

function activateTab(tabId) {
  // Update nav active state
  document.querySelectorAll('.tab-nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.tab === tabId);
  });

  // Show/hide content panels
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.style.display = panel.dataset.tab === tabId ? '' : 'none';
  });
}

export function navigateTo(tabId) {
  if (!TABS.includes(tabId)) return;
  window.location.hash = tabId;
  // hashchange event will trigger activateTab
}

export function initRouter() {
  // Handle hash changes (including back/forward)
  window.addEventListener('hashchange', () => {
    activateTab(getTabFromHash());
  });

  // Nav click handler (event delegation on nav bar)
  const nav = document.querySelector('.tab-nav');
  if (nav) {
    nav.addEventListener('click', (e) => {
      const item = e.target.closest('.tab-nav-item');
      if (item) {
        navigateTo(item.dataset.tab);
      }
    });
  }

  // Activate initial tab from URL hash (or default)
  activateTab(getTabFromHash());
}
