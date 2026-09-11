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
        '<h3>Telegram orqali kirish</h3>' +
        '<p class="cs3-muted">Pastdagi <b>Telegram</b> tugmasini bosib hisobingizni tasdiqlang — tamom. Botga o\'tib qaytish shart emas.</p>' +
        '<div id="cs3TgWidget" style="display:flex;justify-content:center;margin:16px 0 6px;min-height:48px"></div>' +
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

  /** Ulanishni boshlaydi — Telegram Login Widget orqali (bir tugma). */
  function connect(onDone) {
    var modal = ensureModal();
    modal.classList.remove("hidden");
    window.__cs3AuthDone = (typeof onDone === "function") ? onDone : null;

    var holder = document.getElementById("cs3TgWidget");
    var hint = document.getElementById("cs3AuthHint");
    var uname = (CFG.telegramBotUsername || "").replace(/^@/, "");
    if (hint) hint.textContent = "";
    if (!uname) { if (hint) hint.textContent = "Bot nomi sozlanmagan (config.js)."; return; }

    // Telegram tugmasini har ochilganda qayta joylaymiz.
    holder.innerHTML = "";
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://telegram.org/js/telegram-widget.js?22";
    s.setAttribute("data-telegram-login", uname);
    s.setAttribute("data-size", "large");
    s.setAttribute("data-userpic", "false");
    s.setAttribute("data-request-access", "write");
    s.setAttribute("data-onauth", "cs3OnTelegramAuth(user)");
    s.onerror = function () { if (hint) hint.textContent = "Telegram tugmasini yuklab bo'lmadi."; };
    holder.appendChild(s);
  }

  // Telegram Login Widget muvaffaqiyatli bo'lganda chaqiriladi (global).
  global.cs3OnTelegramAuth = function (user) {
    var hint = document.getElementById("cs3AuthHint");
    if (hint) hint.textContent = "Kirilyapti…";
    api("/api/auth/telegram", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(user),
    }).then(function (r) {
      setToken(r.token);
      closeModal();
      if (typeof window.__cs3AuthDone === "function") window.__cs3AuthDone(r.user);
      else location.reload();
    }).catch(function (e) {
      if (hint) hint.textContent = e.message || "Kirishda xatolik.";
    });
  };

  function logout() {
    clearToken();
    location.reload();
  }

  function me() {
    return api("/api/me").then(function (data) {
      // Server har safar yangi token beradi — sessiya uzaytiriladi.
      if (data && data.token) setToken(data.token);
      return data;
    });
  }

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
    }).catch(function (err) {
      // FAQAT haqiqiy 401'da chiqaramiz. Tarmoq/vaqtinchalik xatoda sessiya saqlanadi.
      if (err && err.status === 401) { CS3.clearToken(); asGuest(); return; }
      setBtn("Hisobim");
      if (btn) { btn.title = "Hisob menyusi"; btn.onclick = function () { if (acct) acct.classList.toggle("open"); }; }
      if (acct) {
        acct.innerHTML =
          '<p style="font-size:13px;margin:0 0 12px;color:var(--muted)">Aloqa vaqtincha uzildi — siz tizimdasiz.</p>' +
          '<button type="button" class="acct-link" id="acctLogout">Chiqish</button>';
        var lo = document.getElementById("acctLogout");
        if (lo) lo.onclick = function () { if (confirm("Hisobdan chiqasizmi?")) CS3.logout(); };
      }
    });
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
    }).catch(function (err) {
      // FAQAT 401'da chiqaramiz; tarmoq xatosida sessiya saqlanadi.
      if (err && err.status === 401) { CS3.clearToken(); asGuest(); }
    });
  }

  if (CS3.isLoggedIn()) asUser(); else asGuest();
});
