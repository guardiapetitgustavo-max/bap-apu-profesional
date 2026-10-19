// Service worker: guarda la interfaz para abrir rápido; los datos siempre vienen de Supabase.
const VERSION = "bap-apu-v3";
const ARCHIVOS = ["/app", "/app.html", "/app.js", "/styles.css", "/config.js", "/semilla.js", "/manifest.webmanifest",
  "/assets/bap_isotipo.png", "/assets/bap_logo_principal.png", "/assets/icono-192.png", "/assets/icono-512.png"];
self.addEventListener("install", (e) => e.waitUntil(caches.open(VERSION).then((c) => Promise.allSettled(ARCHIVOS.map((a) => c.add(a)))).then(() => self.skipWaiting())));
self.addEventListener("activate", (e) => e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  // Red primero (para recibir actualizaciones); si no hay conexión, la copia guardada.
  e.respondWith(fetch(e.request).then((r) => { const copia = r.clone(); caches.open(VERSION).then((c) => c.put(e.request, copia)); return r; })
    .catch(() => caches.match(e.request).then((r) => r || caches.match("/app.html"))));
});
