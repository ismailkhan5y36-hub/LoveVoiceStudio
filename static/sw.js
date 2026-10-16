const CACHE_NAME = 'lovevoice-v1';
const ASSETS = [
  '/',
  '/static/index.html',
  '/static/manifest.json',
  '/static/icon.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', event => {
  // Let API calls go to network
  if (event.request.url.includes('/api/') || event.request.url.includes('/outputs/')) {
    return;
  }
  event.respondWith(
    caches.match(event.request).then(response => response || fetch(event.request))
  );
});
