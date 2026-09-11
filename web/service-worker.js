// Cryptospot 3% — service worker
// Ilova sifatida o'rnatilishi (installable) uchun kerak va sahifalarni
// keshlab, sekin internetda ham tez ochilishini ta'minlaydi.
//
// Strategiya: "avval tarmoq, bo'lmasa kesh" (network-first). Shunda kontent
// doim yangi bo'ladi, internet bo'lmaganda oxirgi kesh ko'rsatiladi.

const CACHE = "cs3-v8";
const CORE = [
  "/",
  "/index.html",
  "/app.html",
  "/manifest.json",
  "/assets/css/main.css",
  "/assets/js/config.js",
  "/assets/js/auth.js",
  "/assets/js/main.js",
  "/assets/js/app.js",
  "/assets/js/appdata.js",
  "/assets/js/pwa.js",
  "/assets/img/logo-main.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) =>
      // Har bir faylni alohida keshlaymiz — bittasi topilmasa ham install buzilmaydi.
      Promise.all(CORE.map((u) => cache.add(u).catch(() => {})))
    )
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  // Faqat o'z domenimiz. API (Railway), TradingView, tashqi CDN'larga tegmaymiz.
  if (url.origin !== self.location.origin) return;
  if (url.pathname.indexOf("/api/") !== -1) return;

  event.respondWith(
    fetch(req)
      .then((res) => {
        // Muvaffaqiyatli javobni keshga yozib qo'yamiz (oflayn uchun).
        if (res && res.status === 200 && res.type === "basic") {
          const copy = res.clone();
          caches.open(CACHE).then((cache) => cache.put(req, copy)).catch(() => {});
        }
        return res;
      })
      .catch(() =>
        caches.match(req).then((cached) => {
          if (cached) return cached;
          if (req.mode === "navigate") return caches.match("/index.html");
          return new Response("", { status: 504, statusText: "Offline" });
        })
      )
  );
});
