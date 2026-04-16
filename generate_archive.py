#!/usr/bin/env python3
"""
generate_archive.py
Generates an editorial-styled archive page listing all past briefs.
"""

import json
from pathlib import Path
from datetime import datetime


def issue_number(date_str: str) -> int:
    try:
        anchor = datetime(2025, 1, 1).date()
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return max(1, (d - anchor).days + 1)
    except Exception:
        return 1


def main():
    archive_path = Path("archive.json")
    if not archive_path.exists():
        print("No archive.json found, skipping.")
        return

    archive = json.loads(archive_path.read_text(encoding="utf-8"))
    total_entries = len(archive)

    rows = ""
    for entry in archive:
        total = entry.get("total", "?")
        if "sources" in entry:
            labels = " · ".join(entry["sources"])
        else:
            labels = " · ".join(s.get("label", "") for s in entry.get("sections", []))
        no = issue_number(entry["date"])
        labels = labels or "—"
        rows += f"""
      <tr>
        <td class="col-issue"><span class="mono">№{no:03d}</span></td>
        <td class="col-date"><a href="briefs/{entry['date']}.html">{entry['date_display']}</a></td>
        <td class="col-count">{total} 篇</td>
        <td class="col-topics">{labels}</td>
        <td class="col-arrow"><a href="briefs/{entry['date']}.html" aria-label="開啟" class="arrow">↗</a></td>
      </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Archive · Product &amp; Design 早報</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,400..700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --paper:    #100d0a;
      --paper-2:  #181410;
      --ink:      #f2ecdf;
      --ink-2:    #cbc1ad;
      --ink-3:    #8a7f6c;
      --rule:     #2a231c;
      --rule-2:   #3a3025;
      --accent:   #ff5722;
      --serif: 'Fraunces', Georgia, serif;
      --sans:  'Inter', system-ui, -apple-system, sans-serif;
      --mono:  'JetBrains Mono', ui-monospace, Menlo, monospace;
      --maxw: 960px;
    }}
    html {{ font-size: 16px; -webkit-font-smoothing: antialiased; }}
    body {{
      font-family: var(--sans);
      background: var(--paper);
      color: var(--ink);
      min-height: 100vh;
      line-height: 1.55;
      position: relative;
      overflow-x: hidden;
    }}
    body::before {{
      content: '';
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 0;
      opacity: .035;
      background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 1 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
      mix-blend-mode: screen;
    }}
    body > * {{ position: relative; z-index: 1; }}
    a {{ color: inherit; text-decoration: none; }}

    header {{
      max-width: var(--maxw);
      margin: 0 auto;
      padding: 2.5rem 1.5rem 1.75rem;
      border-bottom: 1px solid var(--rule);
    }}
    .top-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
      font-family: var(--mono);
      font-size: .72rem;
      letter-spacing: .12em;
      text-transform: uppercase;
      color: var(--ink-3);
    }}
    .back {{
      color: var(--accent);
      transition: gap .15s;
      display: inline-flex; align-items: center; gap: .35rem;
    }}
    .back:hover {{ gap: .6rem; }}
    h1 {{
      font-family: var(--serif);
      font-weight: 400;
      font-size: clamp(2.4rem, 6vw, 3.6rem);
      line-height: 1;
      letter-spacing: -.02em;
      text-align: center;
      font-variation-settings: 'opsz' 144, 'SOFT' 30;
    }}
    h1 em {{
      font-style: italic;
      color: var(--accent);
      font-variation-settings: 'opsz' 144, 'SOFT' 80, 'WONK' 1;
    }}

    main {{
      max-width: var(--maxw);
      margin: 0 auto;
      padding: 2.5rem 1.5rem 5rem;
    }}

    .stats {{
      display: flex;
      gap: 2rem;
      padding: 1rem 0 1.5rem;
      border-bottom: 1px solid var(--rule);
      margin-bottom: 1.5rem;
      font-family: var(--mono);
      font-size: .72rem;
      letter-spacing: .1em;
      text-transform: uppercase;
      color: var(--ink-3);
    }}
    .stat-num {{
      font-family: var(--serif);
      font-weight: 500;
      font-size: 2rem;
      color: var(--ink);
      display: block;
      letter-spacing: -.02em;
      line-height: 1;
      margin-bottom: .25rem;
      font-variation-settings: 'opsz' 96, 'SOFT' 30;
    }}
    .stat-num em {{
      font-style: italic;
      color: var(--accent);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: .9rem;
    }}
    thead th {{
      text-align: left;
      padding: .9rem .75rem;
      font-family: var(--mono);
      font-size: .68rem;
      letter-spacing: .15em;
      text-transform: uppercase;
      color: var(--ink-3);
      border-bottom: 1px solid var(--ink);
      font-weight: 500;
    }}
    tbody tr {{
      transition: background .15s;
    }}
    tbody tr:hover {{ background: var(--paper-2); }}
    tbody td {{
      padding: 1rem .75rem;
      border-bottom: 1px solid var(--rule);
      vertical-align: middle;
    }}
    .col-issue {{ width: 70px; }}
    .col-arrow {{ width: 30px; text-align: right; }}
    .col-count {{ width: 80px; color: var(--ink-2); font-family: var(--mono); font-size: .8rem; }}
    .col-topics {{ color: var(--ink-3); font-size: .82rem; }}
    .mono {{
      font-family: var(--mono);
      font-size: .78rem;
      color: var(--accent);
      letter-spacing: .05em;
    }}
    .col-date a {{
      font-family: var(--serif);
      font-size: 1.05rem;
      color: var(--ink);
      transition: color .15s;
      font-variation-settings: 'opsz' 36, 'SOFT' 30;
    }}
    .col-date a:hover {{
      color: var(--accent);
      font-style: italic;
    }}
    .arrow {{
      color: var(--ink-3);
      font-size: 1rem;
      transition: transform .2s, color .2s;
      display: inline-block;
    }}
    tr:hover .arrow {{
      color: var(--accent);
      transform: translate(2px, -2px);
    }}

    .empty {{
      text-align: center;
      padding: 4rem 0;
      font-family: var(--serif);
      font-style: italic;
      color: var(--ink-3);
      font-size: 1.1rem;
    }}

    footer {{
      max-width: var(--maxw);
      margin: 0 auto;
      padding: 2rem 1.5rem 3rem;
      border-top: 1px solid var(--rule);
      text-align: center;
      font-family: var(--mono);
      font-size: .7rem;
      letter-spacing: .1em;
      text-transform: uppercase;
      color: var(--ink-3);
    }}
  </style>
</head>
<body>
  <header>
    <div class="top-row">
      <a href="index.html" class="back">← Today</a>
      <span>Archive</span>
    </div>
    <h1>歷史<em>存檔</em></h1>
  </header>

  <main>
    <div class="stats">
      <div>
        <span class="stat-num">{total_entries:02d}</span>
        Issues on file
      </div>
      <div>
        <span class="stat-num"><em>Daily</em></span>
        09:00 UTC+8
      </div>
    </div>

    <table>
      <thead>
        <tr>
          <th class="col-issue">№</th>
          <th class="col-date">日期</th>
          <th class="col-count">數量</th>
          <th class="col-topics">主題</th>
          <th class="col-arrow"></th>
        </tr>
      </thead>
      <tbody>{rows if rows else '<tr><td colspan="5" class="empty">尚無存檔。</td></tr>'}</tbody>
    </table>
  </main>

  <footer>
    © Daily Brief · Auto-curated by Claude Haiku 4.5
  </footer>
</body>
</html>"""

    Path("archive.html").write_text(html, encoding="utf-8")
    print(f"OK archive.html generated ({total_entries} entries)")


if __name__ == "__main__":
    main()
