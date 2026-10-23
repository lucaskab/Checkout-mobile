"""street-lamp: ornate Victorian cast-iron lamp post with a glowing four-sided lantern, gold bands, a post-mounted
flower collar with trailing petunias and two pennant banners (star / heart pictograms) swaying from a crossbar.
Footprint half .24 x .24, height <= 3.9 (Blender Z up, front +Y)."""
import math
import sys, os
import dv4
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_E as E
from dv4 import RNG

CONFIG = {"floor": "C9C3B8", "seed": 23}


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.2, light=.38)
    iron = dv4.paint_iron("Iron", base="1E2733", mid="39454F", edge="9EA9B2", rust="7A4423", rust_amt=.25)
    gold = dv4.paint_gold("Gold")
    navy = E.paint_painted("Navy", dv4.NAVY, light="7F94C8", dark="0B1226", variation=.15)
    soil = dv4.paint_soil("Soil")
    leafp = dv4.paint_leaf("Leaf", base="3E8E3B", dark="1E5A2A", light="86C654", veins=4)
    ivyp = dv4.paint_leaf("Ivy", base="2F7A33", dark="174A20", light="6DB84A", vein="A8DB8C", veins=4)
    stemp = dv4.paint_flat("Stem", "4E8A34", "2E5A24", variation=.3)
    throat = dv4.paint_flat("Throat", "5A1F3A", "2A0C1A", variation=.2)
    pink = E.paint_petal("PetalPink", "EE8FAE", "C2567E", "FFC6D8")
    purple = E.paint_petal("PetalPurple", "8E6CCF", "5A3E96", "C7AEF0")
    white = E.paint_petal("PetalWhite", "FBF8F1", "C9BFAE", "FFFFFF")
    red_cloth = E.paint_fabric("ClothRed", dv4.RED, "8E2A20", "FF8C7A")
    teal_cloth = E.paint_fabric("ClothTeal", dv4.TEAL, "0E5048", "8FE0D6")
    cream_cloth = E.paint_fabric("ClothCream", dv4.CREAM, "C9BFAE", "FFFFFF")

    # ---- fluted base and tapered post with gold bands
    base = [(0, 0), (.215, 0), (.235, .015), (.235, .06), (.20, .085), (.16, .11), (.125, .20), (.10, .34), (.082, .46), (.078, .52), (.062, .56), (0, .56)]
    dv4.lathe("Base", base, seg=28, paint=iron, scallop=(14, .045))
    dv4.torus("BaseRing", .082, .016, loc=(0, 0, .47), seg=24, minor=7, paint=gold)
    dv4.tube("Post", [(0, 0, .54), (0, 0, 1.8), (0, 0, 3.12)], radius=.046, res=12, paint=iron, resolution=2, taper=[(0, 1.0), (1, .8)])
    for z, r in ((.95, .058), (2.25, .052), (2.95, .05)):
        dv4.torus("Band", r, .014, loc=(0, 0, z), seg=20, minor=7, paint=gold)
    # ---- flower collar around the post (navy pot with a gold lip), petunias and trailing ivy
    collar = [(.05, 1.42), (.16, 1.42), (.20, 1.46), (.225, 1.55), (.24, 1.60), (.225, 1.63), (.185, 1.63), (.18, 1.60), (.05, 1.60), (.05, 1.42)]
    dv4.lathe("Collar", collar, seg=32, paint=navy, cap=False)
    dv4.torus("CollarLip", .215, .014, loc=(0, 0, 1.635), seg=32, minor=6, paint=gold)
    dv4.lathe("CollarSoil", [(.05, 1.60), (.12, 1.615), (.19, 1.60)], seg=24, paint=soil, cap=False)
    pets = (pink, purple, white)
    for i in range(10):
        a = math.radians(i * 36 + RNG.uniform(-8, 8))
        r = RNG.uniform(.09, .13)
        x, y = math.cos(a) * r, math.sin(a) * r
        h = RNG.uniform(.08, .13)
        top = (x * 1.2, y * 1.2, 1.61 + h)
        E.stem("CS%d" % i, (x, y, 1.60), top, stemp, radius=.006)
        E.petunia("CP%d" % i, .055, top, pets[i % 3], throat,
                  rot=(RNG.uniform(25, 45), 0, math.degrees(a) + 90 + RNG.uniform(-10, 10)))
    for i in range(12):
        a = math.radians(i * 30 + RNG.uniform(-8, 8))
        x, y = math.cos(a) * .19, math.sin(a) * .19
        dv4.leaf("CI%d" % i, RNG.uniform(.09, .12), .085, loc=(x, y, 1.64), rot=(RNG.uniform(135, 160), 0, math.degrees(a) - 90 + RNG.uniform(-25, 25)),
                 paint=ivyp, shape="heart", bend=.25, cup=.1, thickness=.003, nl=3, nw=2)
    for i in range(6):
        a = math.radians(i * 60 + 15)
        dv4.leaf("CL%d" % i, .09, .06, loc=(math.cos(a) * .12, math.sin(a) * .12, 1.61), rot=(50, 0, math.degrees(a) - 90), paint=leafp,
                 shape="spade", bend=.3, cup=.15, thickness=.003, nl=3, nw=2)
    # ---- crossbar with ball finials; the pennants hang from it (Anim Sway)
    dv4.tube("CrossBar", [(-.215, 0, 2.42), (.215, 0, 2.42)], radius=.016, res=8, paint=iron, kind="POLY", resolution=1)
    for sx in (-1, 1):
        dv4.sphere("BarBall", .026, loc=(sx * .222, 0, 2.42), seg=10, rings=6, paint=gold)
    for sx in (-1, 1):
        s = [(sx * .03, 0, 2.42)] + dv4.spiral((sx * .07, 0, 2.33), .09, .018, .9, 11, a0=math.radians(90 if sx > 0 else 90), plane="XZ", ccw=sx < 0)[1:]
        dv4.tube("BarScroll%d" % sx, s, radius=.012, res=6, paint=iron, resolution=3)
    sway = "Anim Sway"; dv4.pivot(sway, (0, 0, 2.42))
    for sx, cloth, kind in ((-1, red_cloth, "star"), (1, teal_cloth, "heart")):
        cx = sx * .125
        w, h = .19, .34
        pts = [(-w / 2, 0), (w / 2, 0), (w / 2, -h * .7), (0, -h), (-w / 2, -h * .7)]
        pts.reverse()
        E.flat_shape("Pennant%d" % sx, pts, depth=.012, loc=(cx, 0, 2.40), rot=(90, 0, 0), paint=cloth, out=sway)
        for dx in (-w / 2 + .025, w / 2 - .025):
            dv4.torus("Ring%d" % sx, .012, .004, loc=(cx + dx, 0, 2.415), rot=(0, 90, 0), seg=10, minor=5, paint=gold, out=sway)
        shape = E.star_pts(.058, .024) if kind == "star" else E.heart_pts(.052)
        E.flat_shape("Icon%d" % sx, shape, depth=.01, loc=(cx, .012, 2.40 - h * .40), rot=(90, 0, 0), paint=cream_cloth if kind == "heart" else gold, out=sway)
    # ---- lantern: collar, four scroll brackets, square tapered glass, iron frame, pyramid roof, finial
    dv4.lathe("TopCollar", [(.04, 3.10), (.075, 3.10), (.085, 3.13), (.085, 3.18), (.06, 3.21), (.04, 3.21)], seg=16, paint=iron)
    for i in range(4):
        a = i * 90 + 45
        rot = (0, 0, a)
        s = [(0, 0, 2.98)] + dv4.spiral((.0, .10, 3.08), .085, .015, .8, 10, a0=math.radians(-100), plane="YZ", ccw=True)[1:]
        dv4.tube("Scroll%d" % i, s, radius=.011, res=6, paint=iron, resolution=3, rot=rot)
    dv4.lathe("LanternBase", [(0, 3.19), (.16, 3.19), (.175, 3.215), (.175, 3.245), (.145, 3.26), (0, 3.26)], seg=4, rot=(0, 0, 45), paint=iron)
    dv4.lathe("Glass", [(0, 3.26), (.125, 3.26), (.165, 3.58), (0, 3.58)], seg=4, rot=(0, 0, 45), paint=None, mat_override="E_FFE3A0")
    for i in range(4):
        a = math.radians(i * 90 + 45)
        c, s = math.cos(a), math.sin(a)
        dv4.tube("Edge%d" % i, [(c * .13, s * .13, 3.25), (c * .17, s * .17, 3.59)], radius=.012, res=6, paint=iron, kind="POLY", resolution=1)
    dv4.lathe("Rim", [(.19, 3.58), (.195, 3.60), (.185, 3.635), (.17, 3.635)], seg=4, rot=(0, 0, 45), paint=iron, cap=False)
    dv4.lathe("Roof", [(0, 3.59), (.175, 3.59), (.20, 3.61), (.125, 3.70), (.06, 3.76), (.04, 3.79), (0, 3.80)], seg=4, rot=(0, 0, 45), paint=iron)
    dv4.lathe("RoofCap", [(.03, 3.78), (.055, 3.78), (.055, 3.81), (.03, 3.82)], seg=12, paint=gold)
    dv4.sphere("Finial", .038, loc=(0, 0, 3.84), seg=12, rings=8, paint=gold)
    dv4.lathe("Spike", [(0, 3.86), (.014, 3.86), (0, 3.90)], seg=8, paint=gold)
    return {"name": "StreetLamp", "tex": 1024, "budget": 10000, "floor": "C9C3B8"}
