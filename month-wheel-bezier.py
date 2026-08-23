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
    """Place n axis-aligned rectangles around the Kuiper-belt ellipse.

    - Each rectangle is horizontal (aligned to the page, never rotated).
    - One rectangle is centered in each subsector wedge.
    - The side/corner nearest the sun clears the belt by `gap_in` (measured
      radially), so every box has the same breathing room from the ellipse.

    major_in / minor_in: belt ellipse axis *diameters* in inches
    rect_w_in / rect_h_in: rectangle size in inches (W x H)
    gap_in: breathing room between the belt and the inner edge of each box
    n: number of rectangles (one per subsector)
    """
    a = (major_in / 2.0) * inch      # belt horizontal semi-axis
    b = (minor_in / 2.0) * inch      # belt vertical semi-axis
    w = (rect_w_in / 2.0) * inch     # rectangle half-width
    h = (rect_h_in / 2.0) * inch     # rectangle half-height
    gap = gap_in * inch

    step = 2.0 * math.pi / n
    c.saveState()
    c.setLineWidth(0.75)
    for i in range(n):
        theta = (i + 0.5) * step             # center of each subsector wedge
        dx, dy = math.sin(theta), math.cos(theta)

        # distance from center to the belt along this radial direction
        t_belt = 1.0 / math.sqrt((dx / a) ** 2 + (dy / b) ** 2)

        # push out so the box's near edge clears the belt by `gap`;
        # |dx|*w + |dy|*h is the rectangle's half-extent along the radial axis
        d = t_belt + gap + abs(dx) * w + abs(dy) * h

        rx = cx + d * dx
        ry = cy + d * dy
        c.rect(rx - w, ry - h, 2 * w, 2 * h, stroke=1, fill=0)
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

    c.showPage()
    c.save()
    print(f"Created landscape A5 PDF with concentric circles: {filename}")


if __name__ == "__main__":
    create_a5_concentric_circles()
