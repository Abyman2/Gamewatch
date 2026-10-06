// ============================================================
// GAMEWATCH™ OFFLINE-FIRST SERVICE WORKER (v1.0)
// Enables full functionality during internet outages
// ============================================================

const CACHE_NAME = 'gamewatch-cache-v1';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css?v=12',
    '/static/js/app.js',
    '/static/img/logo.png',
    '/manifest.json'
];

// Install: Cache critical shell assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[GameWatch SW] Pre-caching offline application shell');
            return cache.addAll(STATIC_ASSETS);
        }).then(() => self.skipWaiting())
    );
});

// Activate: Clean up old cache versions
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch: Stale-While-Revalidate for app shell, Network-First for API
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Skip caching for video MJPEG streams and non-GET requests
    if (event.request.method !== 'GET' || url.pathname.startsWith('/api/stream/')) {
        return;
    }

    // For API calls: Network-First with Cache fallback
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request)
                .then((response) => {
                    if (response && response.status === 200) {
                        const copy = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
                    }
                    return response;
                })
                .catch(() => caches.match(event.request))
        );
        return;
    }

    // For Static Shell Assets: Cache-First, fallback to Network
    event.respondWith(
        caches.match(event.request).then((cached) => {
            if (cached) {
                // Fetch fresh in background
                fetch(event.request).then((res) => {
                    if (res && res.status === 200) {
                        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, res));
                    }
                }).catch(() => {});
                return cached;
            }
            return fetch(event.request);
        })
    );
});
