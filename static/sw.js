const CACHE_NAME = 'lovevoice-v2';

self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  // Always network first so updates load instantly
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
