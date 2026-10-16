/* Progressive enhancement: year/tag chips + full-text search for the blog index. */
(function () {
  var box = document.getElementById('filters');
  if (!box) return;
  box.hidden = false;
  var q = document.getElementById('q');
  var status = document.getElementById('status');
  var empty = document.getElementById('empty');
  var rows = [].slice.call(document.querySelectorAll('.card[data-slug]'));
  var groups = [].slice.call(document.querySelectorAll('.year-group'));
  var yearBtns = [].slice.call(box.querySelectorAll('[data-year]'));
  var tagBtns = [].slice.call(box.querySelectorAll('[data-tag]'));
  var year = 'all', tag = null, full = null, loading = false;

  function load() {
    if (full || loading) return;
    loading = true;
    fetch(box.getAttribute('data-search-url')).then(function (r) { return r.json(); }).then(function (d) {
      full = {}; d.forEach(function (i) { full[i.s] = i.t; }); apply();
    }).catch(function () { loading = false; });
  }
  function apply() {
    var terms = q.value.toLowerCase().split(/\s+/).filter(Boolean), shown = 0;
    rows.forEach(function (r) {
      var hay = full ? full[r.getAttribute('data-slug')] : r.getAttribute('data-text');
      var ok = (year === 'all' || r.getAttribute('data-year') === year) &&
               (!tag || ('|' + r.getAttribute('data-tags') + '|').indexOf('|' + tag + '|') > -1) &&
               terms.every(function (t) { return (hay || r.getAttribute('data-text')).indexOf(t) > -1; });
      r.hidden = !ok; if (ok) shown++;
    });
    groups.forEach(function (g) { g.hidden = !g.querySelector('.card:not([hidden])'); });
    empty.hidden = shown > 0;
    status.textContent = (terms.length || year !== 'all' || tag) ? shown + (shown === 1 ? ' post' : ' posts') + ' shown' : '';
  }
  q.addEventListener('focus', load);
  q.addEventListener('input', function () { load(); apply(); });
  yearBtns.forEach(function (b) {
    b.addEventListener('click', function () {
      year = b.getAttribute('data-year');
      yearBtns.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      apply();
    });
  });
  tagBtns.forEach(function (b) {
    b.addEventListener('click', function () {
      tag = (tag === b.getAttribute('data-tag')) ? null : b.getAttribute('data-tag');
      tagBtns.forEach(function (x) { x.setAttribute('aria-pressed', x.getAttribute('data-tag') === tag ? 'true' : 'false'); });
      apply();
    });
  });
})();
