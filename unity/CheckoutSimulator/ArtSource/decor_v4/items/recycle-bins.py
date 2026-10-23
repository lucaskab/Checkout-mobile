"""recycle-bins: four colour-coded rounded bins (paper / plastic / glass / metal) with lids, flap and pictogram badges, on a
stone slab under a small teal shed roof carrying a big recycling-arrows symbol. Footprint half .80 x .24, height <= 1.3."""
import math
import sys, os
import dv4
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_E as E
from dv4 import RNG

CONFIG = {"floor": "C9C3B8", "seed": 25}

BINS = [  # (x, colour, light, dark, icon)
    (-.555, "2E86DE", "8EC4F5", "174A86", "paper"),
    (-.185, "D74A3C", "FFA69A", "7E1F16", "plastic"),
    (.185, "5DA637", "A8E07C", "2C6018", "glass"),
    (.555, "F2C23F", "FFE9A0", "A87A0E", "metal"),
]


def icon_shapes(kind, s=1.0):
    """List of (points, dz) flat polygons in a 0.16 x 0.16 box (local XY, +Z normal), stacked by dz."""
    if kind == "paper":      # two overlapping sheets with a folded corner
        sheet = [(-.045, -.06), (.03, -.06), (.045, -.045), (.045, .06), (-.045, .06)]
        return [([(x - .015, y - .012) for x, y in sheet], 0.0), ([(x + .015, y + .012) for x, y in sheet], .006)]
    if kind == "plastic":    # bottle silhouette
        pts = [(-.028, -.07), (.028, -.07), (.034, -.06), (.034, .0), (.026, .02), (.014, .035), (.014, .055), (.02, .06), (.02, .07),
               (-.02, .07), (-.02, .06), (-.014, .055), (-.014, .035), (-.026, .02), (-.034, .0), (-.034, -.06)]
        return [(pts, 0.0)]
    if kind == "glass":      # wine bottle and a tumbler
        bottle = [(-.02, -.07), (.02, -.07), (.024, -.06), (.024, .0), (.012, .025), (.012, .06), (.016, .065), (.016, .072), (-.016, .072),
                  (-.016, .065), (-.012, .06), (-.012, .025), (-.024, .0), (-.024, -.06)]
        glass = [(.03, -.07), (.072, -.07), (.066, -.01), (.036, -.01)]
        return [([(x - .022, y) for x, y in bottle], 0.0), (glass, 0.0)]
    # metal: tin can with rim lines
    can = E.rounded_rect_pts(.08, .13, .012, 3)
    return [(can, 0.0), (E.rounded_rect_pts(.086, .018, .006, 2), .006), ([(x, y - .06) for x, y in E.rounded_rect_pts(.086, .018, .006, 2)], .006)]


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.2, light=.38)
    slab = dv4.paint_stone("Slab", base="8E8780", dark="5E5852", light="B3ACA3", moss_amt=.3)
    navy = E.paint_painted("Navy", dv4.NAVY, light="7F94C8", dark="0B1226", variation=.15)
    teal = E.paint_painted("Roof", dv4.TEAL, light="9FE6DC", dark="0E5048", variation=.15)
    creamp = E.paint_painted("Cream", dv4.CREAM, light="FFFFFF", dark="C9BFAE", variation=.1)
    dark = dv4.paint_iron("Dark", base="262B30", mid="3B434A", edge="8A949C", rust_amt=.0)
    gold = dv4.paint_gold("Gold")

    # ---- stone slab and the shed roof on four navy posts
    dv4.cube("Slab", (1.52, .44, .05), loc=(0, 0, .025), paint=slab, bevel=.012, segs=2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            dv4.tube("Post", [(sx * .70, sy * .165, .04), (sx * .70, sy * .165, 1.18 + sy * .04)], radius=.022, res=10, paint=navy, kind="POLY", resolution=1)
            dv4.sphere("PostCap", .03, loc=(sx * .70, sy * .165, 1.18 + sy * .04), seg=10, rings=6, paint=gold)
    pitch = -9
    dv4.cube("Roof", (1.56, .44, .035), loc=(0, 0, 1.215), rot=(pitch, 0, 0), paint=teal, bevel=.01, segs=2)
    dv4.cube("RoofEdge", (1.58, .045, .07), loc=(0, .215, 1.23), rot=(pitch, 0, 0), paint=creamp, bevel=.012, segs=2)
    dv4.cube("RoofEdgeB", (1.58, .045, .07), loc=(0, -.215, 1.16), rot=(pitch, 0, 0), paint=creamp, bevel=.012, segs=2)
    dv4.tube("Beam", [(-.70, .165, 1.14), (.70, .165, 1.14)], radius=.02, res=8, paint=navy, kind="POLY", resolution=1)
    dv4.tube("BeamB", [(-.70, -.165, 1.07), (.70, -.165, 1.07)], radius=.02, res=8, paint=navy, kind="POLY", resolution=1)
    # big recycling symbol on the roof top: cream disc badge with navy arrows (readable from the game camera)
    dv4.cylinder("RoofBadge", .21, .014, loc=(0, 0, 1.228), rot=(pitch, 0, 0), seg=32, paint=creamp, bevel=.004)
    for i in range(3):
        E.bent_arrow("Arrow%d" % i, (0, 0), .125, 8 + i * 120, 92 + i * 120, .042, .02, navy, loc=(0, 0, 1.246), rot=(pitch, 0, 0), head=1.55, n=7, tip_k=1.0)

    # ---- bins
    for x, col, light, dk, icon in BINS:
        body = E.paint_painted("Bin" + icon, col, light=light, dark=dk, variation=.12, sheen=.15)
        darkp = E.paint_painted("Lid" + icon, dk, light=col, dark="000000", variation=.12, sheen=.1)
        dv4.cube("Body" + icon, (.33, .32, .70), loc=(x, 0, .05 + .35), paint=body, bevel=.045, segs=3)
        dv4.cube("Base" + icon, (.29, .28, .04), loc=(x, 0, .05 + .02), paint=darkp, bevel=.01, segs=1)
        dv4.cube("Lid" + icon, (.35, .34, .07), loc=(x, 0, .75 + .035), paint=darkp, bevel=.03, segs=3)
        dv4.cube("LidTop" + icon, (.29, .26, .04), loc=(x, 0, .82 + .015), paint=body, bevel=.018, segs=2)
        # swing flap on the front of the lid (slightly open) and a handle bar on top
        dv4.cube("Flap" + icon, (.22, .025, .10), loc=(x, .18, .735), rot=(-22, 0, 0), paint=darkp, bevel=.008, segs=1)
        dv4.tube("Handle" + icon, [(x - .07, -.09, .84), (x - .07, -.09, .875), (x + .07, -.09, .875), (x + .07, -.09, .84)], radius=.009, res=6, paint=dark, resolution=2)
        # front badge: cream rounded plate with the pictogram in the bin's dark shade
        dv4.cube("Badge" + icon, (.24, .012, .24), loc=(x, .16, .42), paint=creamp, bevel=.03, segs=2)
        for pts, dz in icon_shapes(icon):
            E.flat_shape("Icon" + icon + str(dz), [(px * 1.35, py * 1.35) for px, py in pts], depth=.014, loc=(x, .166 + dz, .42), rot=(90, 0, 0), paint=darkp)
        # the same pictogram, small, on the lid top
        for pts, dz in icon_shapes(icon):
            E.flat_shape("LidIcon" + icon + str(dz), [(px * .8, py * .8) for px, py in pts], depth=.012, loc=(x, .015, .84 + dz), rot=(0, 0, 0), paint=creamp)
    return {"name": "RecycleBins", "tex": 1024, "budget": 10000, "floor": "C9C3B8"}
