<%
/* The FAQ "wheel" on the Education page (education.qmd, listing id faq-wheel).

   One card per FAQ in a row that scrolls sideways forever in either
   direction: swipe or trackpad-scroll it, or use the arrow buttons or the
   arrow keys. After the last FAQ comes FAQ #1 again.

   How the endless loop works: the script below adds copies of the whole set
   of cards on both sides of the real ones, and whenever scrolling stops it
   quietly jumps back to the same spot in the real set. The copies are hidden
   from screen readers and the Tab key.

   Each card shows the FAQ's number, the question, the description and the
   thumbnail (`image:`). The number comes from the title, which is written
   "FAQ #4: The question?"; the card shows "FAQ #4" above the question.

   The track deliberately has no `list` class, so Quarto's listing script
   (List.js) leaves these cards alone. */
%>
```{=html}
<div class="faq-wheel">
<button class="faq-wheel-btn faq-wheel-prev" type="button" aria-label="Previous question"><svg viewBox="0 0 16 16" width="18" height="18" aria-hidden="true"><path d="M10.5 2.5 5 8l5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
<div class="faq-wheel-track" tabindex="0" role="region" aria-label="Frequently asked questions">
<% for (const item of items) {
     const title = item.title || "";
     const m = title.match(/^FAQ\s*#\s*(\d+)\s*:\s*(.*)$/i);
     const num = m ? m[1] : "";
     const question = m ? m[2] : title.replace(/^FAQ\s*:\s*/i, ""); %>
<a class="faq-card" href="<%- item.path %>">
<div class="faq-card-img"><% if (item.image) { %><img loading="lazy" src="<%- item.image %>" alt=""><% } %></div>
<div class="faq-card-meta"><span class="faq-card-num">FAQ<%= num ? " #" + num : "" %></span></div>
<h3 class="faq-card-title no-anchor"><%= question %></h3>
<% if (item.description) { %><p class="faq-card-desc"><%= item.description %></p><% } %>
</a>
<% } %>
</div>
<button class="faq-wheel-btn faq-wheel-next" type="button" aria-label="Next question"><svg viewBox="0 0 16 16" width="18" height="18" aria-hidden="true"><path d="M5.5 2.5 11 8l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
</div>
<script>
(function () {
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function setUp(wheel) {
    if (wheel.dataset.ready) return;
    wheel.dataset.ready = "1";
    var track = wheel.querySelector(".faq-wheel-track");
    var originals = Array.prototype.slice.call(track.querySelectorAll(".faq-card"));
    var n = originals.length;
    if (n < 2) { wheel.classList.add("no-loop"); return; }

    var base = 0, setW = 0, step = 0, timer = null;

    function measureStep() {
      var gap = parseFloat(getComputedStyle(track).columnGap) || 0;
      return originals[0].getBoundingClientRect().width + gap;
    }

    // (Re)build the copies on both sides of the real cards.
    function build(keepIndex) {
      track.querySelectorAll(".faq-card-clone").forEach(function (c) { c.remove(); });
      step = measureStep();
      setW = step * n;
      var perSide = Math.ceil((2 * track.clientWidth) / setW) + 1;
      for (var k = 0; k < perSide; k++) {
        originals.forEach(function (card) {
          track.appendChild(clone(card));
        });
        for (var i = n - 1; i >= 0; i--) {
          track.insertBefore(clone(originals[i]), track.firstChild);
        }
      }
      base = originals[0].offsetLeft - track.firstElementChild.offsetLeft;
      track.scrollLeft = base + (keepIndex || 0) * step;
    }

    function clone(card) {
      var c = card.cloneNode(true);
      c.classList.add("faq-card-clone");
      c.setAttribute("aria-hidden", "true");
      c.setAttribute("tabindex", "-1");
      return c;
    }

    function currentIndex() {
      var i = Math.round((track.scrollLeft - base) / step) % n;
      return (i + n) % n;
    }

    // Jump back into the real set without moving what's on screen.
    function recentre() {
      var x = track.scrollLeft;
      var rel = (((x - base) % setW) + setW) % setW;
      var target = base + rel;
      if (Math.abs(target - x) > 1) track.scrollLeft = target;
    }

    function go(dir) {
      track.scrollBy({ left: dir * step, behavior: reduce ? "auto" : "smooth" });
    }

    wheel.querySelector(".faq-wheel-prev").addEventListener("click", function () { go(-1); });
    wheel.querySelector(".faq-wheel-next").addEventListener("click", function () { go(1); });
    track.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight") { e.preventDefault(); go(1); }
      if (e.key === "ArrowLeft") { e.preventDefault(); go(-1); }
    });

    if ("onscrollend" in window) {
      track.addEventListener("scrollend", recentre);
    } else {
      track.addEventListener("scroll", function () {
        clearTimeout(timer);
        timer = setTimeout(recentre, 160);
      });
    }

    var resizeTimer = null;
    window.addEventListener("resize", function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () { build(currentIndex()); }, 150);
    });

    build(0);
  }

  function start() { document.querySelectorAll(".faq-wheel").forEach(setUp); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
</script>
```
