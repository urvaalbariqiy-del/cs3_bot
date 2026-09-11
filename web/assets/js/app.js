// ======================= APP SHELL: tablar, drawer, PWA =======================
(function(){

  function switchTab(tabName){
    document.querySelectorAll(".app-page").forEach(function(p){
      p.classList.toggle("active", p.dataset.tab === tabName);
    });
    document.querySelectorAll(".app-tab-btn").forEach(function(b){
      b.classList.toggle("active", b.dataset.tab === tabName);
    });
    localStorage.setItem("cs3_active_tab", tabName);
    window.scrollTo({top:0, behavior:"instant"});
  }

  function switchSubtab(group, sub){
    document.querySelectorAll('.app-subpanel[data-group="' + group + '"]').forEach(function(p){
      p.classList.toggle("active", p.dataset.sub === sub);
    });
    document.querySelectorAll('.app-subtab-btn[data-group="' + group + '"]').forEach(function(b){
      b.classList.toggle("active", b.dataset.sub === sub);
    });
  }

  document.addEventListener("DOMContentLoaded", function(){
    // ---- Bottom tabs ----
    document.querySelectorAll(".app-tab-btn").forEach(function(btn){
      btn.addEventListener("click", function(){ switchTab(btn.dataset.tab); });
    });
    var savedTab = localStorage.getItem("cs3_active_tab") || "home";
    switchTab(savedTab);

    // ---- Sub-tabs ----
    document.querySelectorAll(".app-subtab-btn").forEach(function(btn){
      btn.addEventListener("click", function(){
        switchSubtab(btn.dataset.group, btn.dataset.sub);
      });
    });

    // ---- Hamburger drawer ----
    var drawer = document.getElementById("appDrawer");
    var overlay = document.getElementById("appDrawerOverlay");
    function openDrawer(){ drawer.classList.add("open"); overlay.classList.add("open"); }
    function closeDrawer(){ drawer.classList.remove("open"); overlay.classList.remove("open"); }
    document.getElementById("appHamburgerBtn")?.addEventListener("click", openDrawer);
    document.getElementById("appDrawerCloseBtn")?.addEventListener("click", closeDrawer);
    overlay?.addEventListener("click", closeDrawer);

    // ---- Til / tema segmentlari (drawer ichida) ----
    document.querySelectorAll("#appLangSeg button").forEach(function(btn){
      btn.addEventListener("click", function(){
        document.querySelectorAll("#appLangSeg button").forEach(function(b){ b.classList.remove("active"); });
        btn.classList.add("active");
        if(typeof applyLang === "function") applyLang(btn.dataset.lang);
      });
    });
    document.querySelectorAll("#appThemeSeg button").forEach(function(btn){
      btn.addEventListener("click", function(){
        document.querySelectorAll("#appThemeSeg button").forEach(function(b){ b.classList.remove("active"); });
        btn.classList.add("active");
        document.documentElement.setAttribute("data-theme", btn.dataset.theme);
        localStorage.setItem("cs3_theme", btn.dataset.theme);
      });
    });
    // boshlang'ich holatni belgilash
    var curLang = localStorage.getItem("cs3_lang") || "uz";
    var curTheme = localStorage.getItem("cs3_theme") || "dark";
    document.querySelectorAll("#appLangSeg button").forEach(function(b){ b.classList.toggle("active", b.dataset.lang === curLang); });
    document.querySelectorAll("#appThemeSeg button").forEach(function(b){ b.classList.toggle("active", b.dataset.theme === curTheme); });

    // ---- Obuna (Lite/Pro/Premium) tanlash — hozircha faqat UI, saqlab qo'yiladi ----
    document.querySelectorAll(".app-tier-card").forEach(function(card){
      card.addEventListener("click", function(){
        document.querySelectorAll(".app-tier-card").forEach(function(c){ c.classList.remove("selected"); });
        card.classList.add("selected");
        localStorage.setItem("cs3_tier_interest", card.dataset.tier);
      });
    });
    var savedTier = localStorage.getItem("cs3_tier_interest");
    if(savedTier){
      document.querySelectorAll(".app-tier-card").forEach(function(c){
        c.classList.toggle("selected", c.dataset.tier === savedTier);
      });
    }

    // ---- Ichki "boshqa tabga o'tish" linklari (data-goto-tab) ----
    document.querySelectorAll("[data-goto-tab]").forEach(function(el){
      el.addEventListener("click", function(e){
        e.preventDefault();
        switchTab(el.dataset.gotoTab);
        if(el.dataset.gotoSub){
          switchSubtab(el.dataset.gotoTab, el.dataset.gotoSub);
        }
      });
    });

    // ---- Service worker + PWA o'rnatish ----
    if("serviceWorker" in navigator){
      navigator.serviceWorker.register("service-worker.js").catch(function(){});
    }
    var deferredPrompt = null;
    var installBtn = document.getElementById("appInstallBtn");
    window.addEventListener("beforeinstallprompt", function(e){
      e.preventDefault();
      deferredPrompt = e;
      if(installBtn) installBtn.style.display = "block";
    });
    installBtn?.addEventListener("click", function(){
      if(!deferredPrompt) return;
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function(){ deferredPrompt = null; });
    });
  });
})();
