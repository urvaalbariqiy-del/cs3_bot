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
   Navbar "Kirish" tugmasi + chap tomondagi hamburger (hisob paneli).
   - kirmagan: "Kirish" -> Telegram orqali ulanish; panelda kirish tugmasi
   - kirgan:  tugma ism, panel esa profil (ism + Telegram ID) + havolalar
   ---------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", function () {
  var btn = document.getElementById("cs3Connect");
  var btnLabel = document.getElementById("cs3ConnectLabel");
  var acct = document.getElementById("accountMenu");
  if (!btn && !acct) return;

  var TG_ICON =
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">' +
    '<path d="M9.04 15.47l-.38 5.34c.54 0 .78-.23 1.06-.51l2.55-2.44 5.29 3.87c.97.54 1.66.26 1.92-.9l3.48-16.3' +
    'c.31-1.45-.52-2.02-1.47-1.67L1.16 9.5c-1.41.55-1.39 1.34-.24 1.69l5.28 1.64L18.4 5.28c.58-.38 1.11-.17.67.21z"/></svg>';

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function setBtn(text) {
    if (btnLabel) btnLabel.textContent = text;
    else if (btn) btn.textContent = text;
  }

  function renderGuest() {
    if (!acct) return;
    acct.innerHTML =
      '<p style="font-size:13px;margin:0 0 12px;color:var(--muted)">' +
        'Video darslar, signallar va bo\'limlarni ko\'rish uchun Telegram orqali kiring — botda faqat <b>Start</b> bosasiz.' +
      '</p>' +
      '<button type="button" class="btn btn-primary" id="acctLogin" ' +
        'style="display:inline-flex;align-items:center;justify-content:center;gap:8px">' +
        TG_ICON + '<span>Telegram orqali kirish</span></button>';
    var a = document.getElementById("acctLogin");
    if (a) a.onclick = function () { acct.classList.remove("open"); CS3.connect(function () { location.reload(); }); };
  }

  function renderUser(me) {
    if (!acct) return;
    var full = (me.user && me.user.full_name) || "Foydalanuvchi";
    var initial = (full.trim().charAt(0) || "U").toUpperCase();
    var tgid = (me.user && me.user.telegram_id) || "";
    var isAdmin = !!(me.user && me.user.is_admin);
    acct.innerHTML =
      '<div class="account-profile">' +
        '<div class="account-avatar">' + esc(initial) + '</div>' +
        '<div>' +
          '<div class="account-name">' + (isAdmin ? "⚙ " : "") + esc(full) + '</div>' +
          '<div class="account-id">ID: ' + esc(String(tgid)) + '</div>' +
        '</div>' +
      '</div>' +
      (isAdmin
        ? '<a class="acct-link" href="admin.html">⚙ Admin panel</a>'
        : '<a class="acct-link" href="kabinet.html">Kabinetim</a>') +
      '<a class="acct-link" href="index.html">Bosh sahifa</a>' +
      '<button type="button" class="acct-link" id="acctLogout">Chiqish</button>';
    var lo = document.getElementById("acctLogout");
    if (lo) lo.onclick = function () { if (confirm("Hisobdan chiqasizmi?")) CS3.logout(); };
  }

  function asGuest() {
    setBtn("Kirish");
    if (btn) { btn.title = "Telegram orqali kirish"; btn.onclick = function () { CS3.connect(function () { location.reload(); }); }; }
    renderGuest();
  }

  function asUser() {
    CS3.me().then(function (me) {
      var name = ((me.user && me.user.full_name) || "Hisobim").split(" ")[0];
      setBtn((me.user && me.user.is_admin ? "⚙ " : "") + name);
      if (btn) { btn.title = "Hisob menyusi"; btn.onclick = function () { if (acct) acct.classList.toggle("open"); }; }
      renderUser(me);
    }).catch(function () { CS3.clearToken(); asGuest(); });
  }

  function refresh() { if (CS3.isLoggedIn()) asUser(); else asGuest(); }

  refresh();
});

/* ----------------------------------------------------------
   Bosh sahifadagi katta "Telegram orqali kirish" tugmasi.
   - kirmagan bo'lsa: Telegram orqali ulanadi
   - oddiy foydalanuvchi: kabinetga o'tadi
   - admin: to'g'ridan-to'g'ri admin panelga o'tadi
   ---------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", function () {
  var sbtn = document.getElementById("cs3Start");
  if (!sbtn) return;
  var lbl = document.getElementById("cs3StartLabel");

  function setLabel(t) { if (lbl) lbl.textContent = t; else sbtn.textContent = t; }

  function asGuest() {
    setLabel("Telegram orqali kirish");
    sbtn.onclick = function () { CS3.connect(function () { location.reload(); }); };
  }

  function asUser() {
    CS3.me().then(function (me) {
      if (me.user && me.user.is_admin) {
        setLabel("⚙ Admin panelga o'tish");
        sbtn.onclick = function () { location.href = "admin.html"; };
      } else {
        var name = ((me.user && me.user.full_name) || "Kabinet").split(" ")[0];
        setLabel(name + " — Kabinetga o'tish");
        sbtn.onclick = function () { location.href = "kabinet.html"; };
      }
    }).catch(function () { CS3.clearToken(); asGuest(); });
  }

  if (CS3.isLoggedIn()) asUser(); else asGuest();
});
