// Cryptospot 3% — PWA: service worker'ni ro'yxatdan o'tkazish va
// "Ilovani o'rnatish" tugmasini ko'rsatish.
(function () {
  "use strict";

  // 1) Service worker
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/service-worker.js").catch(function () {});
    });
  }

  // 2) "Ilovani o'rnatish" tugmasi (brauzer ruxsat berganda ko'rinadi)
  var deferred = null;
  var btn = null;

  function makeBtn() {
    if (btn) return btn;
    btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "⬇️ Ilovani o'rnatish";
    btn.setAttribute("aria-label", "Ilovani o'rnatish");
    btn.style.cssText =
      "position:fixed;left:50%;transform:translateX(-50%);bottom:18px;z-index:9000;" +
      "background:#e8b84b;color:#111;border:none;border-radius:24px;padding:12px 22px;" +
      "font:600 14px/1 Inter,Arial,sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.35);cursor:pointer";
    btn.addEventListener("click", function () {
      if (!deferred) return;
      deferred.prompt();
      deferred.userChoice.then(function () { deferred = null; hide(); });
    });
    document.body.appendChild(btn);
    return btn;
  }
  function show() { makeBtn().style.display = "block"; }
  function hide() { if (btn) btn.style.display = "none"; }

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferred = e;
    show();
  });
  window.addEventListener("appinstalled", function () { deferred = null; hide(); });
})();
