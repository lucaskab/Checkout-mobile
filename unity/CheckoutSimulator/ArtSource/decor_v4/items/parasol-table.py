"""parasol-table: round marble bistro table on a cast-iron tripod pedestal, three teal bentwood-style bistro chairs, a big
orange & cream striped parasol with scalloped valance and visible ribs, a vase of flowers (swaying), cups and cookies.
Footprint half 1.0 x 1.0, height <= 2.7 (Blender: front = +Y, Z up)."""
import math
import dv4
from dv4 import RNG
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib_F as F

CONFIG = {"floor": "C9C3B8", "seed": 23}
ORANGE, CREAM, TEAL, GOLD = "EC862E", "F4EFE4", "1F9A8E", "E0B040"


def chair(prefix, cx, cy, face, teal, wood, chrome):
    """Bistro chair centred at (cx, cy), seat facing angle `face` (degrees, 90 = towards +Y)."""
    ca, sa = math.cos(math.radians(face - 90)), math.sin(math.radians(face - 90))
    def T(p):      # chair local: +Y = front of the chair
        x, y, z = p
        return (cx + x * ca - y * sa, cy + x * sa + y * ca, z)
    SZ = .46
    # seat: domed wooden disc with a rolled steel rim
    dv4.lathe(prefix + "Seat", [(0, SZ - .012), (.19, SZ - .012), (.205, SZ - .005), (.205, SZ + .008), (.18, SZ + .02), (.1, SZ + .028), (0, SZ + .03)],
              seg=24, loc=(cx, cy, 0), paint=wood)
    dv4.torus(prefix + "SeatRim", .205, .009, loc=(cx, cy, SZ), seg=24, minor=6, paint=teal)
    # four legs curving outward, with a ring stretcher
    for i, (lx, ly) in enumerate(((-.15, .15), (.15, .15), (-.15, -.15), (.15, -.15))):
        pts = [T((lx * .95, ly * .95, SZ - .01)), T((lx * 1.1, ly * 1.1, .28)), T((lx * 1.25, ly * 1.25, .0))]
        dv4.tube(prefix + "Leg%d" % i, pts, radius=.012, res=8, paint=teal, resolution=3)
        dv4.sphere(prefix + "Foot%d" % i, .016, loc=T((lx * 1.25, ly * 1.25, .012)), seg=8, rings=5, paint=chrome, scale=(1, 1, .7))
    dv4.torus(prefix + "Ring", .17, .007, loc=(cx, cy, .22), seg=20, minor=5, paint=teal)
    # hoop backrest + two curved slats
    hoop = [T((-.17, -.14, SZ - .01)), T((-.2, -.2, .70)), T((-.17, -.24, .90)), T((0, -.25, .98)), T((.17, -.24, .90)), T((.2, -.2, .70)), T((.17, -.14, SZ - .01))]
    dv4.tube(prefix + "Hoop", hoop, radius=.012, res=8, paint=teal, resolution=4)
    for i, sx in enumerate((-.06, .06)):
        dv4.tube(prefix + "Slat%d" % i, [T((sx, -.17, SZ + .02)), T((sx * 1.1, -.215, .75)), T((sx * 1.2, -.245, .93))], radius=.011, res=6, paint=wood, resolution=3)
    dv4.tube(prefix + "Brace", [T((-.19, -.19, .66)), T((0, -.215, .66)), T((.19, -.19, .66))], radius=.008, res=6, paint=teal, resolution=3)


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.25, light=.36)
    iron = dv4.paint_iron("Iron", base="1E252C", mid="39434C", edge="98A3AB", rust_amt=.2)
    teal = F.paint_enamel("Teal", TEAL, dark="0E5A53", light="8ADFD3", variation=.14, scratch=.08)
    wood = dv4.paint_wood("Wood", base="C98B4E", dark="7A4F2A", light="E8B870", scale=6.0, along="X", edge="F0CB8A", tint=.25)
    marble = F.paint_marble("Marble")
    brass = F.paint_brass("Brass")
    chrome = F.paint_chrome("Chrome")
    para = F.paint_stripes_radial("Parasol", [ORANGE, CREAM], 16, center=(0, 0), dark="5A2A10")
    cream = F.paint_enamel("Cream", "FBF8F1", dark="C9C2B6", light="FFFFFF", variation=.08, scratch=0.0, hl=.25)
    glaze = dv4.paint_terracotta("Vase", base="D9B48C", dark="A98257", glaze="D74A3C", glaze_light="F07A6A", glaze_z=.80, drip=.03)
    leaf = dv4.paint_leaf("Leaf", base="3F8F3A", dark="23602A", light="8CCB55", veins=5)
    petal = F.paint_petal("Petal", ["F2B33D", "EE8FAE", "F45B5B", "FFF1C4"], dark="7A3A2A")
    cookie = F.paint_waffle("Cookie", base="C98B4E", dark="8B5A2B", light="E8B870", scale=70.0)
    coffee = dv4.paint_flat("Coffee", "4A2A14", dark="2A160A", variation=.2, k_light=.1)

    # ---------------------------------------------------------------- table: tripod cast-iron pedestal, marble top with brass edge
    for i in range(3):
        a = math.radians(90 + i * 120)
        c, s = math.cos(a), math.sin(a)
        pts = [(0, 0, .16), (.12 * c, .12 * s, .09), (.26 * c, .26 * s, .03), (.33 * c, .33 * s, .035)]
        dv4.tube("PedLeg%d" % i, pts, radius=.024, res=8, paint=iron, resolution=4, taper=[(0, 1.0), (.7, .9), (1, .55)])
        dv4.sphere("PedToe%d" % i, .03, loc=(.33 * c, .33 * s, .03), seg=10, rings=6, paint=iron, scale=(1.2, 1, .9))
    dv4.lathe("Column", [(0, .12), (.07, .12), (.075, .15), (.05, .19), (.04, .25), (.04, .50), (.045, .58), (.06, .64), (.09, .67), (.11, .69), (0, .69)],
              seg=22, paint=iron)
    dv4.torus("ColRing", .048, .012, loc=(0, 0, .40), seg=12, minor=5, paint=brass)
    dv4.torus("ColRing2", .07, .012, loc=(0, 0, .17), seg=12, minor=5, paint=iron)
    TZ = .70
    dv4.lathe("Top", [(0, TZ), (.355, TZ), (.36, TZ + .01), (.36, TZ + .035), (.355, TZ + .045), (0, TZ + .045)], seg=40, paint=marble)
    dv4.torus("TopEdge", .36, .012, loc=(0, 0, TZ + .022), seg=32, minor=5, paint=brass)

    # ---------------------------------------------------------------- chairs
    for i, (cx, cy) in enumerate(((-.62, .46), (.62, .46), (0, -.74))):
        face = math.degrees(math.atan2(-cy, -cx))
        chair("C%d" % i, cx, cy, face, teal, wood, chrome)

    # ---------------------------------------------------------------- parasol
    PZ = 1.98
    R = .96
    dv4.tube("Pole", [(0, 0, .60), (0, 0, PZ + .36)], radius=.02, res=10, paint=chrome, kind="POLY", resolution=1)
    dv4.lathe("PoleCollar", [(.03, 0), (.045, .01), (.045, .05), (.03, .06)], seg=16, loc=(0, 0, TZ + .045), paint=brass, cap=False)
    dv4.torus("PoleRing", .028, .01, loc=(0, 0, 1.55), seg=14, minor=6, paint=brass)
    prof = []
    for i in range(8):
        t = i / 7
        r = R * (1 - t)
        z = PZ + .38 * (1 - (1 - t) ** 2) ** .9
        prof.append((r, z))
    prof[-1] = (0.0, PZ + .38)
    can = dv4.lathe("Canopy", prof, seg=40, paint=para, cap=False, scallop=(16, .03))
    F.scallop_ring("Valance", 0, 0, R + .005, 16, .10, PZ + .002, para, thickness=0, flare=.012, segs_per=4)
    for j in range(16):
        a = 2 * math.pi * j / 16
        pts = []
        for i in range(0, 6):
            r, z = prof[i]
            rr = r * (1 + .03 * math.cos(16 * a))
            pts.append((math.cos(a) * rr, math.sin(a) * rr, z - .009))
        dv4.tube("Rib%d" % j, pts[::-1], radius=.008, res=4, paint=chrome, kind="POLY", resolution=1)
        dv4.sphere("RibTip%d" % j, .015, loc=pts[0], seg=5, rings=3, paint=brass)
        # runner struts from the pole ring up to the middle of each rib
        dv4.tube("Strut%d" % j, [(0, 0, PZ + .10), pts[3]], radius=.006, res=5, paint=chrome, kind="POLY", resolution=1)
    dv4.torus("Runner", .032, .012, loc=(0, 0, PZ + .10), seg=14, minor=6, paint=chrome)
    dv4.lathe("Finial", [(0, 0), (.04, 0), (.045, .015), (.028, .045), (.014, .08), (.014, .11), (0, .11)], seg=14, loc=(0, 0, PZ + .36), paint=brass)
    dv4.sphere("FinialBall", .034, loc=(0, 0, PZ + .49), seg=12, rings=8, paint=brass)

    # ---------------------------------------------------------------- on the table: vase with flowers (sway), cups, cookies
    VX, VY = -.02, -.08
    dv4.lathe("Vase", [(0, 0), (.04, 0), (.05, .01), (.055, .06), (.04, .11), (.03, .14), (.035, .16), (.032, .162), (.024, .14), (0, .13)],
              seg=18, loc=(VX, VY, TZ + .045), paint=glaze)
    sway = "Anim Sway"; dv4.pivot(sway, (VX, VY, TZ + .20))
    for i in range(5):
        a = i * 1.26 + .4
        lean = .05 + RNG.uniform(0, .03)
        tip = (VX + math.cos(a) * lean * 1.6, VY + math.sin(a) * lean * 1.6, TZ + .20 + RNG.uniform(.13, .20))
        dv4.tube("Stem%d" % i, [(VX, VY, TZ + .18), (VX + math.cos(a) * lean, VY + math.sin(a) * lean, TZ + .30), tip], radius=.004, res=5, paint=leaf, out=sway, resolution=3)
        for k in range(5):
            b = k * 2 * math.pi / 5
            dv4.sphere("Petal%d%d" % (i, k), .018, loc=(tip[0] + math.cos(b) * .02, tip[1] + math.sin(b) * .02, tip[2] + .004),
                       seg=6, rings=3, paint=petal, out=sway, scale=(1.2, 1.2, .55), rot=(0, 0, math.degrees(b)))
        dv4.sphere("Heart%d" % i, .011, loc=(tip[0], tip[1], tip[2] + .014), seg=6, rings=3, paint=cookie, out=sway)
        dv4.leaf("Leaf%d" % i, .06, .03, loc=(VX + math.cos(a) * lean * .8, VY + math.sin(a) * lean * .8, TZ + .26), rot=(50, 0, math.degrees(a) - 90 + 40),
                 paint=leaf, out=sway, shape="spade", bend=.3, cup=.2, thickness=.003, nl=4, nw=2)
    for i, (cx, cy) in enumerate(((.17, .13), (-.2, .14))):
        dv4.lathe("Saucer%d" % i, [(0, 0), (.065, 0), (.07, .006), (.072, .012), (.06, .012), (.05, .006), (0, .006)], seg=14, loc=(cx, cy, TZ + .045), paint=cream)
        dv4.lathe("Cup%d" % i, [(0, 0), (.032, 0), (.037, .008), (.04, .05), (.042, .058), (.04, .06), (.036, .06), (.034, .05), (0, .05)], seg=14, loc=(cx, cy, TZ + .055), paint=cream)
        dv4.lathe("CupCoffee%d" % i, [(0, 0), (.034, 0)], seg=14, loc=(cx, cy, TZ + .104), paint=coffee)
        dv4.torus("CupHandle%d" % i, .018, .006, loc=(cx + .048 * (1 if cx > 0 else -1), cy, TZ + .088), rot=(90, 0, 0), seg=12, minor=5, paint=cream)
        dv4.torus("CupBand%d" % i, .0405, .003, loc=(cx, cy, TZ + .105), seg=18, minor=4, paint=brass)
    dv4.lathe("Plate", [(0, 0), (.08, 0), (.088, .008), (.092, .014), (.08, .014), (0, .006)], seg=22, loc=(.05, -.22, TZ + .045), paint=cream)
    for i in range(3):
        a = i * 2.1
        dv4.cylinder("Cookie%d" % i, .028, .012, loc=(.05 + math.cos(a) * .035, -.22 + math.sin(a) * .035, TZ + .052 + i * .004), seg=10, paint=cookie, bevel=.005)
    return {"name": "ParasolTable", "tex": 1024, "budget": 15000, "floor": "C9C3B8"}
