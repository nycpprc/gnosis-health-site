/* Analytics consent: Google Analytics (GA4) loads only after the visitor clicks Accept.
   Consent Mode defaults to "denied" (set inline in <head>); no request to Google happens before Accept.
   Choice is stored in localStorage ("gh-analytics" = "granted" | "denied"). */
(function () {
  var s = document.currentScript, id = s && s.getAttribute('data-ga-id');
  var KEY = 'gh-analytics', box = document.getElementById('consent');
  if (!id || !box) return;
  var loaded = false;

  function get() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function set(v) { try { v ? localStorage.setItem(KEY, v) : localStorage.removeItem(KEY); } catch (e) {} }

  function load() {
    if (loaded) return; loaded = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { dataLayer.push(arguments); };
    gtag('consent', 'update', { analytics_storage: 'granted' });
    gtag('js', new Date());
    gtag('config', id, { allow_google_signals: false, allow_ad_personalization_signals: false, cookie_flags: 'SameSite=Lax;Secure' });
    var g = document.createElement('script');
    g.async = true; g.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(id);
    document.head.appendChild(g);
  }
  function decide(v) {
    set(v); box.hidden = true;
    if (v === 'granted') load();
  }

  if (navigator.globalPrivacyControl === true && get() !== 'granted') { set('denied'); }
  var c = get();
  if (c === 'granted') load();
  else if (c !== 'denied') box.hidden = false;

  [].forEach.call(box.querySelectorAll('[data-consent]'), function (b) {
    b.addEventListener('click', function () { decide(b.getAttribute('data-consent')); });
  });
  [].forEach.call(document.querySelectorAll('[data-consent-reset]'), function (b) {
    b.addEventListener('click', function () {
      set(null);
      if (loaded) { window.location.reload(); return; }   /* already-loaded GA cannot be unloaded: reload with no choice */
      box.hidden = false; box.querySelector('[data-consent="granted"]').focus();
    });
  });
})();
