# month-wheel-bezier

A print-and-cut **month wheel** for paper planners: a circular 32-day tracker
where each day sits in its own wedge on a ring, connected by a Bézier
"swagger" curve to a small log box on the page's belt. Built with
[ReportLab](https://www.reportlab.com/dev/opensource/) to render directly to
PDF.

Designed for A5 / half-letter planner inserts (e.g. Traveler's Notebook
style): print, trim or fold along the guide marks, and bind into a notebook.
The default output is a full **12-month saddle-stitch booklet** (see
[Booklet mode](#booklet-mode)); single-wheel and 2-up layouts are also
available for one-off sheets.

## How it works

- A set of concentric rings forms the wheel; the outer ring ("Pluto orbit")
  is divided into 32 wedges, one per day, with the day number printed in the
  band between two of the rings.
- A dotted ellipse ("Kuiper belt") surrounds the wheel, with 32 small
  rectangular log boxes arranged around it in two side columns.
- Each day's wedge connects to its log box with a cubic Bézier curve. Near
  the box the curve leaves horizontally (an "S-swagger"); near the wheel it
  blends toward a radial landing for days close to 12/6 o'clock, where a
  horizontal landing would skim the ring tangentially instead of meeting it
  cleanly.
- Connectors can land **on** a day's midpoint (marked with an arrowhead) or
  **between** two days, on the wedge borderline (marked with a dot, and
  optionally a small pigtail loop).
- In booklet mode, each wheel also gets calendar labeling: a **hub label**
  (month name + "(sleep)"/"(walk)"), a ring of **weekday letters** (M T W R
  F S U, i.e. Mon..Sun with R=Thursday and U=Sunday to keep every letter
  distinct) just inside the day numbers, and **blocked/hatched cells** for
  the surplus day slots on months shorter than 32 days (e.g. 29-32 for
  February), so the wheel visually ends where the month does.

## Usage

The generator script takes a `--paper` layout and a `--landing` mode
(default `--paper` is `booklet`, which ignores `--landing` — see
[Booklet mode](#booklet-mode)):

```bash
python month-wheel-bezier.py
python month-wheel-bezier.py --paper booklet --start-weekday sunday
python month-wheel-bezier.py --landing on --paper a5-in-letter
python month-wheel-bezier.py --paper letter-2up --two-up between,on
python month-wheel-bezier.py --paper a5-fold-in-letter --two-up between,on
```

### `--paper` layouts

| Layout | Description |
| --- | --- |
| `booklet` (default) | 12-month A5 saddle-stitch booklet, 7 duplex US Letter sheets. See [Booklet mode](#booklet-mode). |
| `booklet-proof` | Same imposition as `booklet`, but each slot shows a big page number instead of a wheel — fold a blank dummy to check collation before printing the real thing. |
| `a5-in-letter` | US Letter landscape sheet with an A5 trim box + crop marks. Print at 100%, cut to A5. |
| `half-letter-in-letter` | US Letter landscape sheet with a half-letter (8.5x5.5) trim box + crop marks. |
| `half-letter-in-half-letter` | Half-letter landscape sheet, edge-to-edge — print directly on half-letter stock. |
| `letter-2up` | Two wheels on a US Letter portrait sheet, split by a center **cut** line, producing two half-letter pages. |
| `a5-fold-in-letter` | Two wheels on a US Letter portrait sheet, split by a center **fold** line (both wheels upright), with side crop marks trimming the width to A5 — a double-sided folded insert. |

### Other options

- `--landing on|between` — where connectors meet the ring (ignored for the
  2-up/fold/booklet layouts; use `--two-up` for 2-up/fold — booklet mode
  always pairs a `between` "sleep" wheel with an `on` "walk" wheel per month).
- `--two-up TOP,BOTTOM` — per-wheel landing mode for the 2-up/fold layouts.
- `--start-weekday DAY` — weekday of March 1 (booklet layouts only); accepts
  a full name, abbreviation, or single letter (`m t w r f s u`). Every later
  month's weekday rolls forward from it. Default: `sunday`.
- `--radial-sharpness` — how tightly the radial landing blend is confined to
  the 12/6 o'clock days.
- `--output` — output PDF filename. A bare filename is written into the
  `output/` subfolder (created automatically); include a directory to
  override.

## Booklet mode

`--paper booklet` builds a full 12-month (March-February) saddle-stitch
booklet as one 7-sheet, 28-page PDF, imposed for **duplex, short-edge-flip**
printing:

1. Print duplex on US Letter, **short-edge** flip.
2. Trim each sheet's width down to A5 (single cut on the right edge).
3. Fold each sheet once at the horizontal middle (the fold is the spine).
4. Nest the folded sheets inside one another (sheet 1 outermost) and staple
   the spine.

Each month contributes two wheels — a `between`-landing "sleep" wheel and an
`on`-landing "walk" wheel — labeled with the month name, weekday letters, and
hatched-out cells for any days past the month's actual length. Use
`--paper booklet-proof` first to fold a numbered dummy and confirm the page
order before committing real paper.

## Combining individually generated sheets

`concat.py` concatenates two single-sided PDFs into one (with optional 180°
rotation on either input) — useful for hand-assembling double-sided pages
out of separately generated `a5-in-letter` / `half-letter-in-letter` sheets,
as an alternative to the built-in `booklet` layout above.

## Requirements

- Python 3
- [`reportlab`](https://pypi.org/project/reportlab/)
- [`pypdf`](https://pypi.org/project/pypdf/) (for `concat.py`)

```bash
pip install reportlab pypdf
```

## License

GPL-2.0 — see [LICENSE](LICENSE).
