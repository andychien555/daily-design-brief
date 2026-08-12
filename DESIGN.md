# DESIGN.md — 晨刊 MATINS

The implemented visual system. Authority for *why* lives in
`品牌視覺發想/確定視覺/brand-definition.md` (brand) and `brand-art-direction.md`
(art direction); this file records how those decisions are encoded in the code, and
the constraints that will bite anyone changing them.

Surface mode: **Read**. One reader, ~08:00, 5–10 minutes, light room. Structure for
comprehension first, then make the reading worth staying in.

## The five rules

1. **Light is canon.** `:root` is the light palette; `[data-theme="dark"]` is a
   derivative. An unset `data-theme` means light — `scripts.py` depends on this in
   two places (`toggleTheme`, the icon sync).
2. **Square corners. Nothing floats, glows, or casts a shadow.** No `border-radius`,
   no `box-shadow`, no `backdrop-filter` anywhere. Buttons are compact rectangles.
3. **明體 carries the whole interface.** `--serif` is the only reading face;
   `--mono` is kept for the machine layer (№, dates, timestamps) because that is a
   data notation, and Ming has no tabular figures. No italics. This deliberately
   replaces the art direction's "a single neutral grotesque carries the entire
   system", at the brand owner's direction — the AD's masthead-only exception for
   明體 no longer applies because there is nothing to except it from.
4. **Ochre is rationed.** `--dawn` appears exactly twice: the masthead issue number
   and the archive rail's current-day marker. Red and green are reserved for market
   data and must never become interface colour.
5. **Broadsheet.** Full-bleed engraving, ink nameplate plate, one enormous lead, a
   two-column desk. Nothing inside `.cards-grid` may span both tracks. The column
   rule is `.cards-grid::before`, absolutely positioned at `left: 50%` — hanging it
   off the odd cell's `border-right` dictated that cell's right padding, so a cell
   could never hold the same inset on both sides. The 5.5rem gutter between the two
   measures is paid `--card-pad` by each cell and the rest by `column-gap`.
   Collapses to one column at 900px.

## Tokens

| Token | Light | Dark | Role |
|---|---|---|---|
| `--paper` | `#faf6ed` | `#14181e` | ground |
| `--paper-2` | `#f2ebda` | `#1b2028` | recessed panel, hover |
| `--paper-3` | `#e8dfc9` | `#232a34` | deepest fill, broken-image panel |
| `--ink` | `#1a1612` | `#ede7da` | body, masthead |
| `--ink-2` / `--ink-3` | `#423a2e` / `#7a6e58` | `#c4bcab` / `#8a8172` | secondary / meta |
| `--rule` / `--rule-2` | `#dcd3bd` / `#c6baa0` | `#2a323c` / `#3a4450` | hairlines / borders |
| `--accent` | `#2f4a63` | `#8fa9c2` | links, emphasis, kickers |
| `--dawn` | `#c08a3e` | `#d9a85c` | **rationed** — see rule 4 |

Type: `--serif` Noto Serif TC 400/700 everywhere · `--mono` JetBrains Mono for the
machine layer. Layout: `--maxw: 1180px`, `--measure: 70ch` on full-width prose; inside
the two-column desk the track width does the constraining instead.

**The engraving is generated at its full 1672px** so a 1180px frame downscales it
rather than enlarging it out of its own dither grid. It is the only asset allowed
past the 150 KB budget (187 KB), because it is the hero of all 115 pages.

## Dither as material

The brand promotes ordered dither from treatment to material, so it is *computed*,
not drawn. `tools/prepare_assets.py` owns all of it:

- **破曉方塊 (Dawn Ramp)** — 32×32 grid, 8 bands, Bayer 4×4 thresholds on one shared
  lattice. Coverage per band comes from the enumeration in brand-definition.md
  §"1 — The mark"; its geometry spec states the rule as `(9-n)/8`, which contradicts
  the "band 8 empty" it also demands, so the enumerated list wins. Emitted as
  `favicon.svg` and as `MARK_URI`, a CSS **mask** so `.empty-mark` and
  `.endmark-glyph` inherit `currentColor` in both themes from one source.
- **Paper texture** — Bayer 8×8 at 50% coverage, masked over `--ink` at
  `--grain-opacity`. Masked rather than blended because a black tile with
  `mix-blend-mode: screen` is a no-op against a dark ground.
- **Artwork** — cropped, NEAREST-downscaled by an integer factor, median-cut to
  12–16 colours. Lossy encoding is
  not an option: an ordered dither is maximum-entropy to a DCT, so WebP q88 came out
  *larger* than lossless while smearing the grid. Budget: 150 KB per asset, enforced
  in the script.

Regenerate with `python3 tools/prepare_assets.py`. It rewrites `favicon.svg` and
`dither_assets.py`, which `styles.py` imports — so the favicon and the in-page mark
can never drift apart.

## Two constraints that break silently

**1. Card class names are a data contract.** `build_search_index.py` parses rendered
HTML by class: `nl-item / lead / card / ph-card / yt-brief` decide the block kind,
and twelve `FIELD_CLASSES` decide what text is searchable. Renaming any of them
empties or mis-buckets the index with no error. Restyle freely; do not rename.
Regression check: `search-index.json` per-kind counts must be unchanged.

**2. Anything shared across issues must go through `refresh_briefs_shell.py`.**
Historical briefs are written once and never regenerated. Head, masthead, CSS,
archive rail, both scripts, the end mark, the colophon, and the empty state are all
rebuilt inside every archived page from `generate_html.py`'s block functions. Add a
new shared element → add its anchor there, or 115 issues drift.

## Furniture

- **Masthead** — broadsheet nameplate, never redesigned per issue: full-bleed
  engraving → solid ink plate with reversed 晨刊 / MATINS / № / date → ears → 2px
  ink rule. Reversed type sits on a printed block rather than on the painting: the
  engraving's sky is bone white, and a scrim would mean a gradient.
  `masthead_block(..., meta=False)` drops the issue line for non-issue pages (404).
- **Ears** — the front page's own contents line, derived by `issue_stats()` from the
  *rendered* `<main>` rather than from data.json, so a refreshed archive page and a
  freshly generated one cannot report different numbers.
- **Lead** — the main course hoisted out of the flow: kicker, one enormous headline
  taken from the brief's 「一句話總結」 (episode titles like 「EP686 | 🕸️」 cannot
  carry it), then the brief already open, body in two columns. Finance first; an
  article only when there is no podcast; nothing when the day has neither.
  `strip_one_liner()` removes that heading and *only the sentence under it* — an
  article's whole bullet list lives in the same section, and skipping to the next
  `##` silently deleted most of the brief. The card's own kicker and disclosure
  triangle are hidden here (the kicker repeats `.bs-kicker`; the triangle only
  indented the card away from the headline), and its standfirst goes as soon as the
  lead is open, because the body's first paragraph *is* the standfirst.
  Under 700 characters `lead_story()` adds `bs-lead-compact` and the body drops to
  one track — two columns of a brief that short get sliced mid-word.
- **Desk** — 好文 and 推文 in one two-column grid. The tweet lead (`№ 01 · 頭條`)
  sits above it at full width, deliberately outside the grid. A card's hover ground
  is the cell itself, so it lands on rules that are already on the page: the grid's
  top rule, the card's bottom rule, the column rule. The text carries `--card-pad`
  of inset instead, and the tweet deck carries the same one, so everything below
  the divider reads off a single left edge (the rules stay on the outer grid, the
  text sits `--card-pad` inside it). Bleeding the ground *past* the cell to keep the
  text on the outer grid was tried and is worse: the tone then agrees with no rule
  on the page and reads as a highlight that slipped sideways.
- **End mark** — the 破曉方塊 at 13px plus 「本期完」 after `</main>`. The promise
  under the masthead is 「讀得完」; this is that promise as a glyph.
- **Empty state** — mark, one flat sentence, the next publish time. No apology, no
  explanation of the crawler, no substitute content. Padding a thin day would breach
  the promise, so the honest empty state is part of keeping it.
- **404** — spot-scale waterfall, one sentence, one way back.

## Off-brand by definition

Infinite scroll, "load more", related content, next-issue autoplay, push, streak
counters. These are not ugly — they contradict the sentence under the masthead.
