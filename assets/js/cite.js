/* Citation popovers: hover, focus or tap opens; Escape / outside tap closes. */
(function () {
  var cites = [].slice.call(document.querySelectorAll('.cite'));
  if (!cites.length) return;
  var timers = new WeakMap();
  function place(c) {
    var pop = c.querySelector('.cite__pop'), btn = c.querySelector('.cite__btn');
    pop.style.left = '0px'; pop.classList.remove('cite__pop--up');
    var m = 12, r = pop.getBoundingClientRect(), b = btn.getBoundingClientRect();
    var want = b.left + b.width / 2 - r.width / 2;           // centre under the marker
    want = Math.max(m, Math.min(want, window.innerWidth - m - r.width));  // keep inside viewport
    pop.style.left = (want - r.left) + 'px';
    var rr = pop.getBoundingClientRect();                    // flip above the marker if it would run off the bottom
    if (rr.bottom > window.innerHeight - 8 && b.top - rr.height - 12 > 8) pop.classList.add('cite__pop--up');
  }
  function open(c) {
    clearTimeout(timers.get(c));
    cites.forEach(function (o) { if (o !== c) close(o); });
    c.querySelector('.cite__pop').hidden = false;
    c.querySelector('.cite__btn').setAttribute('aria-expanded', 'true');
    place(c);
  }
  function close(c) {
    c.querySelector('.cite__pop').hidden = true;
    c.querySelector('.cite__btn').setAttribute('aria-expanded', 'false');
  }
  function later(c) { clearTimeout(timers.get(c)); timers.set(c, setTimeout(function () { close(c); }, 180)); }
  cites.forEach(function (c) {
    var btn = c.querySelector('.cite__btn');
    var hoverable = window.matchMedia('(hover: hover)').matches;
    if (hoverable) {
      c.addEventListener('mouseenter', function () { open(c); });
      c.addEventListener('mouseleave', function () { if (!c.contains(document.activeElement)) later(c); else later(c); });
    }
    c.addEventListener('focusin', function () { if (hoverable) open(c); });
    c.addEventListener('focusout', function (e) { if (!c.contains(e.relatedTarget)) later(c); });
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      if (btn.getAttribute('aria-expanded') === 'true' && !hoverable) close(c); else open(c);
    });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    cites.forEach(function (c) { if (!c.querySelector('.cite__pop').hidden) { close(c); if (c.contains(document.activeElement)) c.querySelector('.cite__btn').focus(); } });
  });
  document.addEventListener('click', function (e) { cites.forEach(function (c) { if (!c.contains(e.target)) close(c); }); });
  window.addEventListener('resize', function () { cites.forEach(function (c) { if (!c.querySelector('.cite__pop').hidden) place(c); }); });
})();
