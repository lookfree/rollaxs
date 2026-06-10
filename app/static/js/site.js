// Rollax site JS — 汉堡菜单 / 返回顶部 / Hero 视频 / 下拉菜单可达性
(function () {
  "use strict";

  // --- 汉堡菜单(≤900px) ---------------------------------------------------
  var toggle = document.querySelector(".nav-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var open = document.body.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // --- 返回顶部 -------------------------------------------------------------
  var backTop = document.querySelector(".back-to-top");
  if (backTop) {
    backTop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  // --- 首页 Hero 视频:点击播放按钮换入 <video> -------------------------------
  var hero = document.querySelector(".hero--home[data-video]");
  var play = hero && hero.querySelector(".hero-play");
  if (hero && play) {
    play.addEventListener("click", function () {
      var src = hero.getAttribute("data-video");
      if (!src) return;
      var video = document.createElement("video");
      video.src = src.indexOf("/") === 0 || src.indexOf("http") === 0 ? src : "/uploads/" + src;
      video.autoplay = true;
      video.controls = true;
      video.playsInline = true;
      video.className = "hero__video";
      hero.classList.add("hero--playing");
      hero.appendChild(video);
      play.remove();
    });
  }

  // --- 顶栏下拉:键盘焦点 / 触屏点击支持(hover 由 CSS 负责) -------------------
  document.querySelectorAll(".topbar__nav .nav-item").forEach(function (item) {
    var dropdown = item.querySelector(".nav-dropdown");
    if (!dropdown) return;
    item.addEventListener("focusin", function () { item.classList.add("open"); });
    item.addEventListener("focusout", function () {
      // 焦点完全离开 nav-item 后才收起
      setTimeout(function () {
        if (!item.contains(document.activeElement)) item.classList.remove("open");
      }, 0);
    });
  });
})();
