/**
 * CSA (Clinical-Stage Asset Intelligence) PWA Service Worker
 * Strategy: network-first pass-through for navigations, Stale-While-Revalidate
 * for same-origin subresources. Strict bypass for non-GET requests and
 * cross-origin endpoints (Web3Forms, Kaggle, Hugging Face, Google Fonts).
 *
 * Cloudflare Pages clean URLs: /page.html 308-redirects to /page. A service
 * worker must never answer a navigation with a redirected response (Chrome
 * fails it with net::ERR_FAILED), so the precache uses clean extensionless
 * URLs only, navigations pass the original Request through (the browser
 * handles the 308 itself), and redirected responses are never written to or
 * served from the cache.
 */

const CACHE_NAME = 'csa-public-cache-v2026.07.1';
const CORE_ASSETS = [
  '/',
  '/favicon.svg',
  '/og-image.png',
  '/samples/catalyst_calendar_sample.csv',
  '/sitemap.xml',
  '/site.webmanifest'
];

const cacheable = res => res && res.status === 200 && !res.redirected && res.type === 'basic';

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      cache.addAll(CORE_ASSETS.map(url => new Request(url, { cache: 'reload' }))).catch(() => {})
    )
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME && k.startsWith('csa-public-cache-')).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  if (req.mode === 'navigate') {
    const cleanPath = url.pathname.endsWith('.html')
      ? url.pathname.slice(0, -5).replace(/\/index$/, '/') : url.pathname;
    event.respondWith(
      fetch(req).then(res => {
        if (cacheable(res)) {
          const copy = res.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(cleanPath, copy));
        }
        return res;
      }).catch(() =>
        caches.match(cleanPath).then(cached => cached || caches.match('/'))
      )
    );
    return;
  }

  event.respondWith(
    caches.open(CACHE_NAME).then(cache =>
      cache.match(req).then(cached => {
        const network = fetch(req).then(res => {
          if (cacheable(res)) cache.put(req, res.clone());
          return res;
        }).catch(() => cached);
        return cached || network;
      })
    )
  );
});
