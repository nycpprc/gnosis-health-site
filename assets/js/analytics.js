/* Google Analytics (GA4), loaded by default with opt-out.
   Not loaded if: localStorage["gh-analytics"] === "denied" (opted out on /privacy/),
   the browser sends Global Privacy Control, or Do Not Track is "1".
   No ads, no ad personalization, no Google signals. */
(function () {
  var s = document.currentScript, id = s && s.getAttribute('data-ga-id');
  if (!id) return;
  var KEY = 'gh-analytics';
  function get() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function set(v) { try { v ? localStorage.setItem(KEY, v) : localStorage.removeItem(KEY); } catch (e) {} }
  var gpc = navigator.globalPrivacyControl === true;
  var dnt = navigator.doNotTrack === '1' || window.doNotTrack === '1' || navigator.msDoNotTrack === '1';
  var optedOut = get() === 'denied';

  if (!gpc && !dnt && !optedOut) {
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { dataLayer.push(arguments); };
    gtag('consent', 'default', { analytics_storage: 'granted', ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied' });
    gtag('js', new Date());
    gtag('config', id, { allow_google_signals: false, allow_ad_personalization_signals: false, cookie_flags: 'SameSite=Lax;Secure' });
    var g = document.createElement('script');
    g.async = true; g.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(id);
    document.head.appendChild(g);
  }

  /* /privacy/ controls */
  var box = document.querySelector('[data-analytics-controls]');
  if (!box) return;
  var status = box.querySelector('[data-analytics-status]');
  var off = box.querySelector('[data-analytics-off]'), on = box.querySelector('[data-analytics-on]');
  function render() {
    var o = get() === 'denied';
    if (gpc || dnt) {
      status.textContent = 'Analytics is off: your browser sends a ' + (gpc ? 'Global Privacy Control' : 'Do Not Track') + ' signal, so nothing is loaded.';
      off.hidden = true; on.hidden = true; return;
    }
    status.textContent = o ? 'Analytics is off on this browser.' : 'Analytics is on for this browser.';
    off.hidden = o; on.hidden = !o;
  }
  off.addEventListener('click', function () { set('denied'); window.location.reload(); });
  on.addEventListener('click', function () { set(null); window.location.reload(); });
  render();
})();
