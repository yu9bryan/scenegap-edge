// SceneGap Edge project page: fade-in on scroll, active nav link, and a play button for the GIFs when the
// visitor prefers reduced motion (the <picture> then shows a still frame until asked).
(function () {
  "use strict";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var items = document.querySelectorAll(".reveal");

  if (reduce || !("IntersectionObserver" in window)) {
    items.forEach(function (el) { el.classList.add("in"); });
  } else {
    var pending = Array.prototype.slice.call(items);
    var show = function (el) { el.classList.add("in"); };
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { show(e.target); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
    items.forEach(function (el) { io.observe(el); });
    // Safety net: content must never stay hidden, even where observer callbacks are delayed (background tabs,
    // jumps to an anchor). Anything above the bottom of the viewport is shown on scroll, resize and hash change.
    var sweep = function () {
      var limit = window.innerHeight;
      pending = pending.filter(function (el) {
        if (el.classList.contains("in")) return false;
        if (el.getBoundingClientRect().top < limit) { show(el); return false; }
        return true;
      });
      if (!pending.length) {
        window.removeEventListener("scroll", sweep);
        window.removeEventListener("resize", sweep);
        window.removeEventListener("hashchange", sweep);
      }
    };
    window.addEventListener("scroll", sweep, { passive: true });
    window.addEventListener("resize", sweep);
    window.addEventListener("hashchange", sweep);
    window.addEventListener("load", sweep);
  }

  // Reduced motion: the still frame is shown; this button swaps in the animation for that one figure.
  document.querySelectorAll(".play-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var fig = btn.closest(".shot");
      var source = fig && fig.querySelector("picture source");
      var img = fig && fig.querySelector("img");
      if (!source || !img) return;
      source.remove();
      img.src = img.getAttribute("src");
      fig.classList.add("playing");
    });
  });

  // Highlight the nav link of the section in view.
  var links = Array.prototype.slice.call(document.querySelectorAll(".nav a[href^='#']"));
  var sections = links.map(function (a) { return document.querySelector(a.getAttribute("href")); }).filter(Boolean);
  if ("IntersectionObserver" in window && sections.length) {
    var spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        links.forEach(function (a) {
          var on = a.getAttribute("href") === "#" + e.target.id;
          a.classList.toggle("is-active", on);
          if (on) { a.setAttribute("aria-current", "true"); } else { a.removeAttribute("aria-current"); }
        });
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    sections.forEach(function (s) { spy.observe(s); });
  }
})();
