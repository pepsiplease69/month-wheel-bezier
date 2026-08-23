#!/usr/bin/env python3
"""Create a landscape A5 PDF with 4 concentric circles centered on the page."""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.units import inch


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
    # Horizontal (major) axis = 4" diameter, vertical (minor) axis = 3.5" diameter
    a = (4.0 / 2.0) * inch            # horizontal semi-axis
    b = (3.5 / 2.0) * inch            # vertical semi-axis
    c.saveState()
    c.setDash(1, 3)                   # 1 pt dot, 3 pt gap
    c.ellipse(cx - a, cy - b, cx + a, cy + b, stroke=1, fill=0)
    c.restoreState()

    c.showPage()
    c.save()
    print(f"Created landscape A5 PDF with concentric circles: {filename}")


if __name__ == "__main__":
    create_a5_concentric_circles()
