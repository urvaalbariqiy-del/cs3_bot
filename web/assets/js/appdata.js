// ==========================================================
// Cryptospot 3% ilova — tablar uchun ma'lumot (backend bilan)
// ==========================================================
(function () {
  "use strict";
  var CFG = window.SITE_CONFIG || {};
  var base = (CFG.apiBaseUrl || "").replace(/\/+$/, "");
  var ready = !!base && base.indexOf("YOUR-BACKEND-URL") === -1;

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }
  function money(x) { return "$" + Number(x).toLocaleString("en-US", { maximumFractionDigits: 2 }); }
  function full(url) { return url ? (url.charAt(0) === "/" ? base + url : url) : ""; }

  document.addEventListener("DOMContentLoaded", function () {
    if (ready) {
      loadPosts();
      loadVideos();
      loadStrategies();
      loadSignals();
      loadKabinet();
    }
    setupCalculator();
    loadMarket();            // CoinGecko — backendсиз ham ishlaydi
    setInterval(loadMarket, 60000);
  });

  // ---------------- BOZOR (CoinGecko kartalari) ----------------
  function fmtPrice(n) {
    n = Number(n);
    if (n >= 1) return n.toLocaleString("en-US", { maximumFractionDigits: 2 });
    return n.toLocaleString("en-US", { maximumFractionDigits: 6 });
  }
  function fmtCap(n) {
    n = Number(n);
    if (n >= 1e12) return (n / 1e12).toFixed(2) + " T";
    if (n >= 1e9) return (n / 1e9).toFixed(2) + " B";
    if (n >= 1e6) return (n / 1e6).toFixed(2) + " M";
    return n.toLocaleString("en-US");
  }
  var _marketLoaded = false;
  function loadMarket() {
    var grid = $("marketGrid");
    if (!grid) return;
    if (!_marketLoaded) grid.innerHTML = '<p class="muted" style="grid-column:1/-1;text-align:center">Yuklanmoqda…</p>';
    fetch("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=30&page=1&price_change_percentage=24h")
      .then(function (r) { return r.json(); })
      .then(function (rows) {
        if (!Array.isArray(rows) || !rows.length) { if (!_marketLoaded) grid.innerHTML = '<p class="muted" style="grid-column:1/-1;text-align:center">Ma\'lumot yuklanmadi.</p>'; return; }
        _marketLoaded = true;
        grid.innerHTML = rows.map(function (c) {
          var chg = c.price_change_percentage_24h || 0;
          var cls = chg >= 0 ? "mc-up" : "mc-down";
          return '<div class="market-card"><div class="mc-top"><img src="' + esc(c.image) + '" alt=""><div><div class="mc-name">' + esc(c.name) + '</div><div class="mc-sym">' + esc(c.symbol) + '</div></div></div>' +
            '<div class="mc-price">$' + fmtPrice(c.current_price) + '</div>' +
            '<div class="mc-chg ' + cls + '">' + (chg >= 0 ? "+" : "") + chg.toFixed(2) + '%</div>' +
            '<div class="mc-cap">MCap: $' + fmtCap(c.market_cap) + '</div></div>';
        }).join("");
      })
      .catch(function () { if (!_marketLoaded) grid.innerHTML = '<p class="muted" style="grid-column:1/-1;text-align:center">Bozor ma\'lumotini yuklab bo\'lmadi.</p>'; });
  }

  // ---------------- XABARLAR (kanal postlari) ----------------
  function loadPosts() {
    var wrap = $("postsWrap"), empty = $("postsEmpty");
    if (!wrap) return;
    fetch(base + "/api/posts").then(function (r) { return r.json(); }).then(function (d) {
      var posts = d.posts || [];
      if (!posts.length) return;
      if (empty) empty.style.display = "none";
      wrap.innerHTML = "";
      posts.forEach(function (p) {
        var media = "";
        var u = full(p.url);
        if (u && p.kind === "image") media = '<img src="' + esc(u) + '" style="width:100%;border-radius:12px;margin:4px 0 12px" loading="lazy">';
        else if (u && p.kind === "video") media = '<video controls preload="metadata" style="width:100%;border-radius:12px;margin:4px 0 12px;background:#000" src="' + esc(u) + '"></video>';
        else if (u && p.kind === "audio") media = '<audio controls style="width:100%;margin:4px 0 12px" src="' + esc(u) + '"></audio>';
        else if (u && p.kind === "link") media = '<a href="' + esc(u) + '" target="_blank" rel="noopener" class="btn btn-outline btn-block" style="margin:4px 0 12px">Havolani ochish</a>';
        var card = document.createElement("article");
        card.className = "card";
        card.style.cssText = "padding:18px;margin-bottom:16px";
        card.innerHTML =
          '<h3 style="margin:0 0 10px">' + esc(p.title) + '</h3>' + media +
          (p.body ? '<p style="white-space:pre-wrap;font-size:14px;line-height:1.7;color:var(--fg)">' + esc(p.body) + '</p>' : '') +
          '<div style="margin-top:12px"><button class="btn btn-outline" data-cmt="' + p.id + '" style="font-size:13px;padding:7px 13px">💬 Izohlar (' + p.comments + ')</button></div>' +
          '<div id="cmt' + p.id + '" style="display:none;margin-top:12px"></div>';
        wrap.appendChild(card);
      });
      wrap.querySelectorAll("[data-cmt]").forEach(function (b) {
        b.addEventListener("click", function () {
          var id = b.getAttribute("data-cmt"), area = $("cmt" + id);
          if (area.style.display === "none") { area.style.display = "block"; loadComments(id, area); }
          else area.style.display = "none";
        });
      });
    }).catch(function () {});
  }

  function loadComments(id, area) {
    area.innerHTML = '<p class="muted" style="font-size:13px">Yuklanmoqda…</p>';
    fetch(base + "/api/posts/" + id + "/comments").then(function (r) { return r.json(); }).then(function (d) {
      var list = (d.comments || []).map(function (c) {
        return '<div style="padding:9px 0;border-bottom:1px solid var(--border)"><b style="font-size:13px">' + esc(c.name) + '</b>' +
          '<p style="margin:3px 0 0;font-size:13px;white-space:pre-wrap;color:var(--fg)">' + esc(c.text) + '</p></div>';
      }).join("") || '<p class="muted" style="font-size:13px">Hali izoh yo\'q. Birinchi bo\'ling!</p>';
      var form;
      if (window.CS3 && CS3.isLoggedIn()) {
        form = '<div style="margin-top:10px"><textarea id="ci' + id + '" placeholder="Izohingiz…" style="width:100%;background:var(--bg-alt);border:1px solid var(--border);color:var(--fg);border-radius:10px;padding:10px;font:inherit;font-size:14px;min-height:64px"></textarea>' +
          '<button class="btn btn-primary" data-send="' + id + '" style="margin-top:8px;font-size:13px;padding:8px 15px">Yuborish</button>' +
          '<p id="cs' + id + '" style="font-size:12px;margin:6px 0 0;min-height:14px"></p></div>';
      } else {
        form = '<div style="margin-top:10px"><p class="muted" style="font-size:13px;margin-bottom:8px">Izoh yozish uchun Telegram orqali kiring.</p>' +
          '<button class="btn btn-primary" id="cl' + id + '" style="font-size:13px;padding:8px 15px">Telegram orqali kirish</button></div>';
      }
      area.innerHTML = list + form;
      var send = area.querySelector("[data-send]");
      if (send) send.addEventListener("click", function () { sendComment(id, area); });
      var login = $("cl" + id);
      if (login) login.addEventListener("click", function () { CS3.connect(function () { location.reload(); }); });
    }).catch(function () { area.innerHTML = '<p class="muted" style="font-size:13px">Izohlarni yuklab bo\'lmadi.</p>'; });
  }

  function sendComment(id, area) {
    var ta = $("ci" + id), st = $("cs" + id), text = (ta.value || "").trim();
    if (!text) { st.textContent = "Izoh bo'sh."; st.style.color = "#e6484f"; return; }
    st.textContent = "Yuborilmoqda…"; st.style.color = "var(--muted)";
    CS3.api("/api/posts/" + id + "/comments", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: text }),
    }).then(function () { loadComments(id, area); })
      .catch(function (e) { st.textContent = e.message; st.style.color = "#e6484f"; });
  }

  // ---------------- VIDEO DARSLAR (academy) ----------------
  function loadVideos() {
    var grid = $("videoGrid"), empty = $("videoEmpty");
    if (!grid) return;
    var botUrl = CFG.telegramBotUsername ? "https://t.me/" + CFG.telegramBotUsername : "";
    fetch(base + "/api/video-lessons").then(function (r) { return r.json(); }).then(function (d) {
      var lessons = d.lessons || [];
      if (!lessons.length) return;
      if (empty) empty.style.display = "none";
      grid.innerHTML = "";
      lessons.forEach(function (l) {
        var u = full(l.url), media = "";
        if (l.kind === "file" && u) media = '<video controls preload="metadata" style="width:100%;border-radius:10px;margin-top:8px;background:#000" src="' + esc(u) + '"></video>';
        else if (l.kind === "link" && u) media = '<a href="' + esc(u) + '" target="_blank" rel="noopener" class="btn btn-outline btn-block" style="margin-top:10px">Darsni ko’rish</a>';
        else if (l.kind === "tg" && botUrl) media = '<a href="' + esc(botUrl) + '" target="_blank" rel="noopener" class="btn btn-outline btn-block" style="margin-top:10px">Botda ko’rish</a>';
        var card = document.createElement("div");
        card.className = "card feature-card";
        card.innerHTML = '<p class="pill" style="margin-bottom:10px">Video dars</p><h3 style="margin:0 0 8px">' + esc(l.title) + '</h3>' +
          (l.description ? '<p class="muted" style="font-size:13px">' + esc(l.description) + '</p>' : '') + media;
        grid.appendChild(card);
      });
    }).catch(function () {});
  }

  // ---------------- STRATEGIYALAR (academy) ----------------
  function loadStrategies() {
    var grid = $("strategyGrid"), empty = $("strategyEmpty");
    if (!grid) return;
    fetch(base + "/api/strategies").then(function (r) { return r.json(); }).then(function (d) {
      var rows = d.strategies || [];
      if (!rows.length) return;
      if (empty) empty.style.display = "none";
      grid.innerHTML = rows.map(function (s) {
        return '<div class="card" style="padding:18px;margin-bottom:14px"><h3 style="margin:0 0 8px">' + esc(s.title) + '</h3>' +
          (s.text ? '<p style="white-space:pre-wrap;font-size:14px;line-height:1.7;color:var(--fg)">' + esc(s.text) + '</p>' : '') + '</div>';
      }).join("");
    }).catch(function () {});
  }

  // ---------------- SIGNALLAR ----------------
  function loadSignals() {
    var list = $("signalsList");
    if (!list) return;
    function render() {
      fetch(base + "/api/signals").then(function (r) { return r.json(); }).then(function (data) {
        var sigs = data.signals || [];
        if (!sigs.length) { list.innerHTML = '<p class="muted">Hozircha faol signal yo\'q. Tez orada joylanadi.</p>'; return; }
        list.innerHTML = "";
        sigs.forEach(function (s) {
          var dir = s.direction === "LONG" ? "#3ddc97" : "#e6484f";
          var st = s.active ? "#3ddc97" : "var(--muted)";
          var img = s.image ? full(s.image) : "";
          var card = document.createElement("div");
          card.className = "card feature-card" + (s.active ? "" : " cs3-locked");
          card.innerHTML =
            '<p class="pill" style="margin-bottom:10px;color:' + dir + ';border-color:' + dir + '">' + esc(s.symbol) + ' · ' + esc(s.direction) + '</p>' +
            (img ? '<img src="' + esc(img) + '" style="width:100%;border-radius:10px;margin-bottom:10px" loading="lazy">' : '') +
            '<p style="margin:0 0 10px;font-size:12.5px;color:' + st + '"><b>' + esc(s.status_label || "") + '</b></p>' +
            '<p style="margin:0 0 6px;font-size:13.5px"><b>Entry:</b> ' + esc(s.entry) + '</p>' +
            '<p style="margin:0 0 6px;font-size:13.5px"><b>TP:</b> ' + esc(s.tp) + '</p>' +
            '<p style="margin:0 0 6px;font-size:13.5px"><b>SL:</b> ' + esc(s.sl) + '</p>' +
            (s.note ? '<p class="muted" style="font-size:12.5px;margin-top:10px">' + esc(s.note) + '</p>' : '');
          list.appendChild(card);
        });
      }).catch(function () { list.innerHTML = '<p class="muted">Signallarni yuklab bo\'lmadi.</p>'; });
    }
    render();
    setInterval(render, 30000);
  }

  // ---------------- KALKULYATOR ----------------
  function setupCalculator() {
    var btn = $("cCalc");
    if (!btn) return;
    function num(id) { var v = parseFloat((($(id).value) || "").replace(",", ".")); return isFinite(v) ? v : NaN; }
    function pct(x) { return (x >= 0 ? "+" : "") + x.toFixed(2) + "%"; }
    btn.addEventListener("click", function () {
      var err = $("cErr"); err.textContent = "";
      var size = num("cSize"), entry = num("cEntry"), stop = num("cStop");
      if (!(size > 0)) { err.textContent = "Sarmoyani ($) kiriting."; return; }
      if (!(entry > 0)) { err.textContent = "Kirish narxini kiriting."; return; }
      if (!(stop > 0)) { err.textContent = "Stop narxini kiriting."; return; }
      if (stop >= entry) { err.textContent = "Stop narxi kirish narxidan past bo'lishi kerak."; return; }
      var coin = size / entry;
      var tps = [
        { name: "TP1", price: num("cTp1"), p: num("cTp1p") },
        { name: "TP2", price: num("cTp2"), p: num("cTp2p") },
        { name: "TP3", price: num("cTp3"), p: num("cTp3p") },
      ];
      var used = [], totalPct = 0, tpProfit = 0;
      for (var i = 0; i < tps.length; i++) {
        var t = tps[i];
        if (t.price > 0 && t.p > 0) {
          if (t.price <= entry) { err.textContent = t.name + " narxi kirish narxidan yuqori bo'lishi kerak."; return; }
          t.profit = coin * (t.p / 100) * (t.price - entry);
          totalPct += t.p; tpProfit += t.profit; used.push(t);
        }
      }
      if (!used.length) { err.textContent = "Kamida bitta TP narxi va ulushini kiriting."; return; }
      if (totalPct > 100.0001) { err.textContent = "Ulushlar yig'indisi 100% dan oshdi (" + totalPct + "%)."; return; }
      var loss = coin * (entry - stop);
      var rr = loss > 0 ? (tpProfit / loss) : 0;
      var stats = [
        { cls: "win", b: money(tpProfit), s: "Foyda (barcha TP) · " + pct(tpProfit / size * 100) },
        { cls: "lose", b: "-" + money(loss), s: "Zarar (Stop) · " + pct(-(loss / size * 100)) },
        { cls: "", b: coin.toLocaleString("en-US", { maximumFractionDigits: 6 }), s: "Coin miqdori" },
        { cls: "", b: (rr > 0 ? rr.toFixed(2) : "—") + " : 1", s: "Risk / Reward" },
      ];
      $("cStats").innerHTML = stats.map(function (x) { return '<div class="calc-stat ' + x.cls + '"><b>' + x.b + '</b><span>' + x.s + '</span></div>'; }).join("");
      var rows = used.map(function (t) {
        return '<div style="display:flex;justify-content:space-between;gap:10px;padding:8px 0;border-bottom:1px solid var(--border);font-size:13.5px"><span>' + t.name + ' · ' + t.p + '% · ' + t.price + '</span><b style="color:#3ddc97">' + money(t.profit) + '</b></div>';
      }).join("");
      if (totalPct < 99.9999) rows += '<p class="muted" style="font-size:12px;margin-top:8px">Diqqat: ulushlar ' + totalPct + '% — qolgan ' + (100 - totalPct).toFixed(0) + '% hisobga olinmadi.</p>';
      $("cBreak").innerHTML = '<div class="pill" style="margin-bottom:8px">Har bir TP bo\'yicha foyda</div>' + rows;
      $("cResult").style.display = "block";
    });
  }

  // ---------------- KABINET (profil, tarif, to'lov) ----------------
  var PERIOD_UZ = { daily: "Kunlik", monthly: "Oylik" };

  function loadKabinet() {
    loadTariffs();
    // profil
    var box = $("kabProfile");
    if (box) {
      if (window.CS3 && CS3.isLoggedIn()) {
        CS3.me().then(function (me) {
          var u = me.user || {};
          var sub = me.subscription;
          if (u.is_admin) { var w = $("drawerAdminWrap"); if (w) w.style.display = "block"; }
          box.innerHTML =
            '<div class="card" style="padding:18px;display:flex;align-items:center;gap:14px">' +
              '<div class="account-avatar">' + esc((u.full_name || "U").trim().charAt(0).toUpperCase()) + '</div>' +
              '<div style="flex:1"><div style="font-weight:700;font-size:16px">' + (u.is_admin ? "⚙ " : "") + esc(u.full_name || "Foydalanuvchi") + '</div>' +
              '<div class="muted" style="font-size:12.5px;font-family:\'Courier New\',monospace">ID: ' + esc(String(u.telegram_id || "")) + '</div>' +
              '<div style="font-size:13px;margin-top:4px">' + (sub ? ('Obuna: <b>' + esc(sub.tariff_name) + '</b> · ' + sub.days_left + ' kun qoldi') : 'Obuna: <span class="muted">yo\'q</span>') + '</div></div>' +
              (u.is_admin ? '<a href="admin.html" class="btn btn-outline" style="font-size:13px;padding:8px 12px">Admin</a>' : '') +
            '</div>';
        }).catch(function () { guestProfile(box); });
      } else {
        guestProfile(box);
      }
    }
  }

  function guestProfile(box) {
    box.innerHTML =
      '<div class="card" style="padding:22px;text-align:center">' +
        '<div style="font-size:34px;margin-bottom:10px">👤</div>' +
        '<h3 style="margin:0 0 6px">Hisobingizga kiring</h3>' +
        '<p class="muted" style="font-size:13px;margin-bottom:14px">Obuna va bo\'limlar uchun Telegram orqali kiring.</p>' +
        '<button class="btn btn-primary" id="kabLogin">Telegram orqali kirish</button>' +
      '</div>';
    var b = $("kabLogin");
    if (b) b.addEventListener("click", function () { CS3.connect(function () { location.reload(); }); });
  }

  function loadTariffs() {
    var wrap = $("tariffWrap");
    if (!wrap || !ready) return;
    Promise.all([
      fetch(base + "/api/tariffs").then(function (r) { return r.json(); }).catch(function () { return []; }),
      fetch(base + "/api/config").then(function (r) { return r.json(); }).catch(function () { return {}; }),
    ]).then(function (res) {
      var tariffs = res[0] || [], cfg = res[1] || {};
      // Har bir obuna nima ochishini aniq ko'rsatamiz.
      var FEATURES = {
        lite: ["✅ Signallar"],
        pro: ["✅ Signallar", "✅ Video darsliklar"],
        premium: ["✅ Video darsliklar", "✅ Strategiyalar", "✅ Jamoa (yopiq guruh)"],
      };
      if (!tariffs.length) { wrap.innerHTML = '<p class="muted">Tariflar tez orada.</p>'; }
      else {
        wrap.innerHTML = tariffs.map(function (t) {
          var per = (t.periods || []).map(function (p) {
            return '<div style="display:flex;justify-content:space-between;font-size:13.5px;margin-top:6px"><span class="muted">' + esc(PERIOD_UZ[p.period] || p.name) + '</span><b>' + esc(p.price) + ' ' + esc(p.currency) + '</b></div>';
          }).join("");
          var feats = (FEATURES[t.code] || t.sections || []).map(function (s) { return '<li>' + esc(s) + '</li>'; }).join("");
          return '<div class="tier' + (t.code === "premium" ? " pop" : "") + '"><h3>' + esc(t.name) + '</h3>' +
            (t.coming_soon ? '<p class="pill" style="display:inline-block;margin-bottom:6px">Tez kunda</p>' : '') +
            per + (feats ? '<ul style="list-style:none;padding-left:0">' + feats + '</ul>' : '') + '</div>';
        }).join("");
      }
      var lead = $("kabTariffLead");
      if (cfg.free_mode && lead) lead.textContent = "Hozircha barcha bo'limlar BEPUL ochiq. To'liq obuna tez kunda.";
      if (cfg.payments_enabled) setupPayment(tariffs);
    });
  }

  function setupPayment(tariffs) {
    var wrap = $("paymentWrap");
    if (!wrap) return;
    wrap.style.display = "block";
    var pt = $("payTariff"), pp = $("payPeriod");
    pt.innerHTML = tariffs.map(function (t) { return '<option value="' + esc(t.code) + '">' + esc(t.name) + '</option>'; }).join("");
    pp.innerHTML = '<option value="monthly">Oylik</option><option value="daily">Kunlik</option>';
    // hamyon
    fetch(base + "/api/wallet").then(function (r) { return r.json(); }).then(function (w) {
      var box = $("walletBox");
      if (box) box.innerHTML = '<div style="font-size:12.5px;color:var(--muted)">Hamyon (' + esc(w.network || "") + ')</div><div style="font-family:\'Courier New\',monospace;font-size:13.5px;word-break:break-all;margin-top:4px">' + esc(w.address || "—") + '</div>';
    }).catch(function () {});
    var btn = $("paySubmit");
    btn.addEventListener("click", function () {
      var st = $("payStatus");
      if (!(window.CS3 && CS3.isLoggedIn())) { st.textContent = "Avval Telegram orqali kiring."; st.style.color = "#e6484f"; return; }
      var f = $("payReceipt");
      if (!f || !f.files || !f.files.length) { st.textContent = "Chek (skrinshot) tanlang."; st.style.color = "#e6484f"; return; }
      var fd = new FormData();
      fd.append("tariff", pt.value);
      fd.append("period", pp.value);
      fd.append("receipt", f.files[0]);
      btn.disabled = true; st.textContent = "Yuborilmoqda…"; st.style.color = "var(--muted)";
      fetch(base + "/api/payments", { method: "POST", headers: { "Authorization": "Bearer " + CS3.getToken() }, body: fd })
        .then(function (res) { return res.json().catch(function () { return {}; }).then(function (b) { if (!res.ok) throw new Error(b.detail || ("Xatolik (" + res.status + ")")); return b; }); })
        .then(function (b) { st.textContent = b.message || "✅ Chek yuborildi."; st.style.color = "#3ddc97"; f.value = ""; })
        .catch(function (e) { st.textContent = e.message; st.style.color = "#e6484f"; })
        .then(function () { btn.disabled = false; });
    });
  }
})();
