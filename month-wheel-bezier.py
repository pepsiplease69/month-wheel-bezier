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

Paper (--paper): every mode prints on a US Letter sheet, so you only need
letter stock and a trimmer/guillotine:
  * a5-in-letter          -> US Letter LANDSCAPE with an A5 (8.27x5.83) TRIM
                             box + corner crop marks. Print at 100% (actual
                             size, no "fit to page") then cut to A5.
  * half-letter-in-letter -> US Letter LANDSCAPE with a HALF-LETTER (8.5x5.5)
                             TRIM box + corner crop marks. Cut to half-letter.
  * half-letter-in-half-letter -> HALF-LETTER (8.5x5.5) LANDSCAPE sheet,
                             edge-to-edge. Print directly on half-letter stock;
                             no trim box or crop marks needed.
  * letter-2up            -> TWO wheels on a US Letter PORTRAIT sheet (8.5x11),
                             split by a center cut line. Landings set by
                             --two-up (default: between,on). Cut in half for
                             two half-letter pages.

Usage:
  python month-wheel-bezier_35.py --landing on --paper a5-in-letter
  python month-wheel-bezier_35.py --landing between --paper half-letter-in-letter
  python month-wheel-bezier_35.py --paper letter-2up --two-up between,on
"""

import argparse
import math

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5, letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import Color

# Half US Letter ("statement" / Junior size) = 5.5 x 8.5 in. This is a common
# US planner/binder size that is loosely (but not exactly) "A5". Reportlab has
# no built-in constant, so define it in portrait; landscape() flips it to
# 8.5 x 5.5.
HALF_LETTER = (5.5 * inch, 8.5 * inch)

# Default letter-2up wheel landings, TOP first then BOTTOM. Overridable at the
# command line with --two-up (e.g. "on,on", "between,between", "on,between").
TWO_UP_LANDINGS = ("between", "on")


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

    # Top/bottom pairs stagger VERTICALLY (open space above/below):
    #   day 1  (idx 0)  -> up 0.25"      day 17 (idx 16) -> down 0.25"
    Y_OFFSET = {0: 0.25 * inch, 16: -0.25 * inch}

    # Side pairs stagger HORIZONTALLY (no vertical neighbor is disturbed):
    #   day 8  (idx 7)  -> out 0.25"     day 9  (idx 8)  -> in 0.25"
    #   day 24 (idx 23) -> out 0.25"     day 25 (idx 24) -> in 0.25"
    X_OFFSET = {7: 0.25 * inch, 8: -0.25 * inch,
                23: 0.25 * inch, 24: -0.25 * inch}

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


# Cross adjacent boxes so their connectors form a gentle S (idx-based):
#   day 8 <-> day 9,  day 24 <-> day 25,  day 1 <-> day 32,  day 16 <-> day 17
ORBIT_SWAP = {7: 8, 8: 7, 23: 24, 24: 23,
              0: 31, 31: 0, 15: 16, 16: 15}


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
                     font_name="Helvetica", font_size=9):
    """Numbers 1..n in the Neptune-Pluto band, bottoms toward the sun."""
    r_neptune = (neptune_d / 2.0) * inch
    r_pluto = (pluto_d / 2.0) * inch
    r_text = (r_neptune + r_pluto) / 2.0
    step_deg = 360.0 / n
    for i in range(n):
        theta_deg = (i + 0.5) * step_deg
        c.saveState()
        c.translate(cx, cy)
        c.rotate(-theta_deg)
        c.setFont(font_name, font_size)
        c.drawCentredString(0, r_text - 0.35 * font_size, str(i + 1))
        c.restoreState()


def draw_wheel(c, cx, cy, landing="on", radial_exp=5.0):
    """Draw ONE complete month-wheel centered at (cx, cy).

    Extracted so it can be placed once (single-wheel sheets) or twice
    (letter-2up) on the same canvas.
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
    draw_day_numbers(c, cx, cy, neptune_d=2.0, pluto_d=2.5, n=32)


def create_a5_concentric_circles(filename="blank_a5_landscape.pdf",
                                 landing="on", paper="a5-in-letter",
                                 radial_exp=5.0, two_up=TWO_UP_LANDINGS):
    """Month-wheel on a US Letter sheet.

    paper:
      "a5-in-letter"          -> letter LANDSCAPE + A5 (8.27x5.83) trim box
                                 + crop marks. Cut to A5.
      "half-letter-in-letter" -> letter LANDSCAPE + half-letter (8.5x5.5) trim
                                 box + crop marks. Cut to half-letter.
      "half-letter-in-half-letter" -> half-letter (8.5x5.5) LANDSCAPE sheet,
                                 edge-to-edge (no trim box). Print on
                                 half-letter stock directly.
      "letter-2up"            -> two wheels on a letter PORTRAIT sheet (8.5x11)
                                 with a center cut line. two_up = (top, bottom)
                                 landings. The --landing flag is ignored here.

    two_up: a (top_landing, bottom_landing) tuple used only for letter-2up.
    """
    # --- 2-up: two wheels on a portrait letter sheet, split by a cut line ---
    if paper == "letter-2up":
        page_size = letter              # PORTRAIT 8.5 x 11 in
        width, height = page_size
        c = canvas.Canvas(filename, pagesize=page_size)

        top_landing, bottom_landing = two_up
        # Each half-letter region is 8.5 x 5.5; center a wheel in each.
        draw_wheel(c, width / 2.0, 3.0 * height / 4.0, top_landing, radial_exp)
        draw_wheel(c, width / 2.0, 1.0 * height / 4.0, bottom_landing,
                   radial_exp)

        # Center cut line separating the two half-letter pages.
        draw_cut_line(c, 0.0, width, height / 2.0)

        c.showPage()
        c.save()
        print(f"Created month-wheel PDF: {filename}  "
              f"(paper={paper}, top={top_landing}, bottom={bottom_landing})")
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


def main():
    parser = argparse.ArgumentParser(
        description="A5 month-wheel sleep/habit tracker.")
    parser.add_argument(
        "--landing", choices=["on", "between"], default="on",
        help="Where connectors meet the Pluto orbit: 'on' the dates "
             "(sector midpoints) or 'between' dates (sector borderlines). "
             "Ignored for --paper letter-2up (use --two-up instead). "
             "Default: on")
    parser.add_argument(
        "--paper",
        choices=["a5-in-letter", "half-letter-in-letter",
                 "half-letter-in-half-letter", "letter-2up"],
        default="a5-in-letter",
        help="Output layout. 'a5-in-letter' = letter landscape + A5 trim box "
             "+ crop marks. 'half-letter-in-letter' = letter landscape + "
             "half-letter trim box + crop marks. 'half-letter-in-half-letter' "
             "= half-letter landscape sheet, edge-to-edge (print on half-letter "
             "stock, no trimming). 'letter-2up' = two wheels on a portrait "
             "letter sheet with a center cut line (see --two-up). "
             "Default: a5-in-letter")
    parser.add_argument(
        "--two-up", type=_parse_two_up, default=TWO_UP_LANDINGS,
        dest="two_up", metavar="TOP,BOTTOM",
        help="For --paper letter-2up: the landing of each wheel as "
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
        "--output", default=None,
        help="Output PDF filename. Default: sleep_wheel_<landing>_<paper>.pdf")
    args = parser.parse_args()

    out = args.output or f"sleep_wheel_{args.landing}_{args.paper}.pdf"
    create_a5_concentric_circles(filename=out, landing=args.landing,
                                 paper=args.paper, radial_exp=args.radial_exp,
                                 two_up=args.two_up)


if __name__ == "__main__":
    main()
