/* ==========================================================
   Admin panel
   ----------------------------------------------------------
   Kirish faqat Telegram orqali. Bu yerdagi kod hech narsani
   "ruxsat berish" bilan shug'ullanmaydi — har bir so'rovni server
   tekshiradi. Panel ko'rinib turgani hech kimga huquq bermaydi.
   ========================================================== */
(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };

  // ---------- tema ----------
  try {
    var saved = localStorage.getItem("cs3_theme");
    if (saved) document.documentElement.setAttribute("data-theme", saved);
  } catch (e) {}
  $("themeToggle").addEventListener("click", function () {
    var next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("cs3_theme", next); } catch (e) {}
  });

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }
  function status(id, text, kind) {
    var el = $(id);
    if (!el) return;
    el.textContent = text;
    el.className = "form-status" + (kind ? " " + kind : "");
  }
  function num(id) {
    var v = ($(id).value || "").trim().replace(/\s/g, "").replace(",", ".");
    return v === "" ? null : Number(v);
  }

  // ---------- kirish ----------
  $("connectBtn").addEventListener("click", function () {
    CS3.connect(function () { boot(); });
  });
  $("logoutBtn").addEventListener("click", function () { CS3.logout(); });

  function showLogin(msg) {
    $("loginCard").style.display = "";
    $("adminApp").style.display = "none";
    $("logoutBtn").style.display = "none";
    if (msg) status("loginStatus", msg, "err");
  }
  function showApp() {
    $("loginCard").style.display = "none";
    $("adminApp").style.display = "block";
    $("logoutBtn").style.display = "";
  }

  // ---------- tablar ----------
  $("tabs").addEventListener("click", function (e) {
    var btn = e.target.closest(".tab");
    if (!btn) return;
    document.querySelectorAll(".tab").forEach(function (t) { t.classList.remove("active"); });
    document.querySelectorAll(".panel").forEach(function (p) { p.classList.remove("active"); });
    btn.classList.add("active");
    $(btn.getAttribute("data-panel")).classList.add("active");
  });

  // ---------- signallar ----------
  var SIGNAL_FORMS = {
    signals:  { coin: "sgCoin", entry: "sgEntry", stop: "sgStop", tp1: "sgTp1", tp2: "sgTp2", note: "sgNote", status: "sgStatus", list: "sgList" },
    scalping: { coin: "scCoin", entry: "scEntry", stop: "scStop", tp1: "scTp1", tp2: "scTp2", note: "scNote", status: "scStatus", list: "scList" },
  };

  document.querySelectorAll("[data-add-signal]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var section = btn.getAttribute("data-add-signal");
      var f = SIGNAL_FORMS[section];
      var payload = {
        section: section,
        coin: ($(f.coin).value || "").trim(),
        entry: num(f.entry), stop: num(f.stop),
        tp1: num(f.tp1), tp2: num(f.tp2),
        comment: ($(f.note).value || "").trim(),
      };
      if (!payload.coin) { status(f.status, "Coin nomini kiriting.", "err"); return; }
      if ([payload.entry, payload.stop, payload.tp1, payload.tp2].some(function (v) {
        return v === null || isNaN(v);
      })) { status(f.status, "Barcha narxlarni raqam bilan to'ldiring.", "err"); return; }

      btn.disabled = true;
      status(f.status, "Yuborilmoqda…");
      CS3.api("/api/admin/signals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).then(function () {
        status(f.status, "✅ Qo'shildi. Narx kuzatuvi boshlandi.", "ok");
        [f.coin, f.entry, f.stop, f.tp1, f.tp2, f.note].forEach(function (i) { $(i).value = ""; });
        loadSignals(section);
        loadStats();
      }).catch(function (e) {
        status(f.status, e.message, "err");
      }).then(function () { btn.disabled = false; });
    });
  });

  var STATUS_LABEL = {
    pending: "Kutilmoqda", active: "Faol", tp1_hit: "TP1 olindi",
    tp2_hit: "TP2 — yopiq", stopped: "Stop — yopiq", closed: "Yopiq",
  };
  var OPEN = ["pending", "active", "tp1_hit"];

  function loadSignals(section) {
    var f = SIGNAL_FORMS[section];
    CS3.api("/api/admin/signals?section=" + encodeURIComponent(section)).then(function (rows) {
      var box = $(f.list);
      if (!rows.length) { box.innerHTML = '<p class="muted">Hozircha yo\'q.</p>'; return; }
      box.innerHTML = rows.map(function (s) {
        var open = OPEN.indexOf(s.status) !== -1;
        return '<div class="row-item">' +
          '<div><b>' + esc(s.coin) + '</b>' +
          ' <span class="status-pill' + (open ? " open" : "") + '">' +
          esc(STATUS_LABEL[s.status] || s.status) + '</span>' +
          '<div class="meta">Entry ' + esc(s.entry) + ' · Stop ' + esc(s.stop) +
          ' · TP ' + esc(s.tp1) + '/' + esc(s.tp2) + '</div></div>' +
          (open ? '<button class="btn-del" data-close="' + s.id + '" data-sec="' + section + '">Yopish</button>' : '') +
          '</div>';
      }).join("");
    }).catch(function (e) {
      $(f.list).innerHTML = '<p class="muted">' + esc(e.message) + '</p>';
    });
  }

  // ---------- kontent ----------
  var CONTENT_FORMS = {
    videos:     { title: "vdTitle", body: "vdBody", url: "vdUrl", status: "vdStatus", list: "vdList" },
    reminders:  { title: "rmTitle", body: "rmBody", status: "rmStatus", list: "rmList" },
    strategies: { title: "stTitle", body: "stBody", status: "stStatus", list: "stList" },
  };

  document.querySelectorAll("[data-add-content]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var section = btn.getAttribute("data-add-content");
      var f = CONTENT_FORMS[section];
      var title = ($(f.title).value || "").trim();
      if (!title) { status(f.status, "Sarlavhani kiriting.", "err"); return; }

      // Video: tayyor fayl tanlangan bo'lsa — multipart orqali yuklaymiz
      if (section === "videos") {
        var fileInput = document.getElementById("vdFile");
        if (fileInput && fileInput.files && fileInput.files.length) {
          var fd = new FormData();
          fd.append("title", title);
          fd.append("body", ($(f.body).value || "").trim());
          fd.append("file", fileInput.files[0]);
          btn.disabled = true;
          status(f.status, "Video yuklanmoqda… biroz kuting.");
          fetch(CS3.apiBase + "/api/admin/videos/upload", {
            method: "POST",
            headers: { "Authorization": "Bearer " + CS3.getToken() },
            body: fd,
          }).then(function (res) {
            return res.json().catch(function () { return {}; }).then(function (b) {
              if (!res.ok) throw new Error(b.detail || ("Xatolik (" + res.status + ")"));
              return b;
            });
          }).then(function () {
            status(f.status, "✅ Video yuklandi.", "ok");
            $(f.title).value = ""; $(f.body).value = "";
            fileInput.value = ""; if (f.url) $(f.url).value = "";
            loadContent(section); loadStats();
          }).catch(function (e) {
            status(f.status, e.message, "err");
          }).then(function () { btn.disabled = false; });
          return;   // JSON yo'liga o'tmaymiz
        }
      }

      var payload = { section: section, title: title, body: ($(f.body).value || "").trim() };
      if (f.url) {
        var url = ($(f.url).value || "").trim();
        if (url) payload.file_id = url;   // video havolasi file_id maydonida saqlanadi
      }

      btn.disabled = true;
      status(f.status, "Yuborilmoqda…");
      CS3.api("/api/admin/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).then(function () {
        status(f.status, "✅ Qo'shildi.", "ok");
        $(f.title).value = ""; $(f.body).value = "";
        if (f.url) $(f.url).value = "";
        loadContent(section);
        loadStats();
      }).catch(function (e) {
        status(f.status, e.message, "err");
      }).then(function () { btn.disabled = false; });
    });
  });

  function loadContent(section) {
    var f = CONTENT_FORMS[section];
    CS3.api("/api/admin/content/" + encodeURIComponent(section)).then(function (rows) {
      var box = $(f.list);
      if (!rows.length) { box.innerHTML = '<p class="muted">Hozircha yo\'q.</p>'; return; }
      box.innerHTML = rows.map(function (c) {
        return '<div class="row-item">' +
          '<div><b>' + esc(c.title) + '</b>' +
          (c.caption ? '<div class="meta">' + esc(c.caption.slice(0, 90)) + '</div>' : '') +
          '</div>' +
          '<button class="btn-del" data-delc="' + c.id + '" data-sec="' + section + '">O\'chirish</button>' +
          '</div>';
      }).join("");
    }).catch(function (e) {
      $(f.list).innerHTML = '<p class="muted">' + esc(e.message) + '</p>';
    });
  }

  // o'chirish/yopish tugmalari — ro'yxatlar qayta chizilgani uchun delegatsiya
  document.addEventListener("click", function (e) {
    var close = e.target.closest("[data-close]");
    if (close) {
      if (!confirm("Signal yopilsinmi?")) return;
      CS3.api("/api/admin/signals/" + close.getAttribute("data-close"), { method: "DELETE" })
        .then(function () { loadSignals(close.getAttribute("data-sec")); loadStats(); })
        .catch(function (err) { alert(err.message); });
      return;
    }
    var del = e.target.closest("[data-delc]");
    if (del) {
      if (!confirm("O'chirilsinmi?")) return;
      CS3.api("/api/admin/content/" + del.getAttribute("data-delc"), { method: "DELETE" })
        .then(function () { loadContent(del.getAttribute("data-sec")); loadStats(); })
        .catch(function (err) { alert(err.message); });
    }
  });

  // ---------- o'rinlar va hamyon ----------
  $("seatSave").addEventListener("click", function () {
    var taken = num("seatTaken"), total = num("seatTotal");
    if (taken === null || total === null) { status("seatStatus", "Ikkala maydonni to'ldiring.", "err"); return; }
    CS3.api("/api/admin/seats", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ taken: taken, total: total }),
    }).then(function (r) {
      status("seatStatus", "✅ Saqlandi. Bo'sh o'rin: " + r.remaining, "ok");
      loadStats();
    }).catch(function (e) { status("seatStatus", e.message, "err"); });
  });

  $("wSave").addEventListener("click", function () {
    var addr = ($("wAddr").value || "").trim();
    if (!addr) { status("wStatus", "Manzilni kiriting.", "err"); return; }
    CS3.api("/api/admin/wallet", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address: addr, network: ($("wNet").value || "TRC20").trim() }),
    }).then(function () { status("wStatus", "✅ Saqlandi.", "ok"); })
      .catch(function (e) { status("wStatus", e.message, "err"); });
  });

  // ---------- statistika ----------
  function loadStats() {
    Promise.all([
      CS3.api("/api/admin/users"),
      CS3.api("/api/sections"),
      CS3.api("/api/admin/seats"),
    ]).then(function (r) {
      var users = r[0], secs = r[1], seats = r[2];
      var totalItems = secs.reduce(function (a, s) { return a + s.count; }, 0);
      $("statGrid").innerHTML =
        '<div class="stat"><b>' + users.total + '</b><span>Ro\'yxatdan o\'tganlar</span></div>' +
        '<div class="stat"><b>' + totalItems + '</b><span>Jami material</span></div>' +
        '<div class="stat"><b>' + seats.remaining + '</b><span>Bo\'sh o\'rin</span></div>' +
        '<div class="stat"><b>' + secs.length + '</b><span>Bo\'limlar</span></div>';
    }).catch(function () { /* statistika ikkilamchi */ });
  }

  // ---------- boshlash ----------
  function boot() {
    if (!CS3.isLoggedIn()) { showLogin(); return; }
    CS3.api("/api/admin/me").then(function () {
      showApp();
      loadStats();
      loadSignals("signals");
      loadSignals("scalping");
      Object.keys(CONTENT_FORMS).forEach(loadContent);
      CS3.api("/api/admin/seats").then(function (s) {
        $("seatTaken").value = s.taken; $("seatTotal").value = s.total;
      });
      CS3.api("/api/admin/wallet").then(function (w) {
        $("wAddr").value = w.address; $("wNet").value = w.network;
      });
    }).catch(function (e) {
      CS3.clearToken();
      showLogin(e.status === 403
        ? "Bu hisobda admin huquqi yo'q."
        : "Kirish muddati tugagan, qaytadan ulaning.");
    });
  }

  if (!CS3.apiBase) {
    showLogin("API manzili sozlanmagan (assets/js/config.js).");
  } else {
    boot();
  }
})();
