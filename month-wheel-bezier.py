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

    c.showPage()
    c.save()
    print(f"Created landscape A5 PDF with concentric circles: {filename}")


if __name__ == "__main__":
    create_a5_concentric_circles()
