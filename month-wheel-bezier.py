#!/usr/bin/env python3
"""Landscape A5 month-wheel habit tracker.

Two facing A5 pages = one month. This wheel drives the sleep tracker: each
night's Bezier connector runs from the wheel out to a belt rectangle.

Connector LANDING on the Pluto orbit is switchable via --landing:
  * on      -> land at each sector's MIDPOINT (aligned with the day number)
  * between -> land at the BORDERLINE between two dates (sector edge)

Connector styles:
  * side lanes      -> horizontal S-swagger (k_frac=1.25)
  * 12 & 6 o'clock  -> vertical drop with a little loop
  * swapped pairs   -> cross into a gentle S (8/9, 24/25, 1/32, 16/17)

Usage:
  python month-wheel-bezier_24.py --landing on
  python month-wheel-bezier_24.py --landing between --output sleep_between.pdf
"""

import argparse
import math

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import Color


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


def _catmull_rom(c, pts):
    """Draw a smooth path through pts using Catmull-Rom -> Bezier segments."""
    p = c.beginPath()
    p.moveTo(*pts[0])
    n = len(pts)
    for i in range(n - 1):
        p0 = pts[max(i - 1, 0)]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[min(i + 2, n - 1)]
        c1x = p1[0] + (p2[0] - p0[0]) / 6.0
        c1y = p1[1] + (p2[1] - p0[1]) / 6.0
        c2x = p2[0] - (p3[0] - p1[0]) / 6.0
        c2y = p2[1] - (p3[1] - p1[1]) / 6.0
        p.curveTo(c1x, c1y, c2x, c2y, p2[0], p2[1])
    c.drawPath(p, stroke=1, fill=0)


def _tendril_points(p0, p3, waves=1.6, amp=0.28 * inch, samples=90,
                    phase=0.0, taper=True, loop_at=None, loop_r=0.14 * inch):
    """Sample points for a meandering tendril; optional loop/curl at loop_at."""
    p0x, p0y = p0
    p3x, p3y = p3
    dx, dy = p3x - p0x, p3y - p0y
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux

    pts = []
    for s in range(samples + 1):
        t = s / samples
        bx = p0x + dx * t
        by = p0y + dy * t
        env = math.sin(math.pi * t) if taper else 1.0
        off = amp * env * math.sin(2.0 * math.pi * waves * t + phase)
        px = bx + nx * off
        py = by + ny * off
        if loop_at is not None and abs(t - loop_at) < (0.5 / samples):
            for a in range(0, 361, 20):
                ang = math.radians(a)
                pts.append((px + loop_r * math.cos(ang) - loop_r,
                            py + loop_r * math.sin(ang)))
        pts.append((px, py))
    return pts


def _swagger_controls(p0, p3, k_frac=1.25, k_min=14.0):
    """Return the two horizontal control points for a swagger from p3 -> p0."""
    dirx = 1.0 if (p0[0] - p3[0]) >= 0 else -1.0
    k = max(k_frac * abs(p0[0] - p3[0]), k_min)
    c1 = (p3[0] + dirx * k, p3[1])
    c2 = (p0[0] - dirx * k, p0[1])
    return c1, c2


def _swagger_connector(c, p0, p3, k_frac=1.25, k_min=14.0):
    """Horizontal S-swagger from the rectangle (p3) into the Pluto orbit (p0)."""
    c1, c2 = _swagger_controls(p0, p3, k_frac, k_min)
    c.bezier(p3[0], p3[1], c1[0], c1[1], c2[0], c2[1], p0[0], p0[1])


def _loop_connector(c, p0, p3, loop_r=0.13 * inch):
    """Vertical drop (12 & 6 o'clock) with a single little loop en route."""
    pts = _tendril_points(p3, p0, waves=0.0, amp=0.0, phase=0.0,
                          taper=False, loop_at=0.5, loop_r=loop_r)
    _catmull_rom(c, pts)


# Cross adjacent boxes so their connectors form a gentle S (idx-based):
#   day 8 <-> day 9,  day 24 <-> day 25,  day 1 <-> day 32,  day 16 <-> day 17
ORBIT_SWAP = {7: 8, 8: 7, 23: 24, 24: 23,
              0: 31, 31: 0, 15: 16, 16: 15}


def draw_bezier_connectors(c, cx, cy, pluto_d=2.5, n=32, landing="on", **kw):
    """Connectors from each subsector to its box.

    landing:
      "on"      -> land at sector MIDPOINT (aligned with the day number)
      "between" -> land at the BORDERLINE between two dates (sector edge)
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

        span_x = abs(p3[0] - p0[0])
        span_y = abs(p3[1] - p0[1])
        if it["idx"] in ORBIT_SWAP:
            _swagger_connector(c, p0, p3)
        elif span_x < 0.55 * span_y:
            _loop_connector(c, p0, p3)
        else:
            _swagger_connector(c, p0, p3)
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


def create_a5_concentric_circles(filename="blank_a5_landscape.pdf",
                                 landing="on"):
    """Landscape A5 (210 x 148 mm) month-wheel."""
    page_size = landscape(A5)
    width, height = page_size
    cx, cy = width / 2.0, height / 2.0
    c = canvas.Canvas(filename, pagesize=page_size)

    for d in [2.5, 2.0, 1.5, 1.0]:
        c.circle(cx, cy, (d / 2.0) * inch, stroke=1, fill=0)

    draw_dotted_ellipse(c, cx, cy, major_in=4.0, minor_in=3.5)
    draw_subsector_lines(c, cx, cy, inner_d=1.0, outer_d=2.5, n_divisions=32)
    draw_bezier_connectors(c, cx, cy, pluto_d=2.5, n=32, landing=landing,
                           major_in=4.0, minor_in=3.5,
                           rect_w_in=1.25, rect_h_in=0.25, gap_in=0.25)
    draw_belt_rectangles(c, cx, cy, major_in=4.0, minor_in=3.5,
                         rect_w_in=1.25, rect_h_in=0.25, gap_in=0.25, n=32)
    draw_day_numbers(c, cx, cy, neptune_d=2.0, pluto_d=2.5, n=32)

    c.showPage()
    c.save()
    print(f"Created month-wheel PDF: {filename}  (landing={landing})")


def main():
    parser = argparse.ArgumentParser(
        description="A5 month-wheel sleep/habit tracker.")
    parser.add_argument(
        "--landing", choices=["on", "between"], default="on",
        help="Where connectors meet the Pluto orbit: 'on' the dates "
             "(sector midpoints) or 'between' dates (sector borderlines). "
             "Default: on")
    parser.add_argument(
        "--output", default=None,
        help="Output PDF filename. Default: sleep_wheel_<landing>.pdf")
    args = parser.parse_args()

    out = args.output or f"sleep_wheel_{args.landing}.pdf"
    create_a5_concentric_circles(filename=out, landing=args.landing)


if __name__ == "__main__":
    main()
