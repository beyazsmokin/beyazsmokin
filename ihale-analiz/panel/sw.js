// İhale Analiz paneli: uygulama kabuğunu önbellekte tutar, sunucu kapalıyken son verileri gösterir.
const SURUM = "ihale-panel-v2";
const KABUK = ["/", "/app.js", "/stil.css", "/manifest.webmanifest", "/ikon-192.png", "/ikon-512.png",
  "/ikon-maskable.png", "/apple-touch-icon.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SURUM).then((c) => c.addAll(KABUK)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((ks) => Promise.all(ks.filter((k) => k !== SURUM).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function agOnce(istek) {
  const onbellek = await caches.open(SURUM);
  try {
    const yanit = await fetch(istek);
    if (yanit.ok) onbellek.put(istek, yanit.clone());
    return yanit;
  } catch (hata) {
    const eski = await onbellek.match(istek);
    if (!eski) throw hata;
    const basliklar = new Headers(eski.headers);
    basliklar.set("X-Onbellek", "1");
    return new Response(await eski.blob(), { status: 200, headers: basliklar });
  }
}

self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin) return;
  if (e.request.mode === "navigate") {
    e.respondWith(fetch(e.request).catch(() => caches.match("/")));
  } else if (u.pathname.startsWith("/api/") || u.pathname.startsWith("/dosya/")) {
    if (u.pathname === "/api/saglik") return;
    e.respondWith(agOnce(e.request));
  } else {
    e.respondWith(agOnce(e.request));
  }
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const hedef = e.notification.data && e.notification.data.url || "/";
  e.waitUntil(self.clients.matchAll({ type: "window" }).then((ws) => {
    for (const w of ws) { w.focus(); return w.navigate(hedef); }
    return self.clients.openWindow(hedef);
  }));
});
