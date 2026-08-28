#!/usr/bin/env python3
"""Landscape A5 month-wheel habit tracker.

Two facing A5 pages = one month. This wheel drives the sleep tracker: each
night's Bezier connector runs from the wheel out to a belt rectangle.

Connector LANDING on the Pluto orbit is switchable via --landing:
  * on      -> land at each sector's MIDPOINT (aligned with the day number)
  * between -> land at the BORDERLINE between two dates (sector edge)

Connector styles:
  * side lanes      -> horizontal S-swagger (k_frac=1.25)
  * partial radial  -> near-vertical days swing to a radial landing
  * pigtail loops   -> selected 'between' days curl at the landing (LOOP_CURLS)

Calendar labeling (booklet only; single/2-up wheels stay blank):
  * hub label       -> the month name + (sleep)/(walk) in the center hub.
                       'sleep' is the 'between' wheel, 'walk' is the 'on' wheel.
  * weekday letters -> the ring just inside the day numbers, using
                       M T W R F S U (Mon..Sun; note R=Thu, U=Sun).
  * blocked days    -> for months shorter than 32 days, the surplus day-number
                       cells (e.g. 32 for a 31-day month, 31-32 for a 30-day
                       month, 29-32 for Feb) are cross-hatched and lose their
                       number + weekday letter. This anchors the month's end.
  * --start-weekday -> the weekday of MARCH 1 (default sunday). Every later
                       month's start rolls forward from it (31 days of March ->
                       April starts Wednesday, etc.). Leap Feb is ignored.

Paper (--paper):
  * a5-in-letter          -> US Letter LANDSCAPE with an A5 (8.27x5.83) TRIM
                             box + crop marks. Print at 100%, cut to A5.
  * half-letter-in-letter -> US Letter LANDSCAPE with a HALF-LETTER (8.5x5.5)
                             TRIM box + crop marks. Cut to half-letter.
  * half-letter-in-half-letter -> HALF-LETTER (8.5x5.5) LANDSCAPE sheet,
                             edge-to-edge. Print directly on half-letter stock.
  * letter-2up            -> TWO wheels on a US Letter PORTRAIT sheet (8.5x11),
                             split by a center CUT line. Two separate
                             half-letter pages. Landings via --two-up.
  * a5-fold-in-letter     -> TWO wheels on a US Letter PORTRAIT sheet, split by
                             a center FOLD line (not a cut). Both wheels are
                             upright (no rotation). Side crop marks trim the
                             width down to A5 (8.27). The result is an "A5-ish"
                             double-sided folded card (folded height 5.5in is a
                             touch under A5's 5.83in) for a traveler's-notebook-
                             style insert: fold, trim sides, tuck into an A5
                             notebook, band the spine. Landings via --two-up.

Usage:
  python month-wheel-bezier_45.py --landing on --paper a5-in-letter
  python month-wheel-bezier_45.py --paper letter-2up --two-up between,on
  python month-wheel-bezier_45.py --paper booklet --start-weekday sunday
"""

import argparse
import math
import os

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5, letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import Color

# Half US Letter ("statement" / Junior size) = 5.5 x 8.5 in. This is a common
# US planner/binder size that is loosely (but not exactly) "A5". Reportlab has
# no built-in constant, so define it in portrait; landscape() flips it to
# 8.5 x 5.5.
HALF_LETTER = (5.5 * inch, 8.5 * inch)

# Default 2-up / fold wheel landings, TOP first then BOTTOM. Overridable at the
# command line with --two-up (e.g. "on,on", "between,between", "on,between").
TWO_UP_LANDINGS = ("between", "on")

# Weekday letters for the ring just inside the day numbers, indexed Mon..Sun.
# Note the user's convention: R = Thursday (T is Tuesday), U = Sunday (S is
# Saturday). This keeps every letter unique.
WEEKDAY_LETTERS = ["M", "T", "W", "R", "F", "S", "U"]   # 0=Mon .. 6=Sun

# Short abbreviations (0=Mon..6=Sun) used to tag booklet PDF filenames with the
# starting weekday of MARCH 1, e.g. "...-start-sun.pdf" for a Sunday year.
WEEKDAY_ABBR = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Accepted spellings for --start-weekday (the weekday of MARCH 1). Full names,
# common abbreviations, and the single letters above all map to a 0..6 index.
_WEEKDAY_PARSE = {
    "monday": 0, "mon": 0, "m": 0,
    "tuesday": 1, "tue": 1, "tues": 1, "t": 1,
    "wednesday": 2, "wed": 2, "w": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3, "r": 3,
    "friday": 4, "fri": 4, "f": 4,
    "saturday": 5, "sat": 5, "s": 5,
    "sunday": 6, "sun": 6, "u": 6,
}


def draw_dotted_ellipse(c, cx, cy, major_in=4.0, minor_in=3.5):
    """Subtle dotted ellipse (Kuiper belt) centered at (cx, cy)."""
    a = (major_in / 2.0) * inch
    b = (minor_in / 2.0) * inch
    c.saveState()
    c.setStrokeColor(Color(0.45, 0.45, 0.45))
    c.setLineWidth(0.6)
    c.setDash(1, 3)
    c.ellipse(cx - a, cy - b, cx + a, cy + b, stroke=1, fill=0)
    c.restoreState()


def draw_trim_border(c, cx, cy, trim_w, trim_h, crop_marks=True,
                     mark_len=0.25 * inch, mark_gap=0.06 * inch):
    """Draw a TRIM rectangle (+ corner crop marks) centered at (cx, cy).

    The rectangle is exactly the finished page size (A5 or half-letter), so
    after printing at 100% on the larger letter sheet you can cut along it to
    recover that page. The little corner ticks sit OUTSIDE the box (they get
    trimmed away) so they don't mark the finished page.
    """
    x0, y0 = cx - trim_w / 2.0, cy - trim_h / 2.0
    x1, y1 = cx + trim_w / 2.0, cy + trim_h / 2.0

    # The trim line itself: faint dashed rectangle.
    c.saveState()
    c.setStrokeColor(Color(0.55, 0.55, 0.55))
    c.setLineWidth(0.5)
    c.setDash(2, 2)
    c.rect(x0, y0, trim_w, trim_h, stroke=1, fill=0)
    c.restoreState()

    if not crop_marks:
        return

    # Corner crop marks: two short solid ticks pointing outward per corner.
    c.saveState()
    c.setStrokeColor(Color(0.0, 0.0, 0.0))
    c.setLineWidth(0.6)
    c.setDash()  # solid
    corners = [
        (x0, y0, -1, -1),   # bottom-left
        (x1, y0, +1, -1),   # bottom-right
        (x0, y1, -1, +1),   # top-left
        (x1, y1, +1, +1),   # top-right
    ]
    for mx, my, hx, vy in corners:
        # horizontal tick extending outward
        c.line(mx + hx * mark_gap, my,
               mx + hx * (mark_gap + mark_len), my)
        # vertical tick extending outward
        c.line(mx, my + vy * mark_gap,
               mx, my + vy * (mark_gap + mark_len))
    c.restoreState()


def draw_cut_line(c, x0, x1, y, tick_len=0.16 * inch):
    """Horizontal dashed CUT line from x0..x1 at height y (for 2-up sheets).

    Small solid ticks at each end nudge just past the page edge to signal
    "cut here". Use on letter-2up to separate the two half-letter pages.
    """
    c.saveState()
    c.setStrokeColor(Color(0.5, 0.5, 0.5))
    c.setLineWidth(0.6)
    c.setDash(4, 3)
    c.line(x0, y, x1, y)
    c.restoreState()

    # End ticks (solid) as a visual "cut here" cue.
    c.saveState()
    c.setStrokeColor(Color(0.0, 0.0, 0.0))
    c.setLineWidth(0.7)
    c.setDash()
    c.line(x0, y, x0 + tick_len, y)
    c.line(x1 - tick_len, y, x1, y)
    c.restoreState()


def draw_fold_line(c, x0, x1, y, label="FOLD", tick_len=0.16 * inch,
                   font_size=6.5):
    """Horizontal FOLD line from x0..x1 at height y (for the fold booklet).

    Distinct from a cut line: dot-dash "valley fold" styling, end ticks, and
    a small centered 'FOLD' label so you don't cut it by mistake.
    """
    c.saveState()
    c.setStrokeColor(Color(0.55, 0.55, 0.55))
    c.setLineWidth(0.6)
    c.setDash([6, 2, 1, 2])   # dot-dash = classic fold-line convention
    c.line(x0, y, x1, y)
    c.restoreState()

    # End ticks (solid).
    c.saveState()
    c.setStrokeColor(Color(0.0, 0.0, 0.0))
    c.setLineWidth(0.7)
    c.setDash()
    c.line(x0, y, x0 + tick_len, y)
    c.line(x1 - tick_len, y, x1, y)
    c.restoreState()

    # Centered label sitting just above the line, on a small white gap.
    c.saveState()
    cx = (x0 + x1) / 2.0
    c.setFont("Helvetica", font_size)
    tw = c.stringWidth(label, "Helvetica", font_size)
    pad = 3
    c.setFillColor(Color(1, 1, 1))
    c.rect(cx - tw / 2.0 - pad, y - 1.5, tw + 2 * pad, font_size + 2,
           stroke=0, fill=1)
    c.setFillColor(Color(0.35, 0.35, 0.35))
    c.drawCentredString(cx, y + 2.0, label)
    c.restoreState()


def draw_side_crop_marks(c, x, y0, y1, mark_len=0.22 * inch,
                         mark_gap=0.06 * inch):
    """Vertical crop ticks at a trim-x, pointing outward at top & bottom edges.

    Used by the fold booklet to mark where to trim the WIDTH down to A5. y0/y1
    are the page bottom/top; ticks sit just beyond them so they get cut away.
    """
    c.saveState()
    c.setStrokeColor(Color(0.0, 0.0, 0.0))
    c.setLineWidth(0.6)
    c.setDash()
    # bottom tick pointing down, top tick pointing up
    c.line(x, y0 - mark_gap, x, y0 - mark_gap - mark_len)
    c.line(x, y1 + mark_gap, x, y1 + mark_gap + mark_len)
    c.restoreState()

    # Faint dashed trim guide spanning the sheet at this x.
    c.saveState()
    c.setStrokeColor(Color(0.6, 0.6, 0.6))
    c.setLineWidth(0.4)
    c.setDash(2, 3)
    c.line(x, y0, x, y1)
    c.restoreState()


def draw_subsector_lines(c, cx, cy, inner_d=1.0, outer_d=2.5, n_divisions=32):
    """Radial spokes dividing the rings into n_divisions (clockwise from 12)."""
    r_inner = (inner_d / 2.0) * inch
    r_outer = (outer_d / 2.0) * inch
    step = 2.0 * math.pi / n_divisions
    c.saveState()
    c.setLineWidth(0.75)
    for i in range(n_divisions):
        theta = i * step
        dx, dy = math.sin(theta), math.cos(theta)
        c.line(cx + dx * r_inner, cy + dy * r_inner,
               cx + dx * r_outer, cy + dy * r_outer)
    c.restoreState()


def belt_rectangle_layout(cx, cy, major_in=4.0, minor_in=3.5,
                          rect_w_in=1.25, rect_h_in=0.25, gap_in=0.25, n=32):
    """Return placement data for the n belt rectangles (two side columns)."""
    a = (major_in / 2.0) * inch
    b = (minor_in / 2.0) * inch
    w = (rect_w_in / 2.0) * inch
    h = (rect_h_in / 2.0) * inch
    gap = gap_in * inch

    A = a + gap + w
    B = b + gap + h
    min_off = w + 0.075 * inch

    # Box staggers DISABLED. These nudges existed ONLY to give the old crossing
    # S-curves room at 12/3/6/9 o'clock. With cross-wiring removed (ORBIT_SWAP
    # empty), the boxes sit evenly and each wires straight to its own slot.
    # (To restore, set Y_OFFSET = {0: 0.25*inch, 16: -0.25*inch} and
    #  X_OFFSET = {7: 0.25*inch, 8: -0.25*inch, 23: 0.25*inch, 24: -0.25*inch}.)
    Y_OFFSET = {}
    X_OFFSET = {}

    per_side = n // 2
    items = []
    for j in range(per_side):
        Y = B - j * (2.0 * B / (per_side - 1))
        ratio = max(0.0, 1.0 - (Y / B) ** 2)
        X = max(A * math.sqrt(ratio), min_off)
        for sx in (1, -1):
            idx = j if sx == 1 else (n - 1 - j)
            ry = cy + Y + Y_OFFSET.get(idx, 0.0)
            rx = cx + sx * (X + X_OFFSET.get(idx, 0.0))   # + = outward
            items.append({"idx": idx, "sx": sx,
                          "rx": rx, "ry": ry, "w": w, "h": h})
    return items


def draw_belt_rectangles(c, cx, cy, **kw):
    """Draw the axis-aligned rectangles (solid, subtle gray)."""
    items = belt_rectangle_layout(cx, cy, **kw)
    c.saveState()
    c.setStrokeColor(Color(0.45, 0.45, 0.45))
    c.setLineWidth(0.6)
    for it in items:
        c.rect(it["rx"] - it["w"], it["ry"] - it["h"],
               2 * it["w"], 2 * it["h"], stroke=1, fill=0)
    c.restoreState()


def _swagger_controls(p0, p3, center=None, k_frac=1.25, k_min=14.0,
                      radial_exp=3.0, c2_boost=1.0, curl_deg=0.0):
    """Control points for a swagger from p3 (box) -> p0 (orbit).

    c1 (near the box)  : horizontal, so the curve leaves the rectangle flat
                         and keeps the S-swagger character everywhere.

    c2 (near the orbit): PARTIAL radial adoption. We blend the landing tangent
                         between HORIZONTAL (the original look) and RADIAL
                         (parallel to the sun-spoke) using a weight w that
                         depends on how vertical the spoke is at p0:

                             w = |cos(theta)| ** radial_exp

                         - Side lanes (3 & 9 o'clock): spoke ~horizontal, so
                           horizontal landing is already radial -> w ~ 0,
                           S-curves are left UNTOUCHED.
                         - Top/bottom (12 & 6 o'clock): spoke ~vertical, where
                           a horizontal landing would skim tangent -> w ~ 1,
                           so those problematic days swing to a radial landing.

                         radial_exp sharpens the transition: higher = radial
                         is confined to a tighter band around 12/6 o'clock.
                         center=None reproduces the pure-horizontal behavior.

    c2_boost / curl_deg: optional LOOP inducers (see LOOP_CURLS). Lengthening
                         c2 (boost > 1) and rotating its direction tangentially
                         (curl_deg != 0) makes the cubic self-intersect into a
                         small pigtail loop right at the landing point. Defaults
                         (1.0, 0.0) leave the curve untouched.
    """
    dirx = 1.0 if (p0[0] - p3[0]) >= 0 else -1.0
    k = max(k_frac * abs(p0[0] - p3[0]), k_min)
    c1 = (p3[0] + dirx * k, p3[1])

    # Horizontal landing tangent (original): the curve arrives moving in +dirx.
    h_dir = (dirx, 0.0)

    if center is None:
        c2 = (p0[0] - dirx * k, p0[1])
        return c1, c2

    # Radial geometry at the landing point.
    cx, cy = center
    ux, uy = p0[0] - cx, p0[1] - cy          # outward radial
    ulen = math.hypot(ux, uy) or 1.0
    ux, uy = ux / ulen, uy / ulen
    r_dir = (-ux, -uy)                         # radial INWARD (toward the sun)

    # Blend weight: 1 where the spoke is vertical (top/bottom), 0 on the sides.
    w = abs(uy) ** radial_exp

    # Blend the landing DIRECTION, then re-normalize.
    bx = (1.0 - w) * h_dir[0] + w * r_dir[0]
    by = (1.0 - w) * h_dir[1] + w * r_dir[1]
    blen = math.hypot(bx, by) or 1.0
    bx, by = bx / blen, by / blen

    # Optional tangential rotation to induce a pigtail loop at the landing.
    if curl_deg:
        a = math.radians(curl_deg)
        rx = bx * math.cos(a) - by * math.sin(a)
        ry = bx * math.sin(a) + by * math.cos(a)
        bx, by = rx, ry

    # Tangent at the cubic's endpoint p0 is along (p0 - c2); place c2 behind p0.
    # A longer c2 (c2_boost) makes the curve overshoot and curl back on itself.
    c2 = (p0[0] - bx * k * c2_boost, p0[1] - by * k * c2_boost)
    return c1, c2


def _swagger_connector(c, p0, p3, center=None, k_frac=1.25, k_min=14.0,
                       radial_exp=3.0, c2_boost=1.0, curl_deg=0.0):
    """S-swagger from the rectangle (p3) into the Pluto orbit (p0).

    Partial radial adoption: side S-curves stay horizontal; only the
    top/bottom (problematic) days swing to a radial landing. See
    _swagger_controls for the blend details. c2_boost/curl_deg optionally
    induce a pigtail loop at the landing (used in --landing between).
    """
    c1, c2 = _swagger_controls(p0, p3, center, k_frac, k_min, radial_exp,
                               c2_boost=c2_boost, curl_deg=curl_deg)
    c.bezier(p3[0], p3[1], c1[0], c1[1], c2[0], c2[1], p0[0], p0[1])


def _landing_direction(p0, p3, center, radial_exp):
    """Unit vector of TRAVEL at p0 (the direction the curve is heading as it
    arrives at the Pluto orbit). Equals normalize(p0 - c2)."""
    _, c2 = _swagger_controls(p0, p3, center, radial_exp=radial_exp)
    dx, dy = p0[0] - c2[0], p0[1] - c2[1]
    d = math.hypot(dx, dy) or 1.0
    return dx / d, dy / d


def draw_landing_arrowhead(c, p0, p3, center, radial_exp,
                           length=0.09 * inch, width=0.06 * inch):
    """Filled black arrowhead with its TIP on the Pluto orbit (p0), pointing
    in the curve's direction of travel (inward). Used for --landing on."""
    dx, dy = _landing_direction(p0, p3, center, radial_exp)
    # perpendicular to the travel direction
    px, py = -dy, dx
    # base sits 'length' behind the tip, wings splay out by 'width'/2
    bx, by = p0[0] - dx * length, p0[1] - dy * length
    left = (bx + px * width / 2.0, by + py * width / 2.0)
    right = (bx - px * width / 2.0, by - py * width / 2.0)

    c.saveState()
    c.setFillColor(Color(0.0, 0.0, 0.0))
    c.setStrokeColor(Color(0.0, 0.0, 0.0))
    c.setLineWidth(0.3)
    path = c.beginPath()
    path.moveTo(p0[0], p0[1])
    path.lineTo(*left)
    path.lineTo(*right)
    path.close()
    c.drawPath(path, stroke=1, fill=1)
    c.restoreState()


def draw_contact_dot(c, p0, radius=0.028 * inch):
    """Small filled black dot marking where the spoke, the Bezier, and the
    Pluto orbit all meet. Used for --landing between (sector borderlines)."""
    c.saveState()
    c.setFillColor(Color(0.0, 0.0, 0.0))
    c.setStrokeColor(Color(0.0, 0.0, 0.0))
    c.circle(p0[0], p0[1], radius, stroke=0, fill=1)
    c.restoreState()


# Cross-wiring DISABLED. Previously this swapped adjacent boxes at 12/3/6/9
# o'clock (days 1<->32, 8<->9, 16<->17, 24<->25) so their connectors crossed
# into a decorative S. In practice the crossings were non-intuitive and led to
# logging the wrong day, so every box now wires STRAIGHT to its own orbit slot.
# (To restore the old look, repopulate this dict: {7:8, 8:7, 23:24, 24:23,
#  0:31, 31:0, 15:16, 16:15}.)
ORBIT_SWAP = {}


# Pigtail loops at the landing (ONLY used for --landing between). Day 4's
# connector (the 3/4 border) already loops naturally; these values induce a
# matching little loop on its near-vertical neighbors. Keyed by DAY number:
#   value = (c2_boost, curl_deg)
# Tune or extend this dict to add/adjust loops; empty {} disables the effect.
LOOP_CURLS = {
    # --- top-right cluster (upper right quadrant) ---
    3: (1.20, -16.0),   # 2-3 border  (near-vertical -> negative curl)
    5: (1.10,  13.0),   # 4-5 border
    6: (1.15,  15.0),   # 5-6 border
    # day 4 (3-4 border) loops naturally; no entry needed

    # --- bottom-left cluster: 180-degree MIRROR of the top-right ---
    # Partner mapping (rotational): 3->19, 4->20, 5->21, 6->22. Day 20 is
    # induced because, unlike its partner day 4, it does not loop naturally
    # (the belt row stagger breaks perfect symmetry).
    19: (1.20, -16.0),  # 18-19 border  (mirror of day 3)
    20: (1.10,  12.0),  # 19-20 border  (mirror of day 4, induced)
    21: (1.10, -13.0),  # 20-21 border  (mirror of day 5)
    22: (1.15, -15.0),  # 21-22 border  (mirror of day 6)
}


def draw_bezier_connectors(c, cx, cy, pluto_d=2.5, n=32, landing="on",
                           radial_exp=5.0, **kw):
    """Connectors from each subsector to its box.

    landing:
      "on"      -> land at sector MIDPOINT (aligned with the day number)
      "between" -> land at the BORDERLINE between two dates (sector edge)

    radial_exp:
      Sharpness of the PARTIAL radial adoption on swagger landings. The blend
      weight is |cos(theta)| ** radial_exp, so higher values confine the
      radial landing to a tighter band around 12 & 6 o'clock (the problematic
      near-vertical days) and leave the side S-curves untouched.
    """
    r_pluto = (pluto_d / 2.0) * inch
    items = belt_rectangle_layout(cx, cy, n=n, **kw)
    step = 2.0 * math.pi / n
    # midpoint of a sector is +0.5 steps; a borderline is +0.0 steps
    land_bias = 0.5 if landing == "on" else 0.0

    c.saveState()
    c.setStrokeColor(Color(0.35, 0.35, 0.35))   # pencil gray
    c.setLineWidth(0.8)
    for it in items:
        orbit_idx = ORBIT_SWAP.get(it["idx"], it["idx"])
        theta = (orbit_idx + land_bias) * step
        p0 = (cx + r_pluto * math.sin(theta), cy + r_pluto * math.cos(theta))
        p3 = (it["rx"] - it["sx"] * it["w"], it["ry"])

        # Swagger connector for every day. In 'between' mode, selected days
        # get a pigtail loop at the landing (LOOP_CURLS).
        if landing == "between":
            boost, curl = LOOP_CURLS.get(it["idx"] + 1, (1.0, 0.0))
        else:
            boost, curl = (1.0, 0.0)
        _swagger_connector(c, p0, p3, (cx, cy), radial_exp=radial_exp,
                           c2_boost=boost, curl_deg=curl)

        # Contact marker at the Pluto orbit, style depends on landing mode:
        #   on      -> arrowhead pointing inward at the date's midpoint
        #   between -> filled dot at the borderline contact point
        if landing == "on":
            draw_landing_arrowhead(c, p0, p3, (cx, cy), radial_exp)
        else:
            draw_contact_dot(c, p0)
    c.restoreState()


def draw_day_numbers(c, cx, cy, neptune_d=2.0, pluto_d=2.5, n=32,
                     font_name="Helvetica", font_size=9, month_len=None):
    """Numbers 1..n in the Neptune-Pluto band, bottoms toward the sun.

    If month_len is given, days past it (e.g. 32 for a 31-day month) are
    skipped -- their cells get cross-hatched by draw_blocked_cell instead.
    """
    r_neptune = (neptune_d / 2.0) * inch
    r_pluto = (pluto_d / 2.0) * inch
    r_text = (r_neptune + r_pluto) / 2.0
    step_deg = 360.0 / n
    for i in range(n):
        if month_len is not None and (i + 1) > month_len:
            continue
        theta_deg = (i + 0.5) * step_deg
        c.saveState()
        c.translate(cx, cy)
        c.rotate(-theta_deg)
        c.setFont(font_name, font_size)
        c.drawCentredString(0, r_text - 0.35 * font_size, str(i + 1))
        c.restoreState()


def _annular_sector_path(c, cx, cy, r_in, r_out, theta0, theta1, steps=12):
    """A closed path for the wedge between r_in..r_out over theta0..theta1.

    Angles use the wheel convention: point = (cx + r*sin(t), cy + r*cos(t)),
    i.e. t measured clockwise from 12 o'clock. Used as a clip for hatching.
    """
    p = c.beginPath()
    for k in range(steps + 1):                    # outer arc theta0 -> theta1
        t = theta0 + (theta1 - theta0) * k / steps
        x, y = cx + r_out * math.sin(t), cy + r_out * math.cos(t)
        (p.moveTo if k == 0 else p.lineTo)(x, y)
    for k in range(steps + 1):                    # inner arc theta1 -> theta0
        t = theta1 - (theta1 - theta0) * k / steps
        p.lineTo(cx + r_in * math.sin(t), cy + r_in * math.cos(t))
    p.close()
    return p


def draw_blocked_cell(c, cx, cy, i, n, r_in, r_out,
                      spacing=3.2, line_width=0.5):
    """Cross-hatch the day-number cell for sector i (a blocked, non-existent
    day). We clip to the wedge and rule 45-degree parallel lines across it."""
    step = 2.0 * math.pi / n
    theta0, theta1 = i * step, (i + 1) * step
    c.saveState()
    c.clipPath(_annular_sector_path(c, cx, cy, r_in, r_out, theta0, theta1),
               stroke=0, fill=0)

    # Bounding box of the wedge (sample both arcs) for the ruling extent.
    xs, ys = [], []
    for r in (r_in, r_out):
        for k in range(13):
            t = theta0 + (theta1 - theta0) * k / 12.0
            xs.append(cx + r * math.sin(t))
            ys.append(cy + r * math.cos(t))
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)

    c.setStrokeColor(Color(0.35, 0.35, 0.35))
    c.setLineWidth(line_width)
    c.setDash()
    step_b = spacing * math.sqrt(2.0)             # perp spacing for 45deg lines
    b = (ymin - xmax)
    while b <= (ymax - xmin):                      # lines y = x + b
        c.line(xmin - 2, xmin - 2 + b, xmax + 2, xmax + 2 + b)
        b += step_b
    c.restoreState()


def draw_weekday_letters(c, cx, cy, start_weekday, month_len=None,
                         uranus_d=1.5, neptune_d=2.0, n=32,
                         font_name="Helvetica", font_size=8):
    """Weekday letters (M T W R F S U) in the ring just inside the numbers.

    start_weekday is the weekday index of day 1 (0=Mon..6=Sun). None -> the
    wheel stays blank (single-page / 2-up modes). Blocked days are skipped.
    """
    if start_weekday is None:
        return
    r_uranus = (uranus_d / 2.0) * inch
    r_neptune = (neptune_d / 2.0) * inch
    r_text = (r_uranus + r_neptune) / 2.0
    step_deg = 360.0 / n
    for i in range(n):
        if month_len is not None and (i + 1) > month_len:
            continue
        letter = WEEKDAY_LETTERS[(start_weekday + i) % 7]
        theta_deg = (i + 0.5) * step_deg
        c.saveState()
        c.translate(cx, cy)
        c.rotate(-theta_deg)
        c.setFont(font_name, font_size)
        c.drawCentredString(0, r_text - 0.35 * font_size, letter)
        c.restoreState()


def draw_hub_label(c, cx, cy, month_name, kind=None):
    """Two upright lines in the center hub: month name over '(kind)'.

    month_name None/empty -> nothing drawn (blank wheel).
    """
    if not month_name:
        return
    c.saveState()
    c.setFillColor(Color(0.1, 0.1, 0.1))
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(cx, cy + 2.0, month_name)
    if kind:
        c.setFont("Helvetica", 9.5)
        c.drawCentredString(cx, cy - 11.0, "(%s)" % kind)
    c.restoreState()


def draw_wheel(c, cx, cy, landing="on", radial_exp=5.0,
               month_name=None, kind=None, start_weekday=None, month_len=None):
    """Draw ONE complete month-wheel centered at (cx, cy).

    Calendar extras (all optional; omitted -> a blank wheel):
      month_name    -> hub label, top line (e.g. "March")
      kind          -> hub label, bottom line "(sleep)" / "(walk)"
      start_weekday -> weekday index (0=Mon..6=Sun) of day 1, drives the
                       weekday-letter ring
      month_len     -> real day count; surplus day cells are hatched out and
                       lose their number + weekday letter
    """
    for d in [2.5, 2.0, 1.5, 1.0]:
        c.circle(cx, cy, (d / 2.0) * inch, stroke=1, fill=0)

    draw_dotted_ellipse(c, cx, cy, major_in=4.0, minor_in=3.5)
    draw_subsector_lines(c, cx, cy, inner_d=1.0, outer_d=2.5, n_divisions=32)
    draw_bezier_connectors(c, cx, cy, pluto_d=2.5, n=32, landing=landing,
                           radial_exp=radial_exp,
                           major_in=4.0, minor_in=3.5,
                           rect_w_in=1.25, rect_h_in=0.25, gap_in=0.25)
    draw_belt_rectangles(c, cx, cy, major_in=4.0, minor_in=3.5,
                         rect_w_in=1.25, rect_h_in=0.25, gap_in=0.25, n=32)
    draw_day_numbers(c, cx, cy, neptune_d=2.0, pluto_d=2.5, n=32,
                     month_len=month_len)
    draw_weekday_letters(c, cx, cy, start_weekday, month_len=month_len,
                         uranus_d=1.5, neptune_d=2.0, n=32)

    # Hatch out any day-number cells beyond the real month length.
    if month_len is not None:
        r_in = (2.0 / 2.0) * inch           # Neptune orbit (inner edge of band)
        r_out = (2.5 / 2.0) * inch          # Pluto orbit  (outer edge of band)
        for i in range(month_len, 32):
            draw_blocked_cell(c, cx, cy, i, 32, r_in, r_out)

    draw_hub_label(c, cx, cy, month_name, kind)


# ---- 12-month SADDLE-STITCH booklet ----------------------------------------
# Physical build (exactly what you described):
#   1. Print DUPLEX on US Letter, SHORT-EDGE flip.
#   2. Trim each sheet's WIDTH down to A5 (8.27in) -- single RIGHT trim.
#   3. FOLD each sheet once at the horizontal middle (spine = fold).
#   4. NEST the folded sheets one inside another (sheet 1 outermost) and
#      staple the spine = a saddle-stitch booklet.
#
# ORIENTATION -- the important bit that was wrong before:
# The booklet reads as a flip-up pad. When you open to a spread you see the
# TOP page (the leaf that just flipped up, whose back is now showing) and the
# BOTTOM page (the freshly revealed leaf front). Two 180deg effects act on the
# top page: (a) the leaf physically flips 180 as it swings up, and (b) SHORT-
# EDGE duplex already prints the whole back side rotated 180. They CANCEL. So
# every wheel is drawn UPRIGHT (no manual rotation); we only place the right
# page in the right slot. Imposition (T=28 pages, 7 sheets, sheet i, i=1..7):
#   FRONT of sheet i:  top slot = page (30 - 2i),  bottom slot = page (2i - 1)
#   BACK  of sheet i:  top slot = page (2i),       bottom slot = page (29 - 2i)
#
# Calendar year starts in MARCH (Mar..Feb). 32 sectors kept for symmetry;
# cross out the non-days by hand.
MONTHS = ["Mar", "Apr", "May", "Jun", "Jul", "Aug",
          "Sep", "Oct", "Nov", "Dec", "Jan", "Feb"]

# Full names for the hub label.
MONTH_FULL = {
    "Mar": "March", "Apr": "April", "May": "May", "Jun": "June",
    "Jul": "July", "Aug": "August", "Sep": "September", "Oct": "October",
    "Nov": "November", "Dec": "December", "Jan": "January", "Feb": "February",
}

# Day counts, NON-leap (Feb = 28). Surplus sectors past this get hatched out.
MONTH_LENGTHS = {
    "Mar": 31, "Apr": 30, "May": 31, "Jun": 30, "Jul": 31, "Aug": 31,
    "Sep": 30, "Oct": 31, "Nov": 30, "Dec": 31, "Jan": 31, "Feb": 28,
}


def _month_start_weekdays(march_start):
    """Map each month -> the weekday index (0=Mon..6=Sun) of its 1st.

    March 1 is `march_start`; every later month rolls forward by that month's
    (non-leap) length mod 7. No surprises: 31 days of March always lands April
    on the weekday three past March's start, and so on around the year.
    """
    starts = {}
    w = march_start
    for m in MONTHS:
        starts[m] = w
        w = (w + MONTH_LENGTHS[m]) % 7
    return starts


BOOKLET_PAGES_TOTAL = 28


def _booklet_pages(march_start=6):
    """1-indexed page schedule (indices 1..28; index 0 unused).

    p1 blank; p2..p25 = Mar..Feb, each as sleep(between) then walk(on);
    p26..p28 blank. march_start (0=Mon..6=Sun, default Sunday) seeds each
    month's weekday phase. Every spec carries its full name, real day count,
    and start weekday so the wheel can label + hatch itself.
    """
    starts = _month_start_weekdays(march_start)
    pages = [None] * (BOOKLET_PAGES_TOTAL + 1)
    p = 2
    for m in MONTHS:
        common = {"month": m, "name": MONTH_FULL[m],
                  "start_weekday": starts[m], "month_len": MONTH_LENGTHS[m]}
        pages[p] = {**common, "kind": "sleep", "landing": "between"}
        pages[p + 1] = {**common, "kind": "walk", "landing": "on"}
        p += 2
    return pages                              # p1, p26, p27, p28 stay None


def _impose_saddle(total=BOOKLET_PAGES_TOTAL):
    """Return the PDF sheet sequence for a short-edge-duplex flip booklet.

    One entry per PHYSICAL sheet, in order. Each has 'front' and 'back' PDF
    pages; each page maps 'top'/'bottom' slot -> logical page number. Every
    slot is drawn UPRIGHT (short-edge duplex + the flip-up cancel out).
    """
    sheets = []
    n_sheets = total // 4
    for i in range(1, n_sheets + 1):
        sheets.append({
            "front": {"top": 30 - 2 * i, "bottom": 2 * i - 1},
            "back":  {"top": 2 * i,      "bottom": 29 - 2 * i},
        })
    return sheets


def _draw_proof_slot(c, cx, cy, pno, spec):
    "Big upright page number + label instead of a wheel (blank fold-test)."
    label = "blank" if spec is None else f"{spec['month']} {spec['kind']}"
    c.saveState()
    c.setFillColor(Color(0.1, 0.1, 0.1))
    c.setFont("Helvetica-Bold", 64)
    c.drawCentredString(cx, cy - 6, str(pno))
    c.setFont("Helvetica", 12)
    c.drawCentredString(cx, cy + 50, "^ this edge = page top")
    c.drawCentredString(cx, cy - 34, label)
    c.restoreState()


def _draw_booklet_furniture(c, a5_w, height):
    "Fold spine at the middle + single right-side trim guide (every sheet)."
    draw_fold_line(c, 0.0, a5_w, height / 2.0)
    draw_side_crop_marks(c, a5_w, 0.0, height)


def create_booklet(filename="sleep_wheel_booklet.pdf", radial_exp=5.0,
                   proof=False, march_start=6):
    """12-month A5 saddle-stitch booklet on 7 US Letter sheets (duplex).

    PDF page order is front,back,front,back... (14 pages). Print DUPLEX,
    SHORT-EDGE flip, 100%. proof=True prints big page numbers so you can fold
    a blank dummy and confirm collation before committing the real wheels.
    march_start (0=Mon..6=Sun) sets the weekday of MARCH 1.
    """
    width, height = letter                    # portrait 8.5 x 11
    a5_w = landscape(A5)[0]                    # 8.27 finished width
    cx = a5_w / 2.0
    y_bottom, y_top = height / 4.0, 3.0 * height / 4.0

    pages = _booklet_pages(march_start)
    sheets = _impose_saddle()
    c = canvas.Canvas(filename, pagesize=letter)

    for sheet in sheets:
        for side in ("front", "back"):        # PDF order; printer duplexes them
            slots = sheet[side]
            pt, pb = slots["top"], slots["bottom"]
            if proof:
                _draw_proof_slot(c, cx, y_top, pt, pages[pt])
                _draw_proof_slot(c, cx, y_bottom, pb, pages[pb])
            else:
                for pno, y in ((pt, y_top), (pb, y_bottom)):
                    sp = pages[pno]
                    if sp is not None:
                        draw_wheel(c, cx, y, sp["landing"], radial_exp,
                                   month_name=sp["name"], kind=sp["kind"],
                                   start_weekday=sp["start_weekday"],
                                   month_len=sp["month_len"])
            _draw_booklet_furniture(c, a5_w, height)
            c.showPage()

    c.save()
    kind = "PROOF (numbered)" if proof else "booklet"
    print(f"Created 12-month saddle-stitch {kind}: {filename}  "
          f"(7 letter sheets, DUPLEX short-edge -> 28 A5 pages, Mar..Feb)")


def create_a5_concentric_circles(filename="blank_a5_landscape.pdf",
                                 landing="on", paper="a5-in-letter",
                                 radial_exp=5.0, two_up=TWO_UP_LANDINGS):
    """Month-wheel on a US Letter sheet.

    See module docstring / --paper help for what each layout produces.
    two_up: a (top_landing, bottom_landing) tuple used for the 2-up and fold
    layouts.
    """
    # --- 2-up (CUT) and fold (FOLD): both stack two wheels on portrait letter
    if paper in ("letter-2up", "a5-fold-in-letter"):
        page_size = letter              # PORTRAIT 8.5 x 11 in
        width, height = page_size
        c = canvas.Canvas(filename, pagesize=page_size)

        top_landing, bottom_landing = two_up
        is_fold = (paper == "a5-fold-in-letter")

        if is_fold:
            # FLUSH-LEFT layout: the finished A5-width page hugs the paper's
            # LEFT edge, so ALL the excess width piles into a SINGLE trim margin
            # on the RIGHT (~0.23in, clear of the printer dead zone). One cut
            # instead of two. Print at 100% and slice once down the right guide.
            a5_w = landscape(A5)[0]               # 8.27 in finished width
            cx_wheel = a5_w / 2.0                 # center wheels in that width
            draw_wheel(c, cx_wheel, 3.0 * height / 4.0, top_landing, radial_exp)
            draw_wheel(c, cx_wheel, 1.0 * height / 4.0, bottom_landing,
                       radial_exp)
            draw_fold_line(c, 0.0, a5_w, height / 2.0)
            draw_side_crop_marks(c, a5_w, 0.0, height)
            note = (f"top={top_landing}, bottom={bottom_landing}, "
                    f"FOLD, flush-left (single right cut)")
        else:
            # Both wheels centered; center CUT line -> two half-letter pages.
            draw_wheel(c, width / 2.0, 3.0 * height / 4.0, top_landing,
                       radial_exp)
            draw_wheel(c, width / 2.0, 1.0 * height / 4.0, bottom_landing,
                       radial_exp)
            draw_cut_line(c, 0.0, width, height / 2.0)
            note = f"top={top_landing}, bottom={bottom_landing}, CUT"

        c.showPage()
        c.save()
        print(f"Created month-wheel PDF: {filename}  (paper={paper}, {note})")
        return

    # --- half-letter stock, edge-to-edge (page IS the finished size) ---
    if paper == "half-letter-in-half-letter":
        page_size = landscape(HALF_LETTER)   # 8.5 x 5.5 in sheet
        width, height = page_size
        cx, cy = width / 2.0, height / 2.0
        c = canvas.Canvas(filename, pagesize=page_size)

        draw_wheel(c, cx, cy, landing, radial_exp)
        # No trim box: the sheet already equals the finished page.

        c.showPage()
        c.save()
        print(f"Created month-wheel PDF: {filename}  "
              f"(landing={landing}, paper={paper})")
        return

    # --- single wheel on a letter LANDSCAPE sheet, with a trim box ---
    page_size = landscape(letter)       # 11 x 8.5 in sheet
    width, height = page_size
    cx, cy = width / 2.0, height / 2.0
    c = canvas.Canvas(filename, pagesize=page_size)

    draw_wheel(c, cx, cy, landing, radial_exp)

    if paper == "half-letter-in-letter":
        trim_w, trim_h = landscape(HALF_LETTER)   # 8.5 x 5.5 trim box
    else:  # "a5-in-letter"
        trim_w, trim_h = landscape(A5)            # 8.27 x 5.83 trim box
    draw_trim_border(c, cx, cy, trim_w, trim_h)

    c.showPage()
    c.save()
    print(f"Created month-wheel PDF: {filename}  "
          f"(landing={landing}, paper={paper})")


def _parse_weekday(value):
    """Parse --start-weekday into a 0..6 index (0=Mon..6=Sun).

    Accepts full names, common abbreviations, or the single letters
    m/t/w/r/f/s/u (matching the wheel's WEEKDAY_LETTERS).
    """
    key = value.strip().lower()
    if key not in _WEEKDAY_PARSE:
        raise argparse.ArgumentTypeError(
            "must be a weekday (monday..sunday) or a letter m/t/w/r/f/s/u; "
            "got: %r" % value)
    return _WEEKDAY_PARSE[key]


def _parse_two_up(value):
    """Parse a --two-up 'top,bottom' string into a (top, bottom) tuple.

    Accepts 'on' / 'between' for each slot. A single value (e.g. 'on') is
    applied to BOTH wheels. Raises argparse error on anything else.
    """
    parts = [p.strip().lower() for p in value.split(",")]
    if len(parts) == 1:
        parts = parts * 2
    if len(parts) != 2 or any(p not in ("on", "between") for p in parts):
        raise argparse.ArgumentTypeError(
            "must be 'top,bottom' using 'on'/'between' "
            "(e.g. 'between,on', 'on,on', 'between'); got: %r" % value)
    return tuple(parts)


# All PDFs land in this subfolder by default (created on demand). Pass --output
# with an explicit directory (e.g. "sub/foo.pdf" or "/tmp/foo.pdf") to override.
DEFAULT_OUTPUT_DIR = "output"


def _resolve_output_path(filename, output_dir=DEFAULT_OUTPUT_DIR):
    """Route a bare filename into the default output subfolder and ensure the
    target directory exists. If `filename` already carries a directory part, it
    is honored verbatim (only its parent is created)."""
    head, _ = os.path.split(filename)
    if not head:
        filename = os.path.join(output_dir, filename)
        head = output_dir
    os.makedirs(head, exist_ok=True)
    return filename


def main():
    parser = argparse.ArgumentParser(
        description="A5 month-wheel sleep/habit tracker.")
    parser.add_argument(
        "--landing", choices=["on", "between"], default="on",
        help="Where connectors meet the Pluto orbit: 'on' the dates "
             "(sector midpoints) or 'between' dates (sector borderlines). "
             "Ignored for the 2-up/fold layouts (use --two-up instead). "
             "Default: on")
    parser.add_argument(
        "--paper",
        choices=["a5-in-letter", "half-letter-in-letter",
                 "half-letter-in-half-letter", "letter-2up",
                 "a5-fold-in-letter", "booklet", "booklet-proof"],
        default="booklet",
        help="Output layout. 'a5-in-letter' = letter landscape + A5 trim box. "
             "'half-letter-in-letter' = letter landscape + half-letter trim "
             "box. 'half-letter-in-half-letter' = half-letter sheet, "
             "edge-to-edge. 'letter-2up' = two wheels on portrait letter with a "
             "center CUT line -> two half-letter pages. 'a5-fold-in-letter' = "
             "two wheels on portrait letter with a center FOLD line (both "
             "upright); fold + trim sides for an A5-ish double-sided card. "
             "Default: booklet")
    parser.add_argument(
        "--two-up", type=_parse_two_up, default=TWO_UP_LANDINGS,
        dest="two_up", metavar="TOP,BOTTOM",
        help="For letter-2up / a5-fold-in-letter: the landing of each wheel as "
             "'top,bottom' using 'on'/'between'. A single value applies to "
             "both (e.g. 'on' -> both on). Examples: 'between,on' (default), "
             "'on,on', 'between,between', 'on,between'.")
    parser.add_argument(
        "--radial-sharpness", type=float, default=5.0, dest="radial_exp",
        help="Sharpness of the partial radial landing (blend weight is "
             "|cos(theta)| ** sharpness). Higher = radial confined to a "
             "tighter band around 12 & 6 o'clock, leaving the side S-curves "
             "untouched. 0 = pure horizontal (old look). Default: 5.0")
    parser.add_argument(
        "--start-weekday", type=_parse_weekday, default="sunday",
        dest="start_weekday", metavar="DAY",
        help="Weekday of MARCH 1 (booklet only). Full name, abbreviation, or "
             "letter m/t/w/r/f/s/u. Every later month rolls forward from it. "
             "Default: sunday")
    parser.add_argument(
        "--output", default=None,
        help="Output PDF filename. A bare name is written into the '%s/' "
             "subfolder; include a directory to override. "
             "Default: sleep_wheel_<landing>_<paper>.pdf" % DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    if args.paper in ("booklet", "booklet-proof"):
        proof = args.paper == "booklet-proof"
        start = WEEKDAY_ABBR[args.start_weekday]     # e.g. "sun" for Mar 1 = Sun
        stem = "sleep_wheel_booklet_proof" if proof else "sleep_wheel_booklet"
        default = f"{stem}-start-{start}.pdf"
        out = _resolve_output_path(args.output or default)
        create_booklet(filename=out, radial_exp=args.radial_exp, proof=proof,
                       march_start=args.start_weekday)
        return

    out = _resolve_output_path(
        args.output or f"sleep_wheel_{args.landing}_{args.paper}.pdf")
    create_a5_concentric_circles(filename=out, landing=args.landing,
                                 paper=args.paper, radial_exp=args.radial_exp,
                                 two_up=args.two_up)


if __name__ == "__main__":
    main()
