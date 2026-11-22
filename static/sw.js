const CACHE = 'hiremate-v1';
const CDN_CACHE = 'hiremate-cdn-v1';

const CDN_URLS = [
  'https://cdn.tailwindcss.com/3.4.17',
  'https://cdnjs.cloudflare.com/ajax/libs/alpinejs/3.14.8/cdn.min.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CDN_CACHE).then(cache =>
      Promise.allSettled(CDN_URLS.map(url => cache.add(url)))
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE && k !== CDN_CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = e.request.url;

  if (CDN_URLS.some(cdn => url.startsWith(cdn)) || url.includes('fonts.gstatic.com')) {
    e.respondWith(
      caches.match(e.request).then(r => r || fetch(e.request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CDN_CACHE).then(c => c.put(e.request, clone));
        }
        return resp;
      }))
    );
    return;
  }

  if (url.includes('/static/')) {
    e.respondWith(
      caches.match(e.request).then(r => r || fetch(e.request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return resp;
      }))
    );
    return;
  }
});
