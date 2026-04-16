import { events } from './events.js';
import { loadStats } from './stats.js';
import { loadWatchlist, initWatchlist } from './watchlist.js';
import { loadAlerts } from './alerts.js';
import { initSearch } from './search.js';
import { initChart } from './chart.js';
import { initModal } from './modal.js';
import { initCatalog } from './catalog.js';
import { initCases } from './cases.js';
import { initLists, loadUserLists, updateCardIndicators } from './lists.js';
import { initRouter } from './router.js';

async function init() {
  // Initialize all modules (register event listeners)
  initWatchlist();
  initSearch();
  initChart();
  initModal();
  initCatalog();
  initCases();
  initLists();

  // Load initial data
  await Promise.all([loadStats(), loadWatchlist(), loadAlerts(), loadUserLists()]);

  // Initialize router (after data loaded, so panels have content)
  initRouter();

  // Auto-refresh every 5 minutes
  setInterval(() => {
    Promise.all([loadStats(), loadWatchlist(), loadAlerts(), loadUserLists()]);
  }, 300000);

  // Cross-module event wiring
  events.on('watchlist:changed', async () => {
    await Promise.all([loadWatchlist(), loadStats()]);
  });

  events.on('lists:loaded', () => {
    updateCardIndicators();
  });

  events.on('catalog:loaded', () => {
    updateCardIndicators();
  });

  events.on('cases:loaded', () => {
    updateCardIndicators();
  });
}

init();
