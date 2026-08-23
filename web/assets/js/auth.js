/* ==========================================================
   CS3 — saytga Telegram orqali ulanish
   ----------------------------------------------------------
   Parol yo'q, ro'yxatdan o'tish yo'q. Oqim:

     1. "Telegram orqali ulanish" bosiladi
     2. sayt bir martalik havola oladi va botni ochadi
     3. foydalanuvchi /start bosadi
     4. sayt uni tanidi

   Havola bir marta ishlaydi va 5 daqiqada kuchini yo'qotadi.
   Kirish huquqini brauzer emas, server hal qiladi — bu yerdagi kod
   faqat ko'rsatish bilan shug'ullanadi.
   ========================================================== */
(function (global) {
  "use strict";

  var CFG = global.SITE_CONFIG || {};
  var API = (CFG.apiBaseUrl || "").replace(/\/+$/, "");
  var TOKEN_KEY = "cs3_token";

  var pollTimer = null;

  function getToken() {
    try { return localStorage.getItem(TOKEN_KEY); } catch (e) { return null; }
  }
  function setToken(t) {
    try { localStorage.setItem(TOKEN_KEY, t); } catch (e) {}
  }
  function clearToken() {
    try { localStorage.removeItem(TOKEN_KEY); } catch (e) {}
  }

  function api(path, options) {
    options = options || {};
    var headers = options.headers || {};
    var token = getToken();
    if (token) headers["Authorization"] = "Bearer " + token;

    return fetch(API + path, Object.assign({}, options, { headers: headers }))
      .then(function (res) {
        if (res.status === 401) { clearToken(); }
        return res.json().catch(function () { return {}; }).then(function (body) {
          if (!res.ok) {
            var err = new Error(body.detail || ("Xatolik (" + res.status + ")"));
            err.status = res.status;
            throw err;
          }
          return body;
        });
      });
  }

  // ---------- ulanish oynasi ----------

  function ensureModal() {
    var el = document.getElementById("cs3AuthModal");
    if (el) return el;

    el = document.createElement("div");
    el.id = "cs3AuthModal";
    el.className = "cs3-modal hidden";
    el.innerHTML =
      '<div class="cs3-modal-card">' +
        '<button class="cs3-modal-x" type="button" aria-label="Yopish">&times;</button>' +
        '<h3>Telegram orqali ulanish</h3>' +
        '<p class="cs3-muted" id="cs3AuthText">' +
          'Pastdagi tugmani bosing — Telegram ochiladi. U yerda ' +
          '<b>Start</b> bosishingiz kifoya, boshqa hech narsa kerak emas.' +
        '</p>' +
        '<a class="cs3-btn" id="cs3AuthLink" target="_blank" rel="noopener">Telegramni ochish</a>' +
        '<p class="cs3-muted cs3-small" id="cs3AuthHint"></p>' +
      '</div>';
    document.body.appendChild(el);

    el.querySelector(".cs3-modal-x").addEventListener("click", closeModal);
    el.addEventListener("click", function (e) { if (e.target === el) closeModal(); });
    return el;
  }

  function closeModal() {
    var el = document.getElementById("cs3AuthModal");
    if (el) el.classList.add("hidden");
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  /** Ulanishni boshlaydi. onDone(user) muvaffaqiyatda chaqiriladi. */
  function connect(onDone) {
    var modal = ensureModal();
    modal.classList.remove("hidden");
    var hint = document.getElementById("cs3AuthHint");
    var link = document.getElementById("cs3AuthLink");
    hint.textContent = "Havola tayyorlanmoqda…";
    link.removeAttribute("href");

    api("/api/auth/start", { method: "POST" }).then(function (data) {
      link.href = data.bot_url;
      hint.textContent = "Telegramda Start bosgach, shu oyna o'zi yopiladi.";

      // Ba'zi brauzerlar yangi oynani bloklaydi — shuning uchun havolani
      // ko'rinadigan tugma qilib qo'yamiz va o'zimiz ham ochishga urinamiz.
      try { window.open(data.bot_url, "_blank", "noopener"); } catch (e) {}

      var waited = 0;
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = setInterval(function () {
        waited += 2;
        if (waited > (data.expires_in || 300)) {
          clearInterval(pollTimer); pollTimer = null;
          hint.textContent = "Havolaning muddati tugadi. Oynani yopib, qaytadan bosing.";
          return;
        }
        api("/api/auth/poll/" + encodeURIComponent(data.login_token))
          .then(function (r) {
            if (!r.ready) return;
            clearInterval(pollTimer); pollTimer = null;
            setToken(r.token);
            closeModal();
            if (typeof onDone === "function") onDone(r.user);
            else location.reload();
          })
          .catch(function () { /* tarmoq uzilishi — keyingi urinishda */ });
      }, 2000);
    }).catch(function (e) {
      hint.textContent = e.message;
    });
  }

  function logout() {
    clearToken();
    location.reload();
  }

  function me() { return api("/api/me"); }

  global.CS3 = {
    api: api,
    connect: connect,
    logout: logout,
    me: me,
    getToken: getToken,
    clearToken: clearToken,
    apiBase: API,
    isLoggedIn: function () { return !!getToken(); },
  };
})(window);

/* ----------------------------------------------------------
   Har bir sahifadagi "Ulanish" tugmasi.
   Ulangan bo'lsa — ismni ko'rsatadi va bosilganda chiqish taklif qiladi.
   ---------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", function () {
  var btn = document.getElementById("cs3Connect");
  if (!btn) return;

  function asGuest() {
    btn.textContent = "Ulanish";
    btn.onclick = function () { CS3.connect(function () { asUser(); }); };
  }

  function asUser() {
    CS3.me().then(function (me) {
      var name = (me.user.full_name || "Hisobim").split(" ")[0];
      btn.textContent = (me.user.is_admin ? "⚙ " : "") + name;
      btn.title = "Chiqish uchun bosing";
      btn.onclick = function () {
        if (confirm("Hisobdan chiqasizmi?")) CS3.logout();
      };
    }).catch(function () {
      CS3.clearToken();
      asGuest();
    });
  }

  if (CS3.isLoggedIn()) asUser(); else asGuest();
});
