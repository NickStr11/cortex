const CACHE_NAME = 'sniper-v9';
const STATIC_ASSETS = [
  '/static/css/styles.css',
  '/static/js/main.js',
  '/static/js/catalog.js',
  '/static/js/cases.js',
  '/static/js/lists.js',
  '/static/js/watchlist.js',
  '/static/js/search.js',
  '/static/js/chart.js',
  '/static/js/modal.js',
  '/static/js/alerts.js',
  '/static/js/stats.js',
  '/static/js/router.js',
  '/static/js/events.js',
  '/static/js/utils.js',
  '/static/js/state.js',
  '/static/js/item_detail.js',
  '/static/js/theme.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/logo.png',
  '/static/manifest.json',
];

// Install: pre-cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: network-first for static/HTML/API, fall back to cache offline.
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Static assets: network-first to avoid stale JS after deploys.
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // HTML and API: network-first, fall back to cache
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Cache HTML responses for offline fallback
        if (event.request.mode === 'navigate') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
