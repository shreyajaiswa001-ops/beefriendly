"""
BeeFriendly — make_logo.py
Renders assets/logo.png (app icon & sidebar logo) — a cute, small,
kawaii-style bee matching logo.svg. Run once:

    python make_logo.py
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, Ellipse, Polygon, Rectangle
from matplotlib.transforms import Affine2D

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
OUT = os.path.join(ASSETS, "logo.png")


def main() -> None:
    fig, ax = plt.subplots(figsize=(4.8, 4.8), dpi=100)
    ax.set_xlim(0, 240)
    ax.set_ylim(240, 0)          # invert y so SVG-style coords match
    ax.set_aspect("equal")
    ax.axis("off")

    # ---- badge ring (pink → amber → blue feel) ----------------------
    ax.add_patch(Circle((120, 120), 112, color="#DB2777"))
    ax.add_patch(Circle((120, 120), 108, color="#EC4899"))
    ax.add_patch(Circle((120, 120), 104, color="#3B82F6"))
    ax.add_patch(Circle((120, 120), 101, color="#FFFFFF"))

    def wing(cx, angle, color):
        t = Affine2D().rotate_deg_around(cx, 88, angle) + ax.transData
        ax.add_patch(Ellipse((cx, 88), 52, 30, facecolor=color,
                             edgecolor="none", alpha=0.95, transform=t))

    wing(92, -28, "#BFDBFE")
    wing(148, 28, "#DBEAFE")

    # ---- antennae -----------------------------------------------------
    ax.plot([106, 100, 90], [100, 86, 82], color="#78350F",
            lw=5, solid_capstyle="round")
    ax.plot([134, 140, 150], [100, 86, 82], color="#78350F",
            lw=5, solid_capstyle="round")
    for tx in (88, 152):
        ax.add_patch(Circle((tx, 80), 6, facecolor="#F59E0B",
                            edgecolor="#78350F", lw=3))

    # ---- small plump body ----------------------------------------------
    ax.add_patch(Ellipse((120, 140), 80, 88, facecolor="#FFD166",
                         edgecolor="#78350F", lw=5))
    clip = Ellipse((120, 140), 80, 88, transform=ax.transData)
    ax.add_patch(clip)

    # stripes drawn as clipped rectangles
    for y in (146, 170):
        rect = Rectangle((74, y), 92, 13, facecolor="#78350F",
                         edgecolor="none", transform=ax.transData)
        rect.set_clip_path(clip)
        ax.add_patch(rect)

    # ---- big kawaii eyes with shine -------------------------------------
    for ex in (104, 136):
        ax.add_patch(Circle((ex, 126), 10, color="#111827"))
        ax.add_patch(Circle((ex - 3.5, 122.5), 3.2, color="#FFFFFF"))

    # ---- pink blush cheeks ------------------------------------------------
    for bx in (94, 146):
        ax.add_patch(Ellipse((bx, 136), 15, 9, facecolor="#FB7185",
                             edgecolor="none", alpha=0.75))

    # ---- tiny happy smile ---------------------------------------------------
    smile = Arc((120, 128), 22, 14, theta1=200, theta2=340,
                edgecolor="#7C2D12", lw=4)
    ax.add_patch(smile)

    # ---- tiny stinger ---------------------------------------------------------
    ax.add_patch(Polygon([[114, 184], [126, 184], [120, 196]],
                         closed=True, facecolor="#78350F"))

    fig.savefig(OUT, transparent=True, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    print(f"Logo written to: {OUT}")


if __name__ == "__main__":
    main()
