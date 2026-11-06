/* Offline cache: static shop files only. Never caches /api/ or Telegram scripts. */
const CACHE = 'el-static-__BUILD__';
self.addEventListener('install', e => { self.skipWaiting(); });
self.addEventListener('activate', e => e.waitUntil(
  caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('el-static-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())
));
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin || url.pathname.startsWith('/api/') || url.pathname === '/health') return;
  const isAsset = url.pathname.startsWith('/assets/');
  e.respondWith(caches.open(CACHE).then(async cache => {
    const hit = await cache.match(e.request);
    if (hit && isAsset) return hit;
    const fresh = fetch(e.request).then(r => { if (r.ok) cache.put(e.request, r.clone()); return r; });
    try { return await fresh; } catch (err) {
      if (hit) return hit;
      return e.request.mode === 'navigate' ? (await cache.match('/')) || Response.error() : Response.error();
    }
  }));
});
