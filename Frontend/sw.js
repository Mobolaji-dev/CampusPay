const CACHE_NAME = 'campuspay-v1';
const PRECACHE_URLS = [
  '/', '/index.html', '/signup.html', '/dashboard.html', '/vendor.html', '/catalogue.html', '/purchase.html','/payment.html','/pending.html','/profile.html','/pin.html', '/receipt.html', '/transaction.html',


  '/styles/index.css', '/styles/signup.css', '/styles/dashboard.css', '/styles/vendor.css',
  '/styles/catalogue.css', '/styles/purchase.css', '/styles/payment.css', '/styles/pending.css',
  '/styles/profile.css', '/styles/pin.css', '/styles/receipt.css', '/styles/transaction.css',

  '/scripts/index.js', '/scripts/signup.js', '/scripts/dashboard.js',
  '/scripts/profile.js', '/scripts/pin.js', '/scripts/auth.js', '/scripts/firebaseAuth.js', 'scripts/pwa.js',

  '/manifest.json',
  '/icons/icon-1_png', '/icons/icon_2.png' , '/icons/icon_3.png'
];


self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.url.includes('/api/')) {
    event.respondWith(fetch(request).catch(() => caches.match(request)));
    return;
  }
  event.respondWith(caches.match(request).then((cached) => cached || fetch(request)));
});