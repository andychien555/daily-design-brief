#!/usr/bin/env python3
"""
generate_archive.py
Generates a simple archive page listing all past briefs.
"""

import json
from pathlib import Path

def main():
    archive_path = Path("archive.json")
    if not archive_path.exists():
        print("No archive.json found, skipping.")
        return

    archive = json.loads(archive_path.read_text(encoding="utf-8"))

    rows = ""
    for entry in archive:
        total = entry.get("total", "?")
        if "sources" in entry:
            labels = "、".join(entry["sources"])
        else:
            labels = "、".join(s["label"] for s in entry.get("sections", []))
        rows += f"""
      <tr>
        <td><a href="briefs/{entry['date']}.html">{entry['date_display']}</a></td>
        <td>{total} 則</td>
        <td class="topics">{labels}</td>
      </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>歷史存檔 · Product & Design 每日早報</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --ink: #0f0e0d; --paper: #f5f2ec; --accent: #c8460a; --muted: #8a8070; --border: #d8d0c4;
    }}
    body {{ font-family: 'DM Sans', sans-serif; background: var(--paper); color: var(--ink); min-height: 100vh; }}
    header {{ border-bottom: 2px solid var(--ink); padding: 2rem 0 1.25rem; text-align: center; }}
    .back {{ font-size: .78rem; color: var(--accent); text-decoration: none; display: block; margin-bottom: .75rem; }}
    h1 {{ font-family: 'DM Serif Display', serif; font-size: 2rem; }}
    main {{ max-width: 760px; margin: 0 auto; padding: 2.5rem 1.5rem; }}
    table {{ width: 100%; border-collapse: collapse; font-size: .85rem; }}
    th {{ text-align: left; border-bottom: 2px solid var(--ink); padding: .5rem .75rem; font-size: .7rem; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }}
    td {{ padding: .7rem .75rem; border-bottom: 1px solid var(--border); vertical-align: top; }}
    td a {{ color: var(--accent); text-decoration: none; font-weight: 500; }}
    td a:hover {{ text-decoration: underline; }}
    .topics {{ color: var(--muted); font-size: .78rem; }}
  </style>
</head>
<body>
  <header>
    <a href="index.html" class="back">← 今日早報</a>
    <h1>歷史存檔</h1>
  </header>
  <main>
    <table>
      <thead><tr><th>日期</th><th>數量</th><th>主題</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </main>
</body>
</html>"""

    Path("archive.html").write_text(html, encoding="utf-8")
    print(f"✅ archive.html generated ({len(archive)} entries)")

if __name__ == "__main__":
    main()
