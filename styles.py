"""CSS styles for the daily-design-brief HTML output."""

STYLES = """  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --paper:    #1e1915;
      --paper-2:  #26201a;
      --paper-3:  #2e2721;
      --ink:      #f2ecdf;
      --ink-2:    #cbc1ad;
      --ink-3:    #8a7f6c;
      --rule:     #3a3127;
      --rule-2:   #4a3f32;
      --accent:   #ff5722;
      --accent-2: #f6b94a;
      --sage:     #87a07a;
      --grain-blend: screen;
      --grain-opacity: .03;
      --backdrop: rgba(30, 25, 21, .78);

      --serif: 'Fraunces', 'DM Serif Display', Georgia, serif;
      --sans:  'Inter', system-ui, -apple-system, 'Helvetica Neue', sans-serif;
      --mono:  'JetBrains Mono', ui-monospace, Menlo, monospace;

      --maxw: 1180px;
    }
    [data-theme="light"] {
      --paper:    #faf6ed;
      --paper-2:  #f1ead8;
      --paper-3:  #e7dec7;
      --ink:      #1a1612;
      --ink-2:    #403629;
      --ink-3:    #7a6e58;
      --rule:     #dcd3bd;
      --rule-2:   #c6baa0;
      --accent:   #d14412;
      --accent-2: #a56a1d;
      --grain-blend: multiply;
      --grain-opacity: .04;
      --backdrop: rgba(40, 30, 18, .45);
    }
    html { color-scheme: dark; transition: background-color .2s; }
    html[data-theme="light"] { color-scheme: light; }

    html { font-size: 16px; -webkit-font-smoothing: antialiased; }

    body {
      font-family: var(--sans);
      font-feature-settings: 'ss01', 'cv11';
      background: var(--paper);
      color: var(--ink);
      min-height: 100vh;
      line-height: 1.55;
      position: relative;
      overflow-x: hidden;
    }
    /* Subtle paper grain */
    body::before {
      content: '';
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 0;
      opacity: var(--grain-opacity);
      background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 1 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
      mix-blend-mode: var(--grain-blend);
    }
    body > * { position: relative; z-index: 1; }

    a { color: inherit; text-decoration: none; }

    /* ─────────────── Page shell + Archive rail ─────────────── */
    .page-shell {
      display: grid;
      grid-template-columns: 240px minmax(0, 1fr);
      align-items: start;
    }
    .page-main { min-width: 0; }

    .archive-rail {
      position: sticky;
      top: 0;
      max-height: 100vh;
      overflow-y: auto;
      border-right: 1px solid var(--rule);
      padding: 2.25rem 1.25rem 2rem 1.5rem;
      font-size: .78rem;
    }
    .archive-rail::-webkit-scrollbar { width: 6px; }
    .archive-rail::-webkit-scrollbar-track { background: transparent; }
    .archive-rail::-webkit-scrollbar-thumb { background: var(--rule); border-radius: 3px; }

    .rail-heading {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      font-family: var(--mono);
      font-size: .58rem;
      letter-spacing: .18em;
      text-transform: uppercase;
      color: var(--ink-3);
      margin-bottom: 1.1rem;
    }
    .rail-heading a {
      color: var(--ink-3);
      transition: color .15s;
    }
    .rail-heading a:hover { color: var(--accent); }

    .rail-list { display: flex; flex-direction: column; }
    .rail-loading {
      padding: .5rem 0;
      font-family: var(--mono);
      font-size: .6rem;
      letter-spacing: .1em;
      color: var(--ink-3);
    }

    .rail-item {
      display: block;
      padding: .7rem 0 .8rem;
      border-top: 1px solid var(--rule);
      opacity: .72;
      transition: opacity .15s;
    }
    .rail-item:first-child { border-top: none; padding-top: 0; }
    .rail-item:hover { opacity: 1; }
    .rail-item-current { opacity: 1; }
    .rail-item-current .rail-headline { color: var(--ink); }
    .rail-item-current .rail-meta span:first-child { color: var(--accent); }

    .rail-meta {
      display: flex;
      justify-content: space-between;
      font-family: var(--mono);
      font-size: .58rem;
      letter-spacing: .1em;
      color: var(--ink-3);
      margin-bottom: .35rem;
    }

    .rail-headline {
      font-family: var(--serif);
      font-weight: 400;
      font-size: .82rem;
      line-height: 1.35;
      color: var(--ink-2);
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      font-variation-settings: 'opsz' 18, 'SOFT' 30;
      margin-bottom: .3rem;
    }
    .rail-item:hover .rail-headline { color: var(--ink); }

    .rail-date {
      font-family: var(--mono);
      font-size: .58rem;
      color: var(--ink-3);
      letter-spacing: .06em;
    }

    @media (max-width: 980px) {
      .page-shell { grid-template-columns: 1fr; }
      .archive-rail {
        position: static;
        max-height: none;
        border-right: none;
        border-bottom: 1px solid var(--rule);
        padding: 1.25rem 1.5rem;
      }
    }

    /* ─────────────── Masthead ─────────────── */
    .masthead {
      max-width: var(--maxw);
      margin: 0 auto;
      padding: 2.5rem 1.5rem 1.25rem;
    }
    .masthead-row {
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      gap: 1rem;
    }
    .meta-left, .meta-right {
      font-family: var(--mono);
      font-size: .72rem;
      letter-spacing: .12em;
      text-transform: uppercase;
      color: var(--ink-3);
    }
    .meta-left { text-align: left; }
    .meta-right { text-align: right; }
    .masthead-center { text-align: center; }
    .masthead-title {
      font-family: var(--serif);
      font-weight: 500;
      font-size: clamp(2.4rem, 6.5vw, 4.8rem);
      line-height: 1;
      letter-spacing: -.025em;
      font-variation-settings: 'opsz' 144, 'SOFT' 30;
    }
    .masthead-title em {
      font-style: italic;
      color: var(--accent);
      font-variation-settings: 'opsz' 144, 'SOFT' 80, 'WONK' 1;
      padding-right: .04em;
    }

    /* ─────────────── Body / Layout ─────────────── */
    main {
      max-width: var(--maxw);
      margin: 0 auto;
      padding: 2.5rem 1.5rem 5rem;
    }

    .topbar {
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 2rem;
      font-family: var(--mono);
      font-size: .7rem;
      letter-spacing: .1em;
      text-transform: uppercase;
      color: var(--ink-3);
    }
    .topbar .sep {
      flex: 1;
      height: 1px;
      background: var(--rule);
    }
    .topbar a,
    .topbar .topbar-link {
      color: var(--accent);
      transition: color .15s;
    }
    .topbar a:hover,
    .topbar .topbar-link:hover { color: var(--accent-2); }
    .topbar .topbar-link {
      background: none;
      border: none;
      padding: 0;
      font: inherit;
      letter-spacing: inherit;
      text-transform: inherit;
      cursor: pointer;
    }
    .theme-toggle {
      background: none;
      border: 1px solid var(--rule-2);
      color: var(--ink-3);
      width: 28px;
      height: 28px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      border-radius: 2px;
      font-size: .9rem;
      line-height: 1;
      transition: color .15s, border-color .15s, background .15s;
    }
    .theme-toggle:hover {
      color: var(--accent);
      border-color: var(--accent);
    }

    /* ─────────────── Criteria Modal ─────────────── */
    .criteria-modal {
      padding: 0;
      margin: auto;
      inset: 0;
      border: 1px solid var(--rule-2);
      background: var(--paper-2);
      color: var(--ink-2);
      width: min(640px, calc(100vw - 3rem));
      max-height: calc(100vh - 4rem);
      border-radius: 2px;
      box-shadow: 0 30px 60px -20px rgba(0,0,0,.6);
    }
    .criteria-modal::backdrop {
      background: var(--backdrop);
      backdrop-filter: blur(3px);
    }
    .criteria-modal[open] {
      animation: modal-in .2s ease;
    }
    @keyframes modal-in {
      from { opacity: 0; transform: translateY(8px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .criteria-modal-inner {
      padding: 1.75rem 1.9rem 1.9rem;
      max-height: calc(100vh - 4rem);
      overflow-y: auto;
    }
    .criteria-modal-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      margin-bottom: 1.25rem;
      padding-bottom: .9rem;
      border-bottom: 1px solid var(--rule);
    }
    .criteria-modal-head h3 {
      font-family: var(--mono);
      font-size: .72rem;
      letter-spacing: .15em;
      text-transform: uppercase;
      color: var(--ink);
      font-weight: 500;
    }
    .modal-close {
      background: none;
      border: none;
      color: var(--ink-3);
      font-size: 1rem;
      cursor: pointer;
      padding: 0;
      line-height: 1;
      transition: color .15s;
    }
    .modal-close:hover { color: var(--accent); }
    .criteria-body {
      font-size: .85rem;
      line-height: 1.7;
      color: var(--ink-2);
    }
    .criteria-body p { margin-bottom: .9rem; }
    .criteria-body strong { color: var(--ink); font-weight: 500; }
    .criteria-body ul { padding-left: 1.2rem; margin-bottom: .9rem; }
    .criteria-body li { margin-bottom: .35rem; }
    .criteria-body h4 {
      font-family: var(--serif);
      font-style: italic;
      font-size: 1.05rem;
      margin: 1.4rem 0 .5rem;
      color: var(--ink);
      font-weight: 500;
    }
    .criteria-body table {
      width: 100%;
      border-collapse: collapse;
      font-size: .8rem;
      margin-bottom: .75rem;
    }
    .criteria-body th, .criteria-body td {
      text-align: left;
      padding: .5rem .65rem;
      border-bottom: 1px solid var(--rule);
      vertical-align: top;
    }
    .criteria-body th {
      color: var(--ink-3);
      font-weight: 500;
      font-size: .68rem;
      letter-spacing: .12em;
      text-transform: uppercase;
      font-family: var(--mono);
    }
    .criteria-body code {
      background: rgba(255, 87, 34, 0.1);
      color: var(--accent);
      padding: 1px 7px;
      border-radius: 2px;
      font-family: var(--mono);
      font-size: .76rem;
    }
    .criteria-note {
      font-size: .76rem;
      color: var(--ink-3);
      margin-top: 1rem;
      padding-top: .75rem;
      border-top: 1px dashed var(--rule);
      font-style: italic;
    }

    /* ─────────────── Lead / Hero Card ─────────────── */
    .lead {
      margin-bottom: 3rem;
      border-top: 2px solid var(--ink);
      border-bottom: 1px solid var(--rule);
      padding: 2rem 0 2.25rem;
      position: relative;
    }
    .lead::before {
      content: '';
      position: absolute;
      top: -2px; left: 0;
      width: 80px; height: 4px;
      background: var(--accent);
    }
    .lead-anchor {
      display: block;
      cursor: pointer;
      transition: opacity .15s;
    }
    .lead-anchor:hover { opacity: .92; }
    .lead-anchor:hover .lead-arrow { transform: translate(3px, -3px); color: var(--accent); }

    .lead-meta {
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 1.25rem;
      font-family: var(--mono);
      font-size: .72rem;
      letter-spacing: .12em;
      text-transform: uppercase;
      color: var(--ink-3);
    }
    .lead-rank {
      color: var(--accent);
      font-weight: 500;
    }
    .lead-rule {
      flex: 1;
      height: 1px;
      background: var(--rule);
    }
    .lead-author {
      display: flex;
      gap: .5rem;
      align-items: baseline;
      text-transform: none;
      letter-spacing: 0;
      font-family: var(--sans);
      font-size: .82rem;
    }
    .lead-author .author-name { color: var(--ink); font-weight: 500; }
    .lead-author .author-handle { color: var(--ink-3); }

    .lead-summary {
      font-family: var(--serif);
      font-weight: 400;
      font-size: clamp(1.7rem, 3.4vw, 2.6rem);
      line-height: 1.18;
      letter-spacing: -.01em;
      color: var(--ink);
      margin-bottom: 1rem;
      font-variation-settings: 'opsz' 96, 'SOFT' 30;
    }
    .lead-text {
      font-size: 1rem;
      line-height: 1.7;
      color: var(--ink-2);
      max-width: 70ch;
      margin-bottom: 1.5rem;
      display: -webkit-box;
      -webkit-line-clamp: 4;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .lead-foot {
      display: flex;
      align-items: center;
      gap: 1.25rem;
      font-size: .8rem;
      color: var(--ink-3);
      flex-wrap: wrap;
    }
    .lead-arrow {
      margin-left: auto;
      font-size: 1.2rem;
      color: var(--ink-3);
      transition: transform .2s ease, color .2s;
      display: inline-block;
    }

    /* ─────────────── Section divider ─────────────── */
    .grid-divider {
      display: flex;
      align-items: center;
      gap: 1rem;
      margin: 0 0 1.5rem;
      font-family: var(--mono);
      font-size: .7rem;
      letter-spacing: .15em;
      text-transform: uppercase;
      color: var(--ink-3);
    }
    .grid-divider::before,
    .grid-divider::after {
      content: '';
      flex: 1;
      height: 1px;
      background: var(--rule);
    }

    /* ─────────────── Cards Grid ─────────────── */
    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 0;
      border-top: 1px solid var(--rule);
      border-left: 1px solid var(--rule);
    }

    .card {
      border-right: 1px solid var(--rule);
      border-bottom: 1px solid var(--rule);
      background: transparent;
      transition: background .15s;
    }
    .card:hover { background: var(--paper-2); }
    .card-anchor {
      display: flex;
      flex-direction: column;
      gap: .65rem;
      padding: 1.25rem 1.4rem 1.4rem;
      height: 100%;
      cursor: pointer;
      position: relative;
    }
    .card-anchor::after {
      content: '↗';
      position: absolute;
      top: 1.1rem;
      right: 1.2rem;
      color: var(--ink-3);
      font-size: .95rem;
      transition: transform .2s, color .2s;
    }
    .card:hover .card-anchor::after {
      transform: translate(2px, -2px);
      color: var(--accent);
    }

    .card-rank {
      font-family: var(--mono);
      font-size: .68rem;
      letter-spacing: .15em;
      color: var(--accent);
      margin-bottom: .15rem;
    }
    .card-meta {
      display: flex;
      flex-direction: column;
      gap: .1rem;
      margin-bottom: .25rem;
    }
    .author-name {
      font-size: .85rem;
      font-weight: 500;
      color: var(--ink);
    }
    .author-handle {
      font-size: .72rem;
      color: var(--ink-3);
      font-family: var(--mono);
    }

    .card-summary {
      font-family: var(--serif);
      font-weight: 400;
      font-size: 1.1rem;
      line-height: 1.35;
      color: var(--ink);
      letter-spacing: -.005em;
      font-variation-settings: 'opsz' 36, 'SOFT' 30;
    }

    .card-text {
      font-size: .82rem;
      line-height: 1.65;
      color: var(--ink-2);
      flex: 1;
      display: -webkit-box;
      -webkit-line-clamp: 4;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .card-foot {
      display: flex;
      gap: 1rem;
      align-items: center;
      font-size: .72rem;
      color: var(--ink-3);
      padding-top: .65rem;
      border-top: 1px dashed var(--rule);
      flex-wrap: wrap;
    }

    .stat {
      display: inline-flex;
      align-items: center;
      gap: .3rem;
      font-family: var(--mono);
    }
    .glyph {
      color: var(--accent);
      font-size: .8rem;
    }
    .chip {
      margin-left: auto;
      font-family: var(--mono);
      font-size: .65rem;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--ink-2);
      background: rgba(255, 87, 34, 0.08);
      border: 1px solid rgba(255, 87, 34, 0.18);
      padding: 2px 8px;
      border-radius: 999px;
    }

    /* ─────────────── Product Hunt Section ─────────────── */
    .ph-divider {
      margin-top: 3rem;
    }
    .ph-divider span {
      color: var(--accent);
    }
    .ph-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 0;
      border-top: 1px solid var(--rule);
      border-left: 1px solid var(--rule);
      margin-bottom: 3rem;
    }
    .ph-card {
      border-right: 1px solid var(--rule);
      border-bottom: 1px solid var(--rule);
      transition: background .15s;
    }
    .ph-card:hover { background: var(--paper-2); }
    .ph-anchor {
      display: flex;
      flex-direction: column;
      gap: .55rem;
      padding: 1.25rem 1.4rem 1.4rem;
      height: 100%;
      cursor: pointer;
      position: relative;
    }
    .ph-rank {
      font-family: var(--mono);
      font-size: .68rem;
      letter-spacing: .15em;
      color: var(--accent);
      text-transform: uppercase;
    }
    .ph-title {
      font-family: var(--serif);
      font-weight: 500;
      font-size: 1.35rem;
      line-height: 1.2;
      letter-spacing: -.01em;
      color: var(--ink);
      font-variation-settings: 'opsz' 72, 'SOFT' 30;
    }
    .ph-tagline {
      font-family: var(--sans);
      font-size: .82rem;
      line-height: 1.55;
      color: var(--ink-2);
      font-style: italic;
    }
    .ph-summary {
      font-size: .88rem;
      line-height: 1.65;
      color: var(--ink);
      flex: 1;
    }
    .ph-foot {
      display: flex;
      gap: .75rem;
      align-items: center;
      font-size: .7rem;
      color: var(--ink-3);
      padding-top: .65rem;
      border-top: 1px dashed var(--rule);
      flex-wrap: wrap;
    }
    .ph-author {
      font-family: var(--mono);
      letter-spacing: .04em;
    }
    .chip-ph {
      margin-left: 0;
      background: rgba(246, 185, 74, 0.1);
      border-color: rgba(246, 185, 74, 0.25);
      color: var(--accent-2);
    }
    .ph-arrow {
      margin-left: auto;
      font-size: 1rem;
      color: var(--ink-3);
      transition: transform .2s, color .2s;
    }
    .ph-card:hover .ph-arrow {
      transform: translate(2px, -2px);
      color: var(--accent);
    }

    /* ─────────────── Empty state ─────────────── */
    .empty {
      text-align: center;
      padding: 5rem 1rem 4rem;
      border-top: 2px solid var(--ink);
      border-bottom: 1px solid var(--rule);
      position: relative;
    }
    .empty::before {
      content: '';
      position: absolute;
      top: -2px; left: 50%;
      transform: translateX(-50%);
      width: 80px; height: 4px;
      background: var(--accent);
    }
    .empty-mark {
      font-family: var(--serif);
      font-style: italic;
      font-size: 4rem;
      color: var(--accent);
      line-height: 1;
      margin-bottom: 1rem;
      font-variation-settings: 'opsz' 144, 'SOFT' 100, 'WONK' 1;
    }
    .empty-title {
      font-family: var(--serif);
      font-weight: 400;
      font-size: clamp(2rem, 5vw, 3.4rem);
      line-height: 1.1;
      color: var(--ink);
      margin-bottom: 1rem;
      font-variation-settings: 'opsz' 144, 'SOFT' 30;
    }
    .empty-title em {
      font-style: italic;
      color: var(--accent);
      font-variation-settings: 'opsz' 144, 'SOFT' 100, 'WONK' 1;
    }
    .empty-sub {
      color: var(--ink-2);
      font-size: .92rem;
      line-height: 1.7;
      max-width: 480px;
      margin: 0 auto 1.75rem;
    }
    .empty-rule {
      width: 30px;
      height: 1px;
      background: var(--rule-2);
      margin: 0 auto 1rem;
    }
    .empty-foot {
      font-family: var(--serif);
      font-style: italic;
      color: var(--ink-3);
      font-size: .9rem;
    }

    /* ─────────────── Footer ─────────────── */
    footer {
      max-width: var(--maxw);
      margin: 0 auto;
      padding: 3rem 1.5rem 4rem;
      border-top: 1px solid var(--rule);
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      gap: 1.5rem;
      align-items: end;
      font-size: .74rem;
      color: var(--ink-3);
    }
    .colophon-left { text-align: left; }
    .colophon-center {
      text-align: center;
      font-family: var(--serif);
      font-style: italic;
      color: var(--ink-2);
      font-size: .9rem;
    }
    .colophon-center em {
      color: var(--accent);
      font-style: italic;
    }
    .colophon-right {
      text-align: right;
      font-family: var(--mono);
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .colophon-right a { color: var(--ink-2); border-bottom: 1px solid var(--rule-2); }
    .colophon-right a:hover { color: var(--accent); border-color: var(--accent); }

    /* ─────────────── Responsive ─────────────── */
    @media (max-width: 720px) {
      .masthead-row {
        grid-template-columns: 1fr;
        text-align: center;
      }
      .meta-left, .meta-right { text-align: center; }
      .lead-meta { flex-wrap: wrap; gap: .5rem; }
      .lead-author { width: 100%; }
      .cards-grid { grid-template-columns: 1fr; }
      footer {
        grid-template-columns: 1fr;
        text-align: center;
      }
      .colophon-left, .colophon-right { text-align: center; }
    }

    /* ── Tweet context: quoted / replied-to / top replies ── */
    .ctx-quote {
      margin: .65rem 0;
      padding: .55rem .75rem;
      border-left: 2px solid var(--accent);
      background: rgba(232, 90, 26, 0.06);
      font-size: .78rem;
      line-height: 1.55;
      color: var(--ink);
    }
    .ctx-quote.ctx-reply {
      border-left-color: var(--muted);
      background: rgba(138, 128, 112, 0.08);
    }
    .ctx-label {
      display: block;
      font-size: .66rem;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: .25rem;
    }
    .ctx-quote p { margin: 0; }

    .ctx-replies {
      margin-top: .5rem;
      font-size: .75rem;
    }
    .ctx-replies > summary {
      cursor: pointer;
      list-style: none;
      color: var(--muted);
      padding: .3rem 0;
      user-select: none;
    }
    .ctx-replies > summary::-webkit-details-marker { display: none; }
    .ctx-replies > summary::before {
      content: '▸';
      display: inline-block;
      margin-right: .35rem;
      color: var(--accent);
      transition: transform .15s;
    }
    .ctx-replies[open] > summary::before { transform: rotate(90deg); }
    .ctx-replies ul {
      list-style: none;
      padding: 0;
      margin: .35rem 0 0;
      display: flex;
      flex-direction: column;
      gap: .5rem;
    }
    .ctx-replies li {
      padding: .45rem .6rem;
      background: rgba(138, 128, 112, 0.06);
      border-radius: 3px;
    }
    .ctx-rep-author {
      color: var(--ink);
      font-weight: 500;
      margin-right: .5rem;
    }
    .ctx-rep-likes {
      color: var(--muted);
      font-size: .7rem;
    }
    .ctx-replies li p {
      margin: .25rem 0 0;
      color: var(--ink);
      line-height: 1.5;
    }
  </style>
"""
