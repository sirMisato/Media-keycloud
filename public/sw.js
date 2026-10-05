'use strict';
const CACHE = 'mahad-shell-v2';
const ASSETS = ['/offline.html', '/assets/app.css', '/assets/media.css', '/assets/app.js', '/icons/icon-192.png', '/icons/icon-512.png'];
self.addEventListener('install', event => {
    event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)));
    self.skipWaiting();
});
self.addEventListener('activate', event => {
    event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('mahad-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    // Editorial sessions, all uploaded covers and health checks always bypass PWA caching.
    if (event.request.method !== 'GET' || url.origin !== self.location.origin || /^\/(redaksi|masuk|media|up)(\/|$)/.test(url.pathname)) return;
    // HTML remains network-only: withdrawn publications must not survive in an offline cache.
    if (event.request.mode === 'navigate') {
        event.respondWith(fetch(event.request).catch(() => caches.match('/offline.html')));
        return;
    }
    // Only the public shell is cached. Asset hashes can change on every release.
    if (ASSETS.includes(url.pathname) && (!url.search || /^\?v=[a-f0-9]{12}$/.test(url.search))) {
        const response = fetch(event.request);
        event.waitUntil(response.then(async result => {
            if (result.ok) { const cache = await caches.open(CACHE); await cache.put(url.pathname, result.clone()); }
        }).catch(() => {}));
        event.respondWith(response.catch(() => caches.match(url.pathname)));
    }
});
