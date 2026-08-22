"""Inline JavaScript snippets for the daily-design-brief HTML output."""

THEME_BOOTSTRAP_SCRIPT = """  <script>
    (function() {
      try {
        var t = localStorage.getItem('theme');
        if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t;
        if (localStorage.getItem('rail-collapsed') === '1') {
          document.documentElement.dataset.rail = 'collapsed';
        }
      } catch (e) {}
    })();
  </script>"""


INTERACTIVE_SCRIPT = """<script>
  (function() {
    document.querySelectorAll('dialog').forEach(function(d) {
      d.addEventListener('click', function(e) { if (e.target === d) d.close(); });
    });
    // Light is canon: an unset data-theme means light, not dark.
    var icon = document.querySelector('.theme-icon');
    if (icon) icon.textContent = document.documentElement.dataset.theme === 'dark' ? '☾' : '☀';

    var railToggle = document.querySelector('.rail-toggle');
    var railDrawer = document.querySelector('.rail-drawer-toggle');
    var railBackdrop = document.querySelector('.rail-backdrop');
    var mobileMQ = window.matchMedia('(max-width: 980px)');

    function closeDrawer() {
      document.body.classList.remove('rail-drawer-open');
      if (railDrawer) railDrawer.setAttribute('aria-expanded', 'false');
    }
    function openDrawer() {
      document.body.classList.add('rail-drawer-open');
      if (railDrawer) railDrawer.setAttribute('aria-expanded', 'true');
    }

    if (railToggle) {
      var collapsed = document.documentElement.dataset.rail === 'collapsed';
      railToggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
      railToggle.setAttribute('aria-label', collapsed ? '展開側欄' : '收合側欄');
      railToggle.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        if (mobileMQ.matches) {
          closeDrawer();
          return;
        }
        var next = document.documentElement.dataset.rail !== 'collapsed';
        if (next) document.documentElement.dataset.rail = 'collapsed';
        else delete document.documentElement.dataset.rail;
        try { localStorage.setItem('rail-collapsed', next ? '1' : '0'); } catch (err) {}
        railToggle.setAttribute('aria-expanded', next ? 'false' : 'true');
        railToggle.setAttribute('aria-label', next ? '展開側欄' : '收合側欄');
      });
    }

    if (railDrawer) {
      railDrawer.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        if (document.body.classList.contains('rail-drawer-open')) closeDrawer();
        else openDrawer();
      });
    }
    if (railBackdrop) {
      railBackdrop.addEventListener('click', closeDrawer);
    }
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && document.body.classList.contains('rail-drawer-open')) {
        closeDrawer();
      }
    });
    // Close drawer when navigating to an archive item (visual feedback before nav).
    document.addEventListener('click', function(e) {
      if (e.target.closest('.rail-item')) closeDrawer();
    });
    // If viewport grows past mobile breakpoint, drop transient drawer state.
    mobileMQ.addEventListener('change', function(ev) {
      if (!ev.matches) closeDrawer();
    });
  })();
  function toggleTheme() {
    var cur = document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
    var next = cur === 'light' ? 'dark' : 'light';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch (e) {}
    document.querySelectorAll('.theme-icon').forEach(function(el) {
      el.textContent = next === 'dark' ? '☾' : '☀';
    });
  }
</script>"""


# Raw string: every backslash below is emitted verbatim into the page's JS.
ARCHIVE_RAIL_SCRIPT = r"""
<script>
(function() {
  var aside = document.querySelector('.archive-rail');
  if (!aside) return;
  var base = aside.dataset.base || '';
  var active = aside.dataset.active || '';
  var list = aside.querySelector('.rail-list');
  var input = aside.querySelector('.rail-search-input');
  var clearBtn = aside.querySelector('.rail-search-clear');
  var status = aside.querySelector('.rail-search-status');

  var archive = null;      // archive.json — drives the default rail listing
  var indexPromise = null; // search-index.json — fetched lazily on first query
  var latest = '';
  var query = '';

  var KIND_LABEL = { podcast: '財經', article: '好文', tweet: '推文', product: 'Product Hunt' };

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function pad3(n) { return ('000' + n).slice(-3); }
  function escRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
  function note(msg) { list.innerHTML = '<div class="rail-loading">' + esc(msg) + '</div>'; }

  function hrefFor(date) {
    if (date === latest) return base + 'index.html';
    return base ? date + '.html' : 'briefs/' + date + '.html';
  }

  /* ─────────── default listing ─────────── */
  function renderArchive() {
    if (!archive) return;
    if (!archive.length) { note('尚無存檔'); return; }
    var sorted = archive.map(function(e) { return e.date; }).sort();
    var rank = {};
    sorted.forEach(function(d, i) { rank[d] = i + 1; });
    list.innerHTML = archive.map(function(e) {
      var total = (e.total != null) ? e.total : '?';
      var headline = e.headline || ((e.sources || []).join(' · ')) || '—';
      /* e.no is the stamped issue number; positional rank is the fallback for
         entries written before generate_html started recording it. */
      var no = e.no || rank[e.date] || 1;
      return '<a class="rail-item' + (e.date === active ? ' rail-item-current' : '') +
        '" href="' + hrefFor(e.date) + '">' +
        '<div class="rail-meta"><span>№' + pad3(no) + '</span><span>' + esc(total) + ' 篇</span></div>' +
        '<div class="rail-headline">' + esc(headline) + '</div>' +
        '<div class="rail-date">' + esc(e.date_display) + '</div>' +
        '</a>';
    }).join('');
  }

  /* Default cache mode, same as the search index below: Pages serves both with
     max-age=600, and this one is fetched on every single navigation, so
     'no-cache' bought a conditional round trip per page view to shave at most
     ten minutes off how soon the rail lists a new issue. The page the rail sits
     on is cached the same way, so that wait was never really avoidable. */
  fetch(base + 'archive.json')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      archive = Array.isArray(data) ? data : [];
      latest = archive.length ? archive[0].date : '';
      if (!query) renderArchive();
    })
    .catch(function(err) {
      if (!query) note('載入失敗');
      console.error('archive load failed', err);
    });

  /* ─────────── search ─────────── */
  function tokenize(q) {
    return q.trim().toLowerCase().split(/\s+/).filter(Boolean);
  }
  function buildRe(toks) {
    return new RegExp(toks.map(escRe).join('|'), 'gi');
  }
  function matches(item, toks) {
    var hay = ((item.t || '') + ' ' + (item.b || '') + ' ' + (item.m || '')).toLowerCase();
    for (var i = 0; i < toks.length; i++) {
      if (hay.indexOf(toks[i]) < 0) return false;
    }
    return true;
  }
  /* Escape and <mark> in one pass, so entities can never be matched as text. */
  function markup(text, re) {
    var out = '', last = 0, m;
    re.lastIndex = 0;
    while ((m = re.exec(text)) !== null) {
      out += esc(text.slice(last, m.index)) + '<mark>' + esc(m[0]) + '</mark>';
      last = m.index + m[0].length;
      if (m[0].length === 0) re.lastIndex++;
    }
    return out + esc(text.slice(last));
  }
  function snippet(item, re) {
    var fields = [item.t || '', item.b || '', item.m || ''];
    for (var i = 0; i < fields.length; i++) {
      re.lastIndex = 0;
      var m = re.exec(fields[i]);
      if (!m) continue;
      var text = fields[i];
      var start = Math.max(0, m.index - 24);
      var end = Math.min(text.length, start + 110);
      var slice = (start > 0 ? '…' : '') + text.slice(start, end) + (end < text.length ? '…' : '');
      return markup(slice, re);
    }
    return esc((item.t || '').slice(0, 110));
  }

  function loadIndex() {
    if (!indexPromise) {
      /* Default cache mode, matching archive.json above. indexPromise only
         lives as long as this page and clicking a result is a navigation, so
         'no-cache' meant a conditional request for a megabyte-plus index on
         every hop between briefs, even seconds apart.
         Inside Pages' max-age=600 the browser answers from disk without asking
         — no request, so no ETag either. That is the trade: for up to ten
         minutes after a rebuild a returning reader searches yesterday's index.
         The index is rebuilt once a day; the round trip was paid on every
         search. */
      indexPromise = fetch(base + 'search-index.json')
        .then(function(r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.json();
        })
        .catch(function(err) {
          indexPromise = null;  // let the next keystroke retry
          throw err;
        });
    }
    return indexPromise;
  }

  function setStatus(text) {
    if (!status) return;
    status.textContent = text || '';
    status.hidden = !text;
  }

  function renderSearch(index) {
    var toks = tokenize(query);
    if (!toks.length) { reset(); return; }
    var re = buildRe(toks);
    var days = 0, hits = 0;
    var rows = (index.days || []).map(function(day) {
      var found = (day.items || []).filter(function(it) { return matches(it, toks); });
      if (!found.length) return '';
      days++; hits += found.length;
      var first = found[0];
      return '<a class="rail-item rail-item-hit' + (day.d === active ? ' rail-item-current' : '') +
        '" href="' + hrefFor(day.d) + '?q=' + encodeURIComponent(query) + '">' +
        '<div class="rail-meta"><span>№' + pad3(day.no) + '</span><span>' + found.length + ' 則命中</span></div>' +
        '<div class="rail-headline"><span class="rail-hit-kind">' + esc(KIND_LABEL[first.k] || '') + '</span>' +
        snippet(first, re) + '</div>' +
        '<div class="rail-date">' + esc(day.dd) + '</div>' +
        '</a>';
    }).filter(Boolean).join('');

    var onPage = highlightPage(toks);
    if (!days) {
      note('無符合結果');
      setStatus('找不到「' + query + '」');
      return;
    }
    list.innerHTML = rows;
    setStatus(days + ' 天 · ' + hits + ' 則命中' + (onPage ? ' · 本頁 ' + onPage + ' 處' : ''));
  }

  function reset() {
    query = '';
    setStatus('');
    if (clearBtn) clearBtn.hidden = true;
    clearHighlight();
    renderArchive();
  }

  function run() {
    if (clearBtn) clearBtn.hidden = !query;
    if (!query) { reset(); return; }
    setStatus('搜尋中…');
    loadIndex().then(renderSearch).catch(function(err) {
      note('搜尋索引載入失敗');
      setStatus('');
      console.error('search index load failed', err);
    });
  }

  /* ─────────── in-page highlighting ─────────── */
  function clearHighlight() {
    var main = document.querySelector('main');
    if (!main) return;
    main.querySelectorAll('mark.q-hit').forEach(function(m) {
      m.parentNode.replaceChild(document.createTextNode(m.textContent), m);
    });
    main.normalize();
  }

  function highlightPage(toks) {
    clearHighlight();
    var main = document.querySelector('main');
    if (!main || !toks.length) return 0;
    var re = buildRe(toks);
    var walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT, {
      acceptNode: function(node) {
        var p = node.parentNode;
        if (!p || p.nodeType !== 1) return NodeFilter.FILTER_REJECT;
        var tag = p.tagName;
        if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'MARK') return NodeFilter.FILTER_REJECT;
        return node.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);

    var count = 0;
    nodes.forEach(function(node) {
      var text = node.nodeValue;
      re.lastIndex = 0;
      if (!re.test(text)) return;
      re.lastIndex = 0;
      var frag = document.createDocumentFragment();
      var last = 0, m;
      while ((m = re.exec(text)) !== null) {
        if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
        var mark = document.createElement('mark');
        mark.className = 'q-hit';
        mark.textContent = m[0];
        frag.appendChild(mark);
        last = m.index + m[0].length;
        count++;
        if (m[0].length === 0) re.lastIndex++;
      }
      if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
      node.parentNode.replaceChild(frag, node);
    });
    return count;
  }

  /* Landing from a search result: open whatever <details> hides the first hit. */
  function revealFirstHit() {
    var first = document.querySelector('main mark.q-hit');
    if (!first) return;
    var d = first.closest('details');
    while (d) {
      d.open = true;
      d = d.parentElement ? d.parentElement.closest('details') : null;
    }
    first.classList.add('q-hit-active');
    first.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }

  /* ─────────── wiring ─────────── */
  if (input) {
    var timer = null;
    input.addEventListener('input', function() {
      query = input.value.trim();
      clearTimeout(timer);
      timer = setTimeout(run, 140);
    });
    input.addEventListener('keydown', function(e) {
      if (e.key !== 'Escape') return;
      e.stopPropagation();
      if (input.value) { input.value = ''; reset(); }
      else input.blur();
    });
    document.addEventListener('keydown', function(e) {
      if (e.key !== '/' || e.metaKey || e.ctrlKey || e.altKey) return;
      var el = document.activeElement;
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable)) return;
      e.preventDefault();
      if (document.documentElement.dataset.rail === 'collapsed') {
        delete document.documentElement.dataset.rail;
        try { localStorage.setItem('rail-collapsed', '0'); } catch (err) {}
      }
      if (window.matchMedia('(max-width: 980px)').matches) {
        document.body.classList.add('rail-drawer-open');
      }
      input.focus();
      input.select();
    });
  }
  if (clearBtn) {
    clearBtn.addEventListener('click', function() {
      if (input) { input.value = ''; input.focus(); }
      reset();
    });
  }

  /* Deep link: ?q=… arrives from a clicked search result. */
  var initial = '';
  try {
    initial = new URLSearchParams(window.location.search).get('q') || '';
  } catch (err) {}
  if (initial && input) {
    input.value = initial;
    query = initial.trim();
    if (query) {
      if (clearBtn) clearBtn.hidden = false;
      setStatus('搜尋中…');
      loadIndex()
        .then(function(index) { renderSearch(index); revealFirstHit(); })
        .catch(function(err) {
          note('搜尋索引載入失敗');
          setStatus('');
          console.error('search index load failed', err);
        });
    }
  }
})();
</script>
"""
