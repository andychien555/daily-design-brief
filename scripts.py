"""Inline JavaScript snippets for the daily-design-brief HTML output."""

THEME_BOOTSTRAP_SCRIPT = """  <script>
    (function() {
      try {
        var t = localStorage.getItem('theme');
        if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t;
      } catch (e) {}
    })();
  </script>"""


INTERACTIVE_SCRIPT = """<script>
  (function() {
    document.querySelectorAll('dialog').forEach(function(d) {
      d.addEventListener('click', function(e) { if (e.target === d) d.close(); });
    });
    var icon = document.querySelector('.theme-icon');
    if (icon) icon.textContent = document.documentElement.dataset.theme === 'light' ? '☀' : '☾';
  })();
  function toggleTheme() {
    var cur = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
    var next = cur === 'light' ? 'dark' : 'light';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch (e) {}
    document.querySelectorAll('.theme-icon').forEach(function(el) {
      el.textContent = next === 'light' ? '☀' : '☾';
    });
  }
</script>"""


ARCHIVE_RAIL_SCRIPT = """
<script>
(function() {
  var aside = document.querySelector('.archive-rail');
  if (!aside) return;
  var base = aside.dataset.base || '';
  var active = aside.dataset.active || '';
  var list = aside.querySelector('.rail-list');
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function pad3(n) { return ('000' + n).slice(-3); }
  fetch(base + 'archive.json', { cache: 'no-cache' })
    .then(function(r) { return r.json(); })
    .then(function(archive) {
      if (!Array.isArray(archive) || !archive.length) {
        list.innerHTML = '<div class=\"rail-loading\">尚無存檔</div>';
        return;
      }
      var latest = archive[0].date;
      var sortedDates = archive.map(function(e) { return e.date; }).sort();
      var rank = {};
      sortedDates.forEach(function(d, i) { rank[d] = i + 1; });
      var html = archive.map(function(e) {
        var no = rank[e.date] || 1;
        var total = (e.total != null) ? e.total : '?';
        var headline = e.headline || ((e.sources || []).join(' · ')) || '—';
        var isActive = e.date === active;
        var href;
        if (e.date === latest) href = base + 'index.html';
        else if (base) href = e.date + '.html';
        else href = 'briefs/' + e.date + '.html';
        return '<a class=\"rail-item' + (isActive ? ' rail-item-current' : '') + '\" href=\"' + href + '\">' +
          '<div class=\"rail-meta\"><span>№' + pad3(no) + '</span><span>' + esc(total) + ' 篇</span></div>' +
          '<div class=\"rail-headline\">' + esc(headline) + '</div>' +
          '<div class=\"rail-date\">' + esc(e.date_display) + '</div>' +
          '</a>';
      }).join('');
      list.innerHTML = html;
    })
    .catch(function(err) {
      list.innerHTML = '<div class=\"rail-loading\">載入失敗</div>';
      console.error('archive load failed', err);
    });
})();
</script>
"""
