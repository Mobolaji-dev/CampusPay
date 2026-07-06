const CACHE_NAME = 'campuspay-v1.1';
const PRECACHE_URLS = [
  '/', '/index.html', '/signup.html', '/dashboard.html', '/vendor.html', '/catalogue.html', '/purchase.html','/success.html','/pending.html','/profile.html','/pin.html', '/receipt.html', '/transactions.html',


  '/styles/login.css', '/styles/signup.css', '/styles/dashboard.css', '/styles/vendor.css',
  '/styles/catalogue.css', '/styles/purchase.css', '/styles/success.css', '/styles/pending.css',
  '/styles/profile.css', '/styles/pin.css', '/styles/receipt.css', '/styles/transactions.css',

  '/scripts/index.js', '/scripts/signup.js', '/scripts/dashboard.js',
  '/scripts/profile.js', '/scripts/pin.js', '/scripts/auth.js', '/scripts/firebaseAuth.js', '/scripts/transactions.js', '/scripts/pending.js', '/scripts/vendor.js', '/scripts/catalogue.js', '/scripts/success.js', '/scripts/receipt.js', '/scripts/purchase.js' , '/scripts/pwa.js',

  '/manifest.json',
  '/icons/Icon_1.png', '/icons/Icon_2.png' , '/icons/Icon_3.png'
];


self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return Promise.all(
        PRECACHE_URLS.map((url) =>
          cache.add(url).catch((err) => console.warn('Failed to cache:', url, err))
        )
      );
    })
  );
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