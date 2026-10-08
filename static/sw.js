// ============================================================
// GAMEWATCH™ OFFLINE-FIRST SERVICE WORKER (v2.0)
// Enables full functionality during internet outages & offline PWA
// ============================================================

const CACHE_NAME = 'gamewatch-cache-v3';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/js/offline_engine.js',
    '/static/img/logo.png',
    '/manifest.json'
];

// Install: Cache critical shell assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[GameWatch SW] Pre-caching offline application shell v2');
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

// Fetch: Stale-While-Revalidate for app shell, Network-First with Cache fallback for state
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Skip caching for video MJPEG streams and non-GET requests
    if (event.request.method !== 'GET' || url.pathname.startsWith('/api/stream/')) {
        return;
    }

    // For state and telemetry API calls: Network-First with Cache fallback
    if (url.pathname.startsWith('/api/state') || url.pathname.startsWith('/api/lounge_config')) {
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

    // For Static Shell Assets & Pages: Cache-First, fallback to Network, fallback to cached root
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
            return fetch(event.request).catch(() => {
                // If navigation fails completely offline, serve cached index
                if (event.request.mode === 'navigate') {
                    return caches.match('/');
                }
            });
        })
    );
});
