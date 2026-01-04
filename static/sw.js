const CACHE_NAME = 'l8tetools-v1';
const OFFLINE_URL = '/offline';

const ASSETS_TO_CACHE = [
    OFFLINE_URL,
    '/dashboard',
    '/static/style.css',
    '/static/script.js',
    '/static/search.js',
    '/static/manifest.json',
    '/static/icon-192.png',
    '/static/icon-512.png',
    // Tools that work offline
    '/tools/dice-roller',
    '/tools/wheel-of-fortune',
    '/tools/score-tracker',
    '/tools/color-picker',
    '/tools/bmi-calculator',
    '/tools/workday-calculator',
    '/tools/text-sorter',
    '/tools/regex-replacer',
    '/tools/morse-code',
    '/tools/notes',
    '/tools/prefix-suffix'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    // Handling navigation requests (HTML pages)
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .catch(() => {
                    return caches.match(event.request)
                        .then((cachedResponse) => {
                            if (cachedResponse) {
                                return cachedResponse;
                            }
                            // Fallback to offline page
                            return caches.match(OFFLINE_URL);
                        });
                })
        );
        return;
    }

    // Passive caching for other resources (stale-while-revalidate strategy)
    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            const fetchPromise = fetch(event.request).then((networkResponse) => {
                // Check if we received a valid response
                if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
                    return networkResponse;
                }

                // Clone response to cache it
                const responseToCache = networkResponse.clone();
                caches.open(CACHE_NAME).then((cache) => {
                    // Only cache static assets or tool pages, don't cache API calls generally unless specific?
                    // For simplicity, we cache everything mostly, but avoid API mutations.
                    if (event.request.method === 'GET' && !event.request.url.includes('/api/')) {
                        cache.put(event.request, responseToCache);
                    }
                });
                return networkResponse;
            }).catch(() => {
                // If network fails (and no cache processing yet), return nothing (will hit cache match return eventually?)
                // Actually cachedResponse is returned immediately if found in cache-first/stale strategies.
                // But here we are doing: return cached || fetch.
                // Wait, Stale-While-Revalidate logic is usually:
                // return cachedResponse || fetchPromise (if cached is null)
                // BUT we want to update cache in background.
            });

            return cachedResponse || fetchPromise;
        })
    );
});
