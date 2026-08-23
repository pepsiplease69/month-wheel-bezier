# month-wheel-bezier

A print-and-cut **month wheel** for paper planners: a circular 32-day tracker
where each day sits in its own wedge on a ring, connected by a Bézier
"swagger" curve to a small log box on the page's belt. Built with
[ReportLab](https://www.reportlab.com/dev/opensource/) to render directly to
PDF.

Designed for A5 / half-letter planner inserts (e.g. Traveler's Notebook
style): print, trim or fold along the guide marks, and bind into a notebook.

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

## Usage

The generator script takes a `--paper` layout and a `--landing` mode:

```bash
python month-wheel-bezier_41.py --landing on --paper a5-in-letter
python month-wheel-bezier_41.py --paper letter-2up --two-up between,on
python month-wheel-bezier_41.py --paper a5-fold-in-letter --two-up between,on
```

### `--paper` layouts

| Layout | Description |
| --- | --- |
| `a5-in-letter` | US Letter landscape sheet with an A5 trim box + crop marks. Print at 100%, cut to A5. |
| `half-letter-in-letter` | US Letter landscape sheet with a half-letter (8.5x5.5) trim box + crop marks. |
| `half-letter-in-half-letter` | Half-letter landscape sheet, edge-to-edge — print directly on half-letter stock. |
| `letter-2up` | Two wheels on a US Letter portrait sheet, split by a center **cut** line, producing two half-letter pages. |
| `a5-fold-in-letter` | Two wheels on a US Letter portrait sheet, split by a center **fold** line (both wheels upright), with side crop marks trimming the width to A5 — a double-sided folded insert. |

### Other options

- `--landing on|between` — where connectors meet the ring (ignored for the
  2-up/fold layouts; use `--two-up` instead).
- `--two-up TOP,BOTTOM` — per-wheel landing mode for the 2-up/fold layouts.
- `--radial-sharpness` — how tightly the radial landing blend is confined to
  the 12/6 o'clock days.
- `--output` — output PDF filename.

## Building booklets

`concat.py` concatenates two single-sided PDFs into one (with optional 180°
rotation on either input), for assembling double-sided booklet pages from
individually generated wheel sheets.

## Requirements

- Python 3
- [`reportlab`](https://pypi.org/project/reportlab/)
- [`pypdf`](https://pypi.org/project/pypdf/) (for `concat.py`)

```bash
pip install reportlab pypdf
```

## License

GPL-2.0 — see [LICENSE](LICENSE).
