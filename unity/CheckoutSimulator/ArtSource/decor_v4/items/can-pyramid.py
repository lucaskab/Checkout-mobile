"""can-pyramid: promo pyramid of tin cans (colourful fruit labels, no text) on a navy display plinth with gold trim,
a brass pole with a hanging red '%' banner ("Anim Sway", pivot at the crossbar). Footprint half .50 x .40, height <= 1.5."""
import math, os, sys
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib_G as G

CONFIG = {"floor": "F4EFE4", "seed": 13}

CAN_R, CAN_H = .05, .135
PITCH = .107


def can(name, x, y, z, paint_):
    p = [(0, 0), (.043, 0), (.048, .003), (CAN_R, .008), (.0465, .014), (.0465, CAN_H - .014), (CAN_R, CAN_H - .008), (.048, CAN_H - .003),
         (.042, CAN_H), (.037, CAN_H - .004), (0, CAN_H - .004)]
    G.lathe_uv(name, p, seg=12, loc=(x, y, z), rot=(0, 0, RNG.uniform(-6, 6)), paint=paint_)


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.16, light=.36)
    navy = dv4.paint_flat("Plinth", "22345F", dark="131E3A", variation=.3, scale=5.0, edge="6C7FAE", edge_k=.8, edge_r=.008)
    gold = G.paint_brass("Gold", base="DDB244", dark="9C7A20", light="FFE9A0", hammered=.0)
    cream = dv4.paint_flat("Cream", "F4EFE4", dark="D9D0BF", variation=.2, scale=10.0)
    wood = dv4.paint_wood("Top", base="B9743F", dark="6B4128", light="DDA55F", scale=3.0, along="X")
    # ---- plinth: navy box with a gold skirting and a wooden top board
    dv4.cube("Plinth", (.64, .46, .12), loc=(0, 0, .06), paint=navy, bevel=.012, segs=2)
    dv4.cube("Skirt", (.66, .48, .025), loc=(0, 0, .0125), paint=gold, bevel=.006, segs=2)
    dv4.cube("TopBoard", (.66, .48, .02), loc=(0, 0, .13), paint=wood, bevel=.006, segs=2)
    dv4.cube("TrimF", (.62, .012, .04), loc=(0, .236, .085), paint=gold, bevel=.004, segs=1)
    # cream price-tag shaped card on the front (a pentagon tag with a hole): a bevelled slab + ring
    dv4.cube("Tag", (.16, .012, .11), loc=(.14, .236, .06), rot=(0, 0, 0), paint=cream, bevel=.012, segs=3)
    dv4.torus("TagHole", .012, .004, loc=(.14, .243, .095), rot=(90, 0, 0), seg=12, minor=5, paint=gold)
    dv4.cube("TagStripe", (.10, .004, .016), loc=(.14, .244, .045), paint=dv4.paint_flat("Red", "D74A3C", variation=.1), bevel=.003, segs=1)
    # ---- cans: 5x3, 4x2, 3x2, 2x1, 1  (tier colours: red / teal / gold / navy / orange)
    tiers = [
        (5, 3, dict(base="D74A3C", stripe="F4EFE4", fruit="F2B233", fruit_dark="D08A1C", leaf="4E9A3C")),      # peach
        (4, 2, dict(base="1F9A8E", stripe="F4EFE4", fruit="E03B33", fruit_dark="A8231F", leaf="3E8F34")),      # tomato
        (3, 2, dict(base="E0B040", stripe="1D2B4F", fruit="7FC242", fruit_dark="4E8A28", leaf="2F6F2C")),      # pear
        (2, 1, dict(base="1D2B4F", stripe="E0B040", fruit="EC862E", fruit_dark="B85E14", leaf="4E9A3C")),      # orange
        (1, 1, dict(base="EC862E", stripe="F4EFE4", fruit="8A4FB0", fruit_dark="5A2E7A", leaf="3E8F34")),      # plum
    ]
    z = .14
    for t, (nx, ny, cols) in enumerate(tiers):
        lp = G.paint_label("Label%d" % t, r=CAN_R, h=CAN_H, **cols)
        for i in range(nx):
            for j in range(ny):
                if t == 0 and 0 < i < nx - 1 and 0 < j < ny - 1:
                    continue        # hidden interior cans
                x = (i - (nx - 1) / 2) * PITCH + RNG.uniform(-.003, .003)
                y = (j - (ny - 1) / 2) * PITCH + .02 + RNG.uniform(-.003, .003)
                can("Can%d_%d_%d" % (t, i, j), x, y, z, lp)
        z += CAN_H
    # ---- brass pole at the back-left with a ball finial, crossbar and the hanging '%' banner
    px, py = -.27, -.19
    dv4.lathe("PoleBase", [(0, .14), (.05, .14), (.052, .15), (.04, .165), (.016, .17), (0, .17)], seg=16, loc=(px, py, 0), paint=gold)
    dv4.tube("Pole", [(px, py, .16), (px, py, 1.3)], radius=.011, res=8, paint=gold, kind="POLY", resolution=1)
    dv4.sphere("Finial", .024, loc=(px, py, 1.325), seg=12, rings=8, paint=gold)
    dv4.torus("PoleRing", .016, .006, loc=(px, py, 1.29), seg=12, minor=5, paint=gold)
    bar_z = 1.24
    dv4.tube("CrossBar", [(px + .01, py, bar_z), (px + .35, py, bar_z)], radius=.007, res=6, paint=gold, kind="POLY", resolution=1)
    dv4.sphere("BarEnd", .012, loc=(px + .35, py, bar_z), seg=8, rings=6, paint=gold)
    sway = "Anim Sway"; dv4.pivot(sway, (px + .19, py, bar_z))
    banner_p = G.paint_percent("Banner", base="D74A3C", ink="F4EFE4")
    G.flag("Banner", .30, .36, loc=(px + .19, py, bar_z - .004), paint=banner_p, out=sway, nx=8, ny=10, swallow=.35, wave=.015)
    for k in range(3):
        dv4.torus("Loop%d" % k, .012, .003, loc=(px + .06 + k * .13, py, bar_z), rot=(0, 90, 0), seg=10, minor=4, paint=gold, out=sway)
    return {"name": "CanPyramid", "tex": 1024, "budget": 10000, "floor": "F4EFE4"}
