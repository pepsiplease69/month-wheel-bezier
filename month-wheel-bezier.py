#!/usr/bin/env python3
"""Landscape A5 month-wheel: concentric orbits, Kuiper belt, subsectors,
day numbers, belt rectangles, and horizontal S-curve Bezier connectors.

The four diagonal "corner" day-groups get a frolicky double-inflection
connector (smooth, hand-drawn feel, no sharp corners):
    upper-right  2-5,  lower-right 12-15,
    lower-left  17-20, upper-left  27-30.
"""

import math

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import Color

# Day numbers (1-based) that get the extra-wiggly connector.
FROLICKY_DAYS = set(range(2, 6)) | set(range(12, 16)) \
    | set(range(17, 21)) | set(range(27, 31))


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

    per_side = n // 2
    items = []
    for j in range(per_side):
        Y = B - j * (2.0 * B / (per_side - 1))
        ratio = max(0.0, 1.0 - (Y / B) ** 2)
        X = max(A * math.sqrt(ratio), min_off)
        for sx in (1, -1):
            idx = j if sx == 1 else (n - 1 - j)
            items.append({"idx": idx, "sx": sx,
                          "rx": cx + sx * X, "ry": cy + Y, "w": w, "h": h})
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


def _squiggle_points(p0, p3, waves=3.0, amp=0.09 * inch, samples=64,
                     phase=0.0, taper=True):
    """Sample points along p0->p3 with a sinusoidal perpendicular wobble,
    producing a hand-drawn, flame-like tendril."""
    p0x, p0y = p0
    p3x, p3y = p3
    dx, dy = p3x - p0x, p3y - p0y
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length          # along-path unit vector
    nx, ny = -uy, ux                            # perpendicular unit vector

    pts = []
    for s in range(samples + 1):
        t = s / samples
        # base point along the straight line
        bx = p0x + dx * t
        by = p0y + dy * t
        # sinusoidal offset; taper the ends so it starts/lands cleanly
        env = math.sin(math.pi * t) if taper else 1.0
        off = amp * env * math.sin(2.0 * math.pi * waves * t + phase)
        pts.append((bx + nx * off, by + ny * off))
    return pts


def _simple_connector(c, p0, p3, sx, waves=2.5, amp=0.08 * inch, phase=0.0):
    """A gently wiggly tendril from p0 to p3."""
    pts = _squiggle_points(p0, p3, waves=waves, amp=amp, phase=phase)
    _catmull_rom(c, pts)


def _frolicky_connector(c, p0, p3, sx, waves=2.5, amp=0.13 * inch, phase=0.0):
    """A more frolicky, multi-wave tendril from p0 to p3."""
    pts = _squiggle_points(p0, p3, waves=waves, amp=amp, phase=phase)
    _catmull_rom(c, pts)


def draw_bezier_connectors(c, cx, cy, pluto_d=2.5, n=32, **kw):
    """S-curve connectors from each subsector's Pluto-orbit edge to its box.
    Corner day-groups (FROLICKY_DAYS) get the wander-y double-inflection path.
    """
    r_pluto = (pluto_d / 2.0) * inch
    items = belt_rectangle_layout(cx, cy, n=n, **kw)
    step = 2.0 * math.pi / n

    c.saveState()
    c.setStrokeColor(Color(0.85, 0.20, 0.15))   # red, like the sketch
    c.setLineWidth(1.0)
    for it in items:
        theta = (it["idx"] + 0.5) * step
        # start on the Pluto orbit for this subsector
        p0 = (cx + r_pluto * math.sin(theta), cy + r_pluto * math.cos(theta))
        # end at the rectangle's inner edge
        p3 = (it["rx"] - it["sx"] * it["w"], it["ry"])
        day = it["idx"] + 1
        phase = (it["idx"] * 1.7) % (2.0 * math.pi)   # vary each tendril
        if day in FROLICKY_DAYS:
            _frolicky_connector(c, p0, p3, it["sx"], phase=phase)
        else:
            _simple_connector(c, p0, p3, it["sx"], phase=phase)
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


def create_a5_concentric_circles(filename: str = "blank_a5_landscape.pdf") -> None:
    """Landscape A5 (210 x 148 mm) month-wheel."""
    page_size = landscape(A5)
    width, height = page_size
    cx, cy = width / 2.0, height / 2.0
    c = canvas.Canvas(filename, pagesize=page_size)

    # --- Concentric circles (solid): Pluto, Neptune, Uranus, Saturn ---
    for d in [2.5, 2.0, 1.5, 1.0]:
        c.circle(cx, cy, (d / 2.0) * inch, stroke=1, fill=0)

    # --- Kuiper belt (dotted ellipse) ---
    draw_dotted_ellipse(c, cx, cy, major_in=4.0, minor_in=3.5)

    # --- 32 subsector spokes (Saturn -> Pluto) ---
    draw_subsector_lines(c, cx, cy, inner_d=1.0, outer_d=2.5, n_divisions=32)

    # --- Connectors (drawn under the rectangles) ---
    draw_bezier_connectors(c, cx, cy, pluto_d=2.5, n=32,
                           major_in=4.0, minor_in=3.5,
                           rect_w_in=1.25, rect_h_in=0.25, gap_in=0.25)

    # --- 32 horizontal rectangles just outside the Kuiper belt ---
    draw_belt_rectangles(c, cx, cy, major_in=4.0, minor_in=3.5,
                         rect_w_in=1.25, rect_h_in=0.25, gap_in=0.25, n=32)

    # --- Day numbers 1..32 (bottoms toward the sun) ---
    draw_day_numbers(c, cx, cy, neptune_d=2.0, pluto_d=2.5, n=32)

    c.showPage()
    c.save()
    print(f"Created month-wheel PDF: {filename}")


if __name__ == "__main__":
    create_a5_concentric_circles()
