<%
/* The FAQ "wheel" on the Education page (education.qmd, listing id faq-wheel).

   One card per FAQ in a row that scrolls sideways: swipe or trackpad-scroll
   it, or use the arrow buttons. The arrows wrap around, so "next" on the
   last card goes back to FAQ #1.

   Each card shows the FAQ's number and date, the question, the description
   and the thumbnail (`image:`). The number comes from the title, which is
   written "FAQ #4: The question?"; the card shows "FAQ #4" above the
   question. */
%>
```{=html}
<div class="faq-wheel">
<button class="faq-wheel-btn faq-wheel-prev" type="button" aria-label="Previous question"><svg viewBox="0 0 16 16" width="18" height="18" aria-hidden="true"><path d="M10.5 2.5 5 8l5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
<div class="faq-wheel-track list" tabindex="0" role="region" aria-label="Frequently asked questions">
<% for (const item of items) {
     const title = item.title || "";
     const m = title.match(/^FAQ\s*#\s*(\d+)\s*:\s*(.*)$/i);
     const num = m ? m[1] : "";
     const question = m ? m[2] : title.replace(/^FAQ\s*:\s*/i, ""); %>
<a class="faq-card" href="<%- item.path %>" <%= metadataAttrs(item) %>>
<div class="faq-card-img"><% if (item.image) { %><img loading="lazy" src="<%- item.image %>" alt=""><% } %></div>
<div class="faq-card-meta"><span class="faq-card-num">FAQ<%= num ? " #" + num : "" %></span><% if (item.date) { %> &middot; <%= item.date %><% } %></div>
<h3 class="faq-card-title no-anchor"><%= question %></h3>
<% if (item.description) { %><p class="faq-card-desc"><%= item.description %></p><% } %>
</a>
<% } %>
</div>
<button class="faq-wheel-btn faq-wheel-next" type="button" aria-label="Next question"><svg viewBox="0 0 16 16" width="18" height="18" aria-hidden="true"><path d="M5.5 2.5 11 8l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
</div>
<script>
(function () {
  var smooth = !(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  document.querySelectorAll(".faq-wheel").forEach(function (wheel) {
    if (wheel.dataset.ready) return;
    wheel.dataset.ready = "1";
    var track = wheel.querySelector(".faq-wheel-track");
    function step() {
      var card = track.querySelector(".faq-card");
      if (!card) return track.clientWidth;
      var gap = parseFloat(getComputedStyle(track).columnGap) || 0;
      return card.getBoundingClientRect().width + gap;
    }
    function go(dir) {
      var max = track.scrollWidth - track.clientWidth;
      var behavior = smooth ? "smooth" : "auto";
      if (dir > 0 && track.scrollLeft >= max - 4) track.scrollTo({ left: 0, behavior: behavior });
      else if (dir < 0 && track.scrollLeft <= 4) track.scrollTo({ left: max, behavior: behavior });
      else track.scrollBy({ left: dir * step(), behavior: behavior });
    }
    wheel.querySelector(".faq-wheel-prev").addEventListener("click", function () { go(-1); });
    wheel.querySelector(".faq-wheel-next").addEventListener("click", function () { go(1); });
    track.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight") { e.preventDefault(); go(1); }
      if (e.key === "ArrowLeft") { e.preventDefault(); go(-1); }
    });
    function update() {
      wheel.classList.toggle("no-overflow", track.scrollWidth <= track.clientWidth + 4);
    }
    window.addEventListener("resize", update);
    window.addEventListener("load", update);
    update();
  });
})();
</script>
```
