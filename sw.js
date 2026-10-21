/* Zypuc: funciona sin internet con la última versión guardada.
   Siempre intenta traer lo más nuevo primero (precios frescos) y, si no hay conexión, usa la copia guardada. */
const VERSION = "zypuc-v6";
const BASE = ["./", "index.html", "productos.json", "precios.json", "logo-claro.png", "logo-oscuro.png", "icon-192.png", "icon-512.png", "favicon.svg", "manifest.webmanifest"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => Promise.allSettled(BASE.map(u => c.add(u)))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  e.respondWith(
    fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(VERSION).then(c => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req, { ignoreSearch: true }).then(r => r || caches.match("index.html")))
  );
});
