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


def _simple_connector(c, p0, p3, sx, handle=0.45):
    """Single smooth S: horizontal tangents at both ends."""
    p0x, p0y = p0
    p3x, p3y = p3
    k = max(handle * abs(p3x - p0x), 10.0)
    c.bezier(p0x, p0y,
             p0x + sx * k, p0y,
             p3x - sx * k, p3y,
             p3x, p3y)


def _frolicky_connector(c, p0, p3, sx, handle=0.6, wiggle=0.18 * inch):
    """Smooth double-inflection S: two chained cubics with horizontal tangents
    at the start, the middle waypoint, and the end -> no sharp corners, but a
    wander-y, hand-drawn feel. The mid waypoint is nudged vertically so the
    path loops out before settling into the box."""
    p0x, p0y = p0
    p3x, p3y = p3

    mx = (p0x + p3x) / 2.0
    my = (p0y + p3y) / 2.0
    # push the mid waypoint away from the wheel center for a frolicky bulge
    my += wiggle if p3y >= 0 else -wiggle

    k1 = max(handle * abs(mx - p0x), 10.0)
    k2 = max(handle * abs(p3x - mx), 10.0)

    # segment 1: p0 -> mid  (horizontal tangents both ends)
    c.bezier(p0x, p0y,
             p0x + sx * k1, p0y,
             mx - sx * k1, my,
             mx, my)
    # segment 2: mid -> p3  (horizontal tangents both ends -> smooth join)
    c.bezier(mx, my,
             mx + sx * k2, my,
             p3x - sx * k2, p3y,
             p3x, p3y)


def draw_bezier_connectors(c, cx, cy, pluto_d=2.5, n=32, **kw):
    """S-curve connectors from each subsector's Pluto-orbit edge to its box.
    Corner day-groups (FROLICKY_DAYS) get the wander-y double-inflection path.
    """
    r_pluto = (pluto_d / 2.0) * inch
    items = belt_rectangle_layout(cx, cy, n=n, **kw)
    step = 2.0 * math.pi / n

    c.saveState()
    c.setStrokeColor(Color(0.45, 0.45, 0.45))
    c.setLineWidth(0.6)
    for it in items:
        theta = (it["idx"] + 0.5) * step
        p0 = (cx + r_pluto * math.sin(theta), cy + r_pluto * math.cos(theta))
        p3 = (it["rx"] - it["sx"] * it["w"], it["ry"])
        day = it["idx"] + 1
        # translate so wiggle sign uses page-relative y (above/below center)
        p0_rel = (p0[0], p0[1] - cy)
        p3_rel = (p3[0], p3[1] - cy)
        if day in FROLICKY_DAYS:
            # draw in center-relative coords for the wiggle sign, then offset
            c.saveState()
            c.translate(0, cy)
            _frolicky_connector(c, p0_rel, p3_rel, it["sx"])
            c.restoreState()
        else:
            _simple_connector(c, p0, p3, it["sx"])
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
