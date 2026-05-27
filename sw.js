// SPX Rotation Calculator — Service Worker
// Enables offline use and home screen installation

const CACHE = 'spx-rotate-v14';
const ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  'https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600;700&family=Bebas+Neue&display=swap',
];

// Install: cache core assets
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(cache => {
      return cache.addAll(ASSETS).catch(() => {
        // Font loading may fail offline — that's fine
        return cache.addAll(['/index.html', '/manifest.json']);
      });
    })
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: always network-first for data.json and APIs, cache-first for static assets
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // NEVER cache data.json — always fetch fresh
  if (url.pathname.includes('data.json')) {
    e.respondWith(
      fetch(e.request, { cache: 'no-store' }).catch(() =>
        new Response('{}', { headers: { 'Content-Type': 'application/json' } })
      )
    );
    return;
  }

  // Always network for external APIs
  if (
    url.hostname.includes('stlouisfed.org') ||
    url.hostname.includes('alphavantage.co') ||
    url.hostname.includes('er-api.com')
  ) {
    e.respondWith(
      fetch(e.request).catch(() =>
        new Response(JSON.stringify({ error: 'offline' }), {
          headers: { 'Content-Type': 'application/json' }
        })
      )
    );
    return;
  }

  // Cache-first for static app assets (HTML, JS, icons)
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(response => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE).then(cache => cache.put(e.request, clone));
        }
        return response;
      }).catch(() => caches.match('/index.html'));
    })
  );
});

// Push notifications (future: server-sent)
self.addEventListener('push', e => {
  const data = e.data ? e.data.json() : {};
  e.waitUntil(
    self.registration.showNotification(data.title || 'SPX Rotate', {
      body: data.body || 'Rotation conditions have changed.',
      icon: 'icon-192.png',
      badge: 'icon-192.png',
      vibrate: [200, 100, 200],
      data: { url: '/' }
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(clients.openWindow('/'));
});
