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
  var pollVis = null;

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
        '<p class="cs3-muted">Tugmani bosing — Telegram ochiladi, u yerda <b>Start</b> bosasiz va shu yerga qaytasiz. Tamom.</p>' +
        '<div id="cs3BotWrap" style="margin-top:14px"></div>' +
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
    stopPolling();
  }

  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    if (pollVis) { document.removeEventListener("visibilitychange", pollVis); pollVis = null; }
  }

  /** Kirish muvaffaqiyatli tugadi — tokenni saqlab, oynani yopamiz. */
  function finishLogin(r, onDone) {
    setToken(r.token);
    clearPending();
    stopPolling();
    closeModal();
    var cb = (typeof onDone === "function") ? onDone : window.__cs3AuthDone;
    if (typeof cb === "function") cb(r.user);
    else location.reload();
  }

  var PENDING_KEY = "cs3_login_pending";

  function savePending(t) {
    try { localStorage.setItem(PENDING_KEY, JSON.stringify({ t: t, at: Date.now() })); } catch (e) {}
  }
  function readPending() {
    try {
      var raw = localStorage.getItem(PENDING_KEY);
      if (!raw) return null;
      var o = JSON.parse(raw);
      if (!o || !o.t || (Date.now() - o.at) > 5 * 60 * 1000) { clearPending(); return null; }
      return o.t;
    } catch (e) { return null; }
  }
  function clearPending() {
    try { localStorage.removeItem(PENDING_KEY); } catch (e) {}
  }

  /** Bir martalik havolani oldindan olib qo'yadi (tugma bosilishi bilan ochilsin). */
  function prepareBotLogin() {
    return api("/api/auth/start", { method: "POST" });
  }

  /**
   * Tayyor havola bilan kirishni boshlaydi.
   * MUHIM: bu funksiya tugma bosilishi bilan bir zumda chaqirilishi kerak —
   * shundagina brauzer Telegramni ochishga ruxsat beradi.
   */
  function beginBotLogin(d, onDone, hintEl, holderEl) {
    var hint = hintEl || document.getElementById("cs3AuthHint");
    var holder = holderEl || document.getElementById("cs3BotWrap");
    if (!d || !d.login_token) { if (hint) hint.textContent = "Ulanib bo'lmadi — qaytadan urinib ko'ring."; return; }
    // Server bot nomini bermasa, config.js'dagi nom bilan havolani o'zimiz yig'amiz.
    var url = d.bot_url;
    if (!url) {
      var u = (CFG.telegramBotUsername || "").replace(/^@/, "");
      if (!u) { if (hint) hint.textContent = "Bot nomi sozlanmagan (config.js)."; return; }
      url = "https://t.me/" + u + "?start=" + encodeURIComponent(d.login_token);
    }

    savePending(d.login_token);
    startPolling(d.login_token, onDone, hint);

    if (holder) {
      holder.innerHTML =
        '<a class="btn btn-primary" style="display:block;text-align:center;width:100%" ' +
        'href="' + url + '" target="_blank" rel="noopener">Telegramni ochish</a>';
    }
    if (hint) hint.textContent = "Telegramda «Start» tugmasini bosing, so'ng shu yerga qayting.";

    openTelegram(url);
    return url;
  }

  /** Telegramni ochadi: avval yangi oyna, bo'lmasa shu oynada. */
  function openTelegram(url) {
    var opened = null;
    try { opened = window.open(url, "_blank"); } catch (e) {}
    if (!opened) { try { location.href = url; } catch (e2) {} }
  }

  /* ----------------------------------------------------------
     BOT ORQALI KIRISH (ishonchli yo'l — o'rnatilgan ilova ichida ham ishlaydi)
     1) server bir martalik havola beradi
     2) Telegram ochiladi, foydalanuvchi "Start" bosadi
     3) sayt serverdan so'rab turadi va tokenni oladi
     ---------------------------------------------------------- */
  function botLogin(onDone, hintEl, holderEl) {
    var hint = hintEl || document.getElementById("cs3AuthHint");
    function say(t) { if (hint) hint.textContent = t; }
    stopPolling();
    say("Telegram tayyorlanmoqda…");
    return prepareBotLogin()
      .then(function (d) { beginBotLogin(d, onDone, hintEl, holderEl); })
      .catch(function (e) { say((e && e.message) || "Ulanib bo'lmadi."); });
  }

  /** Telegramdan qaytilganda: boshlangan kirish bo'lsa, jimgina davom ettiramiz. */
  function resumePendingLogin() {
    if (getToken()) { clearPending(); return; }
    var t = readPending();
    if (t) startPolling(t, null, null);
  }

  function startPolling(loginToken, onDone, hint) {
    var deadline = Date.now() + 5 * 60 * 1000; // 5 daqiqa
    var busy = false;

    function tick() {
      if (busy) return;
      if (Date.now() > deadline) {
        stopPolling();
        clearPending();
        if (hint) hint.textContent = "Vaqt tugadi — qaytadan urinib ko'ring.";
        return;
      }
      busy = true;
      api("/api/auth/poll/" + encodeURIComponent(loginToken))
        .then(function (r) {
          busy = false;
          if (r && r.ready && r.token) finishLogin(r, onDone);
        })
        .catch(function () { busy = false; });
    }

    pollTimer = setInterval(tick, 2000);
    // Telegramdan qaytganda darhol tekshiramiz (kutib o'tirmaydi).
    pollVis = function () { if (!document.hidden) tick(); };
    document.addEventListener("visibilitychange", pollVis);
    tick();
  }

  /** Ulanishni boshlaydi — bitta yo'l: bot orqali kirish. */
  function connect(onDone) {
    var modal = ensureModal();
    modal.classList.remove("hidden");
    window.__cs3AuthDone = (typeof onDone === "function") ? onDone : null;

    var wrap = document.getElementById("cs3BotWrap");
    var hint = document.getElementById("cs3AuthHint");
    if (hint) hint.textContent = "Tayyorlanmoqda…";
    if (wrap) {
      wrap.innerHTML =
        '<button type="button" class="btn btn-primary" id="cs3BotOpen" style="width:100%" disabled>Telegramni ochish</button>';
    }

    prepareBotLogin().then(function (d) {
      var btn = document.getElementById("cs3BotOpen");
      if (hint) hint.textContent = "";
      if (!btn) return;
      btn.disabled = false;
      var url = null;
      btn.onclick = function () {
        if (url) { openTelegram(url); return; }
        url = beginBotLogin(d, onDone, hint, null);
      };
    }).catch(function (e) {
      if (hint) hint.textContent = (e && e.message) || "Ulanib bo'lmadi.";
    });
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
      finishLogin(r);
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
    botLogin: botLogin,
    openTelegram: openTelegram,
    prepareBotLogin: prepareBotLogin,
    beginBotLogin: beginBotLogin,
    resumePendingLogin: resumePendingLogin,
    logout: logout,
    me: me,
    getToken: getToken,
    clearToken: clearToken,
    apiBase: API,
    isLoggedIn: function () { return !!getToken(); },
  };
})(window);

/* Telegramdan qaytganda boshlangan kirishni davom ettiramiz. */
document.addEventListener("DOMContentLoaded", function () {
  try { CS3.resumePendingLogin(); } catch (e) {}
});

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
