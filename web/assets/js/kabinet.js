/* ==========================================================
   Shaxsiy kabinet
   ----------------------------------------------------------
   Kirish Telegram orqali (parol yo'q). Olingan token localStorage'da
   saqlanadi va har bir so'rovda Authorization sarlavhasida yuboriladi.

   Muhim: bu yerda hech qanday kirish huquqi "hisoblanmaydi" — nima ochiq,
   nima yopiq ekanini faqat server aytadi. Brauzerdagi kod hech qachon
   yopiq mazmunni olmaydi, shuning uchun uni yashirishning ham hojati yo'q.
   ========================================================== */

(function () {
  "use strict";

  var CFG = window.SITE_CONFIG || {};
  var API = (CFG.apiBaseUrl || "").replace(/\/+$/, "");
  var TOKEN_KEY = "cs3_token";

  var $ = function (id) { return document.getElementById(id); };

  // ---------- tema ----------
  var savedTheme = localStorage.getItem("cs3_theme");
  if (savedTheme) document.documentElement.setAttribute("data-theme", savedTheme);
  $("themeBtn").addEventListener("click", function () {
    var next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("cs3_theme", next);
  });

  // ---------- token ----------
  function getToken() { return localStorage.getItem(TOKEN_KEY); }
  function setToken(t) { localStorage.setItem(TOKEN_KEY, t); }
  function clearToken() { localStorage.removeItem(TOKEN_KEY); }

  function api(path, options) {
    options = options || {};
    var headers = options.headers || {};
    var token = getToken();
    if (token) headers["Authorization"] = "Bearer " + token;
    return fetch(API + path, Object.assign({}, options, { headers: headers }))
      .then(function (res) {
        if (res.status === 401) { clearToken(); showLogin(); throw new Error("unauthorized"); }
        return res.json().then(function (body) {
          if (!res.ok) throw new Error(body.detail || "Xatolik yuz berdi");
          return body;
        });
      });
  }

  // ---------- ko'rinishlar ----------
  function showLogin() {
    $("loading").classList.add("hidden");
    $("appView").classList.add("hidden");
    $("logoutBtn").classList.add("hidden");
    $("loginView").classList.remove("hidden");
    mountTelegramButton();
  }

  function showApp() {
    $("loading").classList.add("hidden");
    $("loginView").classList.add("hidden");
    $("appView").classList.remove("hidden");
    $("logoutBtn").classList.remove("hidden");
  }

  function notice(text, kind) {
    var el = $("notice");
    el.textContent = text;
    el.className = "notice" + (kind ? " " + kind : "");
    el.classList.remove("hidden");
  }

  // ---------- Telegram orqali ulanish ----------
  // Umumiy modul (auth.js) ishlatiladi: bir martalik havola -> botda /start.

  function mountTelegramButton() {
    var box = $("tgLoginBox");
    if (box.dataset.mounted) return;
    box.dataset.mounted = "1";

    var btn = document.createElement("button");
    btn.className = "btn btn-primary";
    btn.type = "button";
    btn.textContent = "Telegram orqali ulanish";
    btn.addEventListener("click", function () {
      CS3.connect(function () { load(); });
    });
    box.appendChild(btn);

    $("loginHint").textContent =
      "Telegramda faqat Start bosasiz — boshqa hech narsa kerak emas.";
  }

  function tryWebAppLogin() {
    var tg = window.Telegram && window.Telegram.WebApp;
    if (!tg || !tg.initData) return Promise.resolve(false);
    return api("/api/auth/webapp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ init_data: tg.initData }),
    }).then(function (data) { setToken(data.token); return true; })
      .catch(function () { return false; });
  }

  $("logoutBtn").addEventListener("click", function () {
    clearToken();
    location.reload();
  });

  // ---------- obuna kartasi ----------
  function renderSubscription(me) {
    $("userName").textContent = me.user.full_name || "Xush kelibsiz";
    var box = $("subCard");

    if (!me.subscription) {
      box.innerHTML =
        '<div class="tariff-name">Obuna yo\'q</div>' +
        '<div class="row muted"><span>Bo\'limlarni ochish uchun tarif tanlang</span></div>';
      return;
    }

    var s = me.subscription;
    box.innerHTML =
      '<div class="tariff-name">' + esc(s.tariff_name) + '</div>' +
      '<div class="row"><span class="muted">Tugash sanasi</span><b>' +
        esc(fmtDate(s.ends_at)) + '</b></div>' +
      '<div class="row"><span class="muted">Qolgan muddat</span><b>' +
        s.days_left + ' kun</b></div>';
  }

  // ---------- bo'limlar ----------
  function renderSections(list) {
    var wrap = $("sections");
    wrap.innerHTML = "";

    list.forEach(function (sec) {
      var card = document.createElement("button");
      card.className = "sec-card" + (sec.locked ? " locked" : "");
      card.type = "button";

      var html =
        '<div class="sec-title">' + esc(sec.title) + '</div>' +
        '<div class="sec-meta">' + sec.count + ' ta material</div>';
      if (sec.locked) {
        html += '<span class="sec-lock">🔒 ' + esc(sec.min_tariff_name) + ' kerak</span>';
      }
      card.innerHTML = html;

      card.addEventListener("click", function () {
        if (sec.locked) {
          notice(sec.title + " bo'limi " + sec.min_tariff_name +
                 " obunasi uchun. Pastdagi tariflardan tanlang.", null);
          $("tariffsHeading").scrollIntoView({ behavior: "smooth" });
        } else {
          openSection(sec);
        }
      });
      wrap.appendChild(card);
    });
  }

  function openSection(sec) {
    $("itemsTitle").textContent = sec.title;
    $("items").innerHTML = '<p class="muted">Yuklanmoqda…</p>';
    $("itemsPanel").classList.remove("hidden");
    $("itemsPanel").scrollIntoView({ behavior: "smooth" });

    api("/api/sections/" + encodeURIComponent(sec.code)).then(function (data) {
      var box = $("items");
      box.innerHTML = "";
      if (!data.items.length) {
        box.innerHTML = '<p class="muted">Bu bo\'limda hozircha material yo\'q.</p>';
        return;
      }
      data.items.forEach(function (it) {
        var row = document.createElement("button");
        row.className = "item";
        row.type = "button";
        if (data.kind === "signal") {
          row.innerHTML =
            '<span class="item-name">💠 ' + esc(it.coin) + '</span>' +
            '<span class="status ' + (it.is_open ? "open" : "closed") + '">' +
              statusLabel(it.status) + '</span>';
          row.addEventListener("click", function () { toggleSignal(row, it.id); });
        } else {
          row.innerHTML =
            '<span class="item-name">' + esc(it.title) + '</span>' +
            (it.has_file ? '<span class="status">fayl</span>' : '');
          row.addEventListener("click", function () { toggleContent(row, it.id); });
        }
        box.appendChild(row);
      });
    }).catch(function (e) {
      $("items").innerHTML = '<p class="muted">' + esc(e.message) + '</p>';
    });
  }

  $("closeItems").addEventListener("click", function () {
    $("itemsPanel").classList.add("hidden");
  });

  function toggleSignal(row, id) {
    if (row.nextSibling && row.nextSibling.classList &&
        row.nextSibling.classList.contains("detail")) {
      row.nextSibling.remove();
      return;
    }
    api("/api/signals/" + id).then(function (s) {
      var d = document.createElement("div");
      d.className = "detail";
      d.innerHTML =
        cell("Kirish (Entry)", s.entry) +
        cell("Stop", s.stop) +
        cell("TP1", s.tp1) +
        cell("TP2", s.tp2) +
        (s.comment ? '<div class="detail-note">📝 ' + esc(s.comment) + '</div>' : "");
      row.after(d);
    }).catch(function (e) { notice(e.message, "err"); });
  }

  function toggleContent(row, id) {
    if (row.nextSibling && row.nextSibling.classList &&
        row.nextSibling.classList.contains("detail")) {
      row.nextSibling.remove();
      return;
    }
    api("/api/content/" + id).then(function (c) {
      var d = document.createElement("div");
      d.className = "detail";
      var body = c.caption ? '<div class="detail-note">' + esc(c.caption) + "</div>" : "";
      if (c.has_file) {
        body += '<div class="detail-note">📎 Fayl botda ochiladi: ' +
                '<a href="https://t.me/' + esc(CFG.telegramBotUsername) +
                '" target="_blank" rel="noopener">botga o\'tish</a></div>';
      }
      d.innerHTML = body || '<div class="detail-note muted">Qo\'shimcha ma\'lumot yo\'q.</div>';
      row.after(d);
    }).catch(function (e) { notice(e.message, "err"); });
  }

  function cell(k, v) {
    return '<div><span class="k">' + esc(k) + '</span><span class="v">' + fmtNum(v) + "</span></div>";
  }

  function statusLabel(st) {
    return ({
      pending: "Kutilmoqda",
      active: "Faol",
      tp1_hit: "TP1 olindi",
      tp2_hit: "TP2 — yopiq",
      stopped: "Stop — yopiq",
      closed: "Yopiq",
    })[st] || st;
  }

  // ---------- tariflar ----------
  var currentTariff = null;

  function renderTariffs(list) {
    var wrap = $("tariffs");
    wrap.innerHTML = "";
    list.forEach(function (t) {
      var card = document.createElement("div");
      card.className = "tariff" + (t.code === currentTariff ? " current" : "");

      var prices = t.periods.map(function (p) {
        return '<div class="price-row"><span>' + esc(p.name) + '</span>' +
               '<b>' + fmtNum(p.price) + " " + esc(p.currency) + "</b>" +
               '<button class="btn btn-primary btn-sm" data-t="' + esc(t.code) +
               '" data-p="' + esc(p.period) + '">Tanlash</button></div>';
      }).join("");

      card.innerHTML =
        "<h3>" + esc(t.name) + (t.code === currentTariff ? " ✓" : "") + "</h3>" +
        "<ul>" + t.sections.map(function (s) { return "<li>" + esc(s) + "</li>"; }).join("") + "</ul>" +
        '<div class="prices">' + prices + "</div>";

      wrap.appendChild(card);
    });

    wrap.querySelectorAll("button[data-t]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openPayment(btn.getAttribute("data-t"), btn.getAttribute("data-p"));
      });
    });
  }

  // ---------- to'lov ----------
  var payState = { tariff: null, period: null, methodId: null };

  function openPayment(tariff, period) {
    payState = { tariff: tariff, period: period, methodId: null };
    $("payModal").classList.remove("hidden");
    $("payTitle").textContent = "To'lov";
    $("payBody").innerHTML = '<p class="muted">Yuklanmoqda…</p>';

    api("/api/payment-methods").then(function (methods) {
      if (!methods.length) {
        $("payBody").innerHTML =
          '<p class="muted">To\'lov usullari hali kiritilmagan. Iltimos, admin bilan bog\'laning.</p>';
        return;
      }
      var html = '<p class="muted">To\'lov usulini tanlang, to\'lang va chek rasmini yuklang.</p>';
      methods.forEach(function (m) {
        html += '<button class="method" type="button" data-id="' + m.id + '">' +
                '<div class="m-title">' + esc(m.title) + "</div>" +
                '<div class="m-details">' + esc(m.details) + "</div></button>";
      });
      html +=
        '<div class="file-row"><label for="receiptInput">Chek (rasm):</label>' +
        '<input type="file" id="receiptInput" accept="image/*" /></div>' +
        '<button class="btn btn-primary btn-block" id="paySubmit">Chekni yuborish</button>' +
        '<p class="muted kab-note" id="payMsg"></p>';
      $("payBody").innerHTML = html;

      $("payBody").querySelectorAll(".method").forEach(function (el) {
        el.addEventListener("click", function () {
          $("payBody").querySelectorAll(".method").forEach(function (x) {
            x.classList.remove("active");
          });
          el.classList.add("active");
          payState.methodId = el.getAttribute("data-id");
        });
      });
      if (methods.length === 1) {
        $("payBody").querySelector(".method").click();
      }
      $("paySubmit").addEventListener("click", submitPayment);
    });
  }

  function submitPayment() {
    var input = $("receiptInput");
    var msg = $("payMsg");
    if (!input.files || !input.files[0]) {
      msg.textContent = "Avval chek rasmini tanlang.";
      return;
    }
    var fd = new FormData();
    fd.append("tariff", payState.tariff);
    fd.append("period", payState.period);
    if (payState.methodId) fd.append("method_id", payState.methodId);
    fd.append("receipt", input.files[0]);

    $("paySubmit").disabled = true;
    msg.textContent = "Yuborilmoqda…";

    api("/api/payments", { method: "POST", body: fd })
      .then(function (r) {
        closePayment();
        notice(r.message, "ok");
      })
      .catch(function (e) {
        msg.textContent = e.message;
        $("paySubmit").disabled = false;
      });
  }

  function closePayment() { $("payModal").classList.add("hidden"); }
  $("payClose").addEventListener("click", closePayment);
  $("payModal").addEventListener("click", function (e) {
    if (e.target === $("payModal")) closePayment();
  });

  // ---------- yordamchilar ----------
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }
  function fmtNum(n) {
    if (n == null || isNaN(n)) return String(n == null ? "" : n);
    return Number(n).toLocaleString("ru-RU", { maximumFractionDigits: 8 });
  }
  function fmtDate(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleDateString("ru-RU") + " " +
           d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  }

  // ---------- boshlash ----------
  function load() {
    return Promise.all([
      api("/api/me"),
      api("/api/sections"),
      api("/api/tariffs"),
    ]).then(function (res) {
      var me = res[0];
      currentTariff = me.subscription ? me.subscription.tariff : null;
      renderSubscription(me);
      renderSections(res[1]);
      renderTariffs(res[2]);
      showApp();
    }).catch(function (e) {
      if (e.message !== "unauthorized") {
        $("loading").textContent = "Server bilan bog'lanib bo'lmadi: " + e.message;
      }
    });
  }

  if (!API) {
    $("loading").textContent =
      "API manzili sozlanmagan. assets/js/config.js ichidagi apiBaseUrl'ni to'ldiring.";
  } else if (getToken()) {
    load();
  } else {
    tryWebAppLogin().then(function (loggedIn) {
      if (loggedIn) load(); else showLogin();
    });
  }
})();
