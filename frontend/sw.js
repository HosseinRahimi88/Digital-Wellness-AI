/*
  Minimal service worker: exists only so the app is installable as a
  PWA (a fetch handler is part of most browsers' install criteria).
  Deliberately does NOT cache anything or serve offline - offline
  support was explicitly out of scope for v1; every request just
  passes straight through to the network.
*/
self.addEventListener('install', (e) => self.skipWaiting());
self.addEventListener('activate', (e) => self.clients.claim());
self.addEventListener('fetch', (e) => {
  e.respondWith(fetch(e.request));
});
