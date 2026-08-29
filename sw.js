/**
 * SatyaScan Service Worker (sw.js)
 * -------------------------------------------------------------
 * ARCHITECTURAL NOTE ON OFFLINE OCR:
 * The SatyaScan app shell, styles, and cached past scan results are available
 * 100% offline via this Service Worker and browser localStorage caching.
 *
 * NOTE FOR FULL ON-DEVICE OFFLINE SCANNING:
 * Currently, heavy deep-learning OCR (EasyOCR with PyTorch) runs on the FastAPI backend
 * (/scan endpoint). To achieve 100% offline text extraction from newly captured images
 * without reaching any backend server, client-side OCR would need to run directly in the
 * browser using WebAssembly / Web Workers (such as Tesseract.js or ONNX Runtime Web with
 * a quantized OCR model), coupled with client-side JavaScript ports of extract_fields.py
 * and compliance.py.
 *
 * For now, previously scanned label results and audit history are cached locally in
 * localStorage so inspectors/consumers can review compliance reports offline anytime.
 * -------------------------------------------------------------
 */

const CACHE_NAME = 'satyascan-app-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/manifest.json'
];

// 1. Install Event: Pre-cache App Shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SatyaScan SW] Pre-caching app shell assets');
      return cache.addAll(ASSETS_TO_CACHE);
    }).then(() => self.skipWaiting())
  );
});

// 2. Activate Event: Clean up outdated caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            console.log('[SatyaScan SW] Deleting legacy cache:', name);
            return caches.delete(name);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// 3. Fetch Event: Stale-While-Revalidate / Cache-First for static assets
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET and API mutation requests (like /scan)
  if (event.request.method !== 'GET') {
    return;
  }

  // Handle App Shell and Static Assets
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        // Fetch background update for cache (Stale-While-Revalidate)
        fetch(event.request)
          .then((networkResponse) => {
            if (networkResponse && networkResponse.status === 200) {
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(event.request, networkResponse);
              });
            }
          })
          .catch(() => {
            // Ignore network errors when offline
          });
        return cachedResponse;
      }

      // Network fallback with dynamic caching for fonts and assets
      return fetch(event.request)
        .then((networkResponse) => {
          if (
            networkResponse &&
            networkResponse.status === 200 &&
            (url.origin === location.origin || url.hostname.includes('fonts.googleapis.com') || url.hostname.includes('fonts.gstatic.com'))
          ) {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseClone);
            });
          }
          return networkResponse;
        })
        .catch(() => {
          // If offline and requesting navigation, return cached index.html
          if (event.request.mode === 'navigate') {
            return caches.match('/index.html') || caches.match('/');
          }
        });
    })
  );
});
