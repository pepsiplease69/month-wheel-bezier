#!/usr/bin/env python3
"""Create a landscape A5 PDF with 4 concentric circles centered on the page."""

import math

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import Color


def draw_dotted_ellipse(c, cx, cy, major_in=4.0, minor_in=3.5):
    """Draw a subtle, faint dotted ellipse (Kuiper belt) centered at (cx, cy).

    major_in: horizontal (major) axis diameter in inches
    minor_in: vertical (minor) axis diameter in inches
    """
    a = (major_in / 2.0) * inch      # horizontal semi-axis
    b = (minor_in / 2.0) * inch      # vertical semi-axis
    c.saveState()
    c.setStrokeColor(Color(0.45, 0.45, 0.45))  # medium gray, subtle but visible
    c.setLineWidth(0.6)                         # thin, still prints reliably
    c.setDash(1, 3)                             # small dots, moderate gaps
    c.ellipse(cx - a, cy - b, cx + a, cy + b, stroke=1, fill=0)
    c.restoreState()


def draw_sector_lines(c, cx, cy, inner_d=1.0, outer_d=2.5):
    """Draw radial spokes at 12, 3, 6, 9 o'clock.

    Each line runs from the Saturn orbit (inner_d) out to the Pluto orbit
    (outer_d), dividing the rings into four sectors.

    inner_d: diameter (inches) of the innermost circle to start from (Saturn)
    outer_d: diameter (inches) of the outermost circle to end at (Pluto)
    """
    r_inner = (inner_d / 2.0) * inch
    r_outer = (outer_d / 2.0) * inch

    # (dx, dy) unit directions for 12, 3, 6, 9 o'clock
    directions = [
        (0.0,  1.0),   # 12 o'clock (up)
        (1.0,  0.0),   # 3 o'clock (right)
        (0.0, -1.0),   # 6 o'clock (down)
        (-1.0, 0.0),   # 9 o'clock (left)
    ]

    c.saveState()
    c.setLineWidth(0.75)
    for dx, dy in directions:
        c.line(cx + dx * r_inner, cy + dy * r_inner,
               cx + dx * r_outer, cy + dy * r_outer)
    c.restoreState()


def draw_subsector_lines(c, cx, cy, inner_d=1.0, outer_d=2.5, n_divisions=32):
    """Draw evenly-spaced radial spokes dividing the rings into n_divisions.

    Angles start at 12 o'clock and step clockwise. With n_divisions=32 the
    four quadrants are each split into 8 subsectors (32 total). Uses the same
    line width as draw_sector_lines so the grid looks uniform.
    """
    r_inner = (inner_d / 2.0) * inch
    r_outer = (outer_d / 2.0) * inch
    step = 2.0 * math.pi / n_divisions      # radians between spokes

    c.saveState()
    c.setLineWidth(0.75)                     # same as the quadrant lines
    for i in range(n_divisions):
        theta = i * step                     # measured clockwise from 12 o'clock
        dx, dy = math.sin(theta), math.cos(theta)
        c.line(cx + dx * r_inner, cy + dy * r_inner,
               cx + dx * r_outer, cy + dy * r_outer)
    c.restoreState()


def draw_belt_rectangles(c, cx, cy, major_in=4.0, minor_in=3.5,
                         rect_w_in=1.25, rect_h_in=0.25,
                         gap_in=0.25, n=32):
    """Place n axis-aligned rectangles in two vertical columns around the belt.

    Layout rules (to eliminate the top/bottom overlaps):
    - Every rectangle stays horizontal (aligned to the page, never rotated).
    - Boxes are stacked at evenly-spaced vertical levels, so vertically
      adjacent boxes are close but never overlap.
    - Exactly 2 boxes sit at the very top and 2 at the very bottom; the rest
      fan outward down each side, hugging an ellipse that clears the belt.
    - The edge nearest the sun keeps `gap_in` of breathing room from the belt.

    major_in / minor_in: belt ellipse axis *diameters* in inches
    rect_w_in / rect_h_in: rectangle size in inches (W x H)
    gap_in: breathing room between the belt and the near edge of each box
    n: total number of rectangles (split evenly into two side columns)
    """
    a = (major_in / 2.0) * inch      # belt horizontal semi-axis
    b = (minor_in / 2.0) * inch      # belt vertical semi-axis
    w = (rect_w_in / 2.0) * inch     # rectangle half-width
    h = (rect_h_in / 2.0) * inch     # rectangle half-height
    gap = gap_in * inch

    # Placement ellipse for box CENTERS: sized so the near edge clears the belt
    # by `gap` both on the sides (horizontal) and at the top/bottom (vertical).
    A = a + gap + w                  # horizontal semi-axis for centers
    B = b + gap + h                  # vertical semi-axis for centers

    # Minimum horizontal offset so the 2 top / 2 bottom boxes never overlap.
    min_off = w + 0.075 * inch

    per_side = n // 2                # levels stacked from top to bottom
    c.saveState()
    # Match the Kuiper-belt ellipse style (medium gray, thin), but solid.
    c.setStrokeColor(Color(0.45, 0.45, 0.45))
    c.setLineWidth(0.6)
    # c.setDash(1, 3)               # dotted; uncomment this line for dotted
    for j in range(per_side):
        # evenly spaced vertical centers from top (+B) to bottom (-B)
        Y = B - j * (2.0 * B / (per_side - 1))
        ratio = max(0.0, 1.0 - (Y / B) ** 2)
        X = max(A * math.sqrt(ratio), min_off)   # hug ellipse; clamp at ends
        for sx in (1, -1):
            rx = cx + sx * X
            ry = cy + Y
            c.rect(rx - w, ry - h, 2 * w, 2 * h, stroke=1, fill=0)
    c.restoreState()


def draw_day_numbers(c, cx, cy, neptune_d=2.0, pluto_d=2.5, n=32,
                     font_name="Helvetica", font_size=9):
    """Print numbers 1..n, one per subsector, in the Neptune-Pluto band.

    - Numbering starts in the first subsector clockwise from 12 o'clock.
    - Each number is centered in its subsector wedge.
    - Numbers are oriented with their BOTTOM facing the sun (center), so the
      wheel reads correctly as you rotate the page.
    - Placed radially between the Neptune (inner) and Pluto (outer) orbits.
    """
    r_neptune = (neptune_d / 2.0) * inch
    r_pluto = (pluto_d / 2.0) * inch
    r_text = (r_neptune + r_pluto) / 2.0     # midpoint of the band

    step_deg = 360.0 / n                       # 11.25 deg for n=32
    for i in range(n):
        theta_deg = (i + 0.5) * step_deg       # center of the subsector
        c.saveState()
        c.translate(cx, cy)
        c.rotate(-theta_deg)                   # +y now points radially outward
        c.setFont(font_name, font_size)
        # vertical centering: shift baseline down by ~0.35 * font size
        c.drawCentredString(0, r_text - 0.35 * font_size, str(i + 1))
        c.restoreState()


def create_a5_concentric_circles(filename: str = "blank_a5_landscape.pdf") -> None:
    """Create a single-page landscape A5 PDF (210 x 148 mm) with 4
    concentric circles centered on the page.

    Diameters: 2.5", 2", 1.5", 1"
    """
    page_size = landscape(A5)
    width, height = page_size
    cx, cy = width / 2.0, height / 2.0

    c = canvas.Canvas(filename, pagesize=page_size)

    # --- Concentric circles (solid) ---
    diameters_in = [2.5, 2.0, 1.5, 1.0]
    for d in diameters_in:
        r = (d / 2.0) * inch          # radius in points
        c.circle(cx, cy, r, stroke=1, fill=0)

    # --- Dotted ellipse around the circles ---
    draw_dotted_ellipse(c, cx, cy, major_in=4.0, minor_in=3.5)

    # --- 32 subsector lines (each quadrant split into 8) from Saturn to Pluto ---
    draw_subsector_lines(c, cx, cy, inner_d=1.0, outer_d=2.5, n_divisions=32)

    # --- 32 horizontal rectangles just outside the Kuiper belt ---
    draw_belt_rectangles(c, cx, cy, major_in=4.0, minor_in=3.5,
                         rect_w_in=1.25, rect_h_in=0.25, gap_in=0.25, n=32)

    # --- Day numbers 1..32 in the Neptune-Pluto band, bottoms toward the sun ---
    draw_day_numbers(c, cx, cy, neptune_d=2.0, pluto_d=2.5, n=32)

    c.showPage()
    c.save()
    print(f"Created landscape A5 PDF with concentric circles: {filename}")


if __name__ == "__main__":
    create_a5_concentric_circles()
