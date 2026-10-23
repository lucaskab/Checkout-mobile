"""ice-cream-cart (diamond): pastel mint & pink ice-cream wagon - big white spoked wheels, checkered skirt, cream panels with a
cone pictogram, four freezer wells (chrome lids / open tubs of colourful ice cream with scoops), a cone holder full of waffle
cones, a giant triple-scoop cone ornament, and a striped scalloped parasol with a swaying pennant.
Footprint half .80 x .42, height <= 2.5 (Blender: X across, front = +Y, Z up)."""
import math
import dv4
from dv4 import RNG
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib_F as F

CONFIG = {"floor": "C9C3B8", "seed": 22}

MINT, PINK, CREAM, TEAL, GOLD = "BFE8DC", "EE8FAE", "F4EFE4", "1F9A8E", "E0B040"
PX = 0.0           # parasol pole x


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.22, light=.36)
    mint = F.paint_enamel("Mint", MINT, dark="6FB5A3", light="FFFFFF", variation=.14, scratch=.06)
    pink = F.paint_enamel("Pink", PINK, dark="B8536F", light="FFD5E2", variation=.14, scratch=.05)
    cream = F.paint_enamel("Cream", CREAM, dark="C9BFA8", light="FFFFFF", variation=.1, scratch=.04)
    white = F.paint_enamel("White", "FBF8F1", dark="C9C2B6", light="FFFFFF", variation=.08, scratch=.04)
    teal = F.paint_enamel("Teal", TEAL, dark="0F5C55", light="7FD6CB", variation=.14)
    gold = F.paint_brass("Gold")
    chrome = F.paint_chrome("Chrome")
    iron = dv4.paint_iron("Iron", base="2A3138", mid="434C55", edge="9AA4AC", rust_amt=.1)
    wood = dv4.paint_wood("Wood", base="D8A15E", dark="8C5A2E", light="F0C98A", scale=5.0, along="Y", edge="F6D9A6", tint=.2)
    icon = F.paint_icon_cone("Icon", base=CREAM, scoop=PINK, scoop2="A8E6CF", at=(.0, .50), size=.15)
    checker = F.paint_checker("Checker", PINK, "FBF8F1", size=.055, axis="XZ")
    checker_s = F.paint_checker("CheckerS", PINK, "FBF8F1", size=.055, axis="YZ")
    waffle = F.paint_waffle("Waffle")
    para = F.paint_stripes_radial("Parasol", [PINK, CREAM, MINT], 18, center=(PX, 0), dark="5A2A3A")
    straw = F.paint_icecream("Straw", ["F28DAA"], sprinkles=False)
    mintc = F.paint_icecream("MintChoc", ["A8E6CF"], sprinkles=True)
    choco = F.paint_icecream("Choco", ["6B4228"], sprinkles=False)
    vanil = F.paint_icecream("Vanilla", ["FFF8DC"], sprinkles=True, k_ao=.35, k_light=.2)
    cherry = F.paint_enamel("Cherry", "C0263B", dark="6E0F1E", light="FF8A9A", variation=.1, scratch=0.0, hl=.35)

    # ---------------------------------------------------------------- undercarriage, wheels, handle
    dv4.cube("Frame", (.92, .48, .07), loc=(0, 0, .215), paint=iron, bevel=.012)
    dv4.tube("Axle", [(-.64, 0, .30), (.64, 0, .30)], radius=.018, res=8, paint=iron, kind="POLY", resolution=1)
    for sx in (-1, 1):
        F.spoked_wheel("W%d" % sx, (sx * .58, 0, .30), .29, .022, .045, 12, white, gold, pink, axis="X", rim_minor=6, rim_seg=24)
    for sx in (-.30, .30):
        dv4.cylinder("Caster%s" % sx, .055, .035, loc=(sx - .0175, .18, .055), rot=(0, 90, 0), seg=10, paint=iron, bevel=.008)
    for y in (-.16, .16):
        dv4.tube("Handle%s" % y, [(-.48, y, .62), (-.64, y, .66), (-.71, y, .80), (-.74, y, .98)], radius=.015, res=8, paint=chrome, resolution=3)
    dv4.cylinder("Grip", .024, .38, loc=(-.74, -.19, .98), rot=(-90, 0, 0), seg=12, paint=wood, bevel=.008)
    for y in (-.21, .21):
        dv4.sphere("GripCap%s" % y, .028, loc=(-.74, y, .98), seg=8, rings=5, paint=gold)

    # ---------------------------------------------------------------- cabinet body
    dv4.cube("Cabinet", (1.0, .58, .50), loc=(0, 0, .52), paint=mint, bevel=.025, segs=2)
    # checkered skirt band around the bottom
    dv4.cube("SkirtF", (1.0, .60, .075), loc=(0, 0, .315), paint=checker, bevel=.008, segs=2)
    dv4.cube("SkirtS", (1.02, .58, .075), loc=(0, 0, .315), paint=checker_s, bevel=.008, segs=2)
    # cream panels: front/back carry the cone pictogram, sides plain, pink frames
    for (x, y, w, rz, p) in ((0, .292, .62, 0, icon), (0, -.292, .62, 0, icon), (-.502, 0, .40, 90, cream), (.502, 0, .40, 90, cream)):
        dv4.cube("Panel%s%s" % (x, y), (w, .012, .30), loc=(x, y, .52), rot=(0, 0, rz), paint=p, bevel=.012, segs=1)
        dv4.cube("PanelFrame%s%s" % (x, y), (w + .04, .010, .34), loc=(x, y, .52), rot=(0, 0, rz), paint=pink, bevel=.008, segs=1)
    for z in (.36, .74):
        for y in (.298, -.298):
            dv4.tube("Rail%s%s" % (z, y), [(-.51, y, z), (.51, y, z)], radius=.011, res=6, paint=gold, kind="POLY", resolution=1)
        for x in (.508, -.508):
            dv4.tube("RailS%s%s" % (z, x), [(x, -.30, z), (x, .30, z)], radius=.011, res=6, paint=gold, kind="POLY", resolution=1)
    # counter top (white) with a pink lip
    dv4.cube("Counter", (1.06, .64, .05), loc=(0, 0, .795), paint=white, bevel=.016, segs=2)
    dv4.cube("CounterEdge", (1.06, .64, .012), loc=(0, 0, .822), paint=pink, bevel=.005, segs=2)
    TZ = .82

    # ---------------------------------------------------------------- freezer wells: 2 chrome lids (back), 2 open tubs (front)
    wells = ((-.05, -.15, "lid"), (.25, -.15, "lid"), (-.05, .15, straw), (.25, .15, mintc))
    for i, (wx, wy, kind) in enumerate(wells):
        dv4.lathe("WellRing%d" % i, [(.115, 0), (.135, 0), (.135, .012), (.115, .012)], seg=16, loc=(wx, wy, TZ), paint=chrome, cap=False)
        if kind == "lid":
            dv4.lathe("Lid%d" % i, [(0, 0), (.12, 0), (.128, .012), (.126, .03), (.10, .045), (.045, .055), (.03, .07), (.03, .085), (.02, .09), (0, .09)],
                      seg=16, loc=(wx, wy, TZ + .005), paint=chrome)
            dv4.torus("LidKnob%d" % i, .028, .012, loc=(wx, wy, TZ + .095), seg=12, minor=5, paint=pink)
        else:
            dv4.lathe("Tub%d" % i, [(0, -.10), (.11, -.10), (.113, -.02), (.113, .01), (0, .01)], seg=20, loc=(wx, wy, TZ), paint=chrome)
            dv4.sphere("Cream%d" % i, .105, loc=(wx, wy, TZ - .02), scale=(1, 1, .45), seg=14, rings=7, paint=kind)
            for j in range(2):
                a = j * 2.6 + i
                dv4.sphere("Blob%d%d" % (i, j), RNG.uniform(.032, .04), loc=(wx + math.cos(a) * .05, wy + math.sin(a) * .05, TZ + .02), seg=8, rings=5, paint=kind)
    # scoop utensil standing in the front-right tub
    dv4.lathe("ScoopCup", [(0, 0), (.03, 0), (.035, .01), (.035, .04), (0, .04)], seg=12, loc=(.31, .10, TZ + .02), rot=(20, 40, 0), paint=chrome)
    dv4.tube("ScoopHandle", [(.32, .08, TZ + .05), (.40, .02, TZ + .20)], radius=.009, res=6, paint=teal, kind="POLY", resolution=1)
    dv4.sphere("ScoopEnd", .012, loc=(.40, .02, TZ + .20), seg=8, rings=5, paint=teal)
    # taller tubs of the other two flavours behind the lids? no - a small 2-flavour display tub on the back-left corner instead
    dv4.lathe("DispTub", [(0, 0), (.07, 0), (.075, .01), (.075, .09), (.07, .10), (0, .10)], seg=18, loc=(-.40, -.17, TZ), paint=pink)
    dv4.sphere("DispCream", .066, loc=(-.40, -.17, TZ + .09), scale=(1, 1, .6), seg=10, rings=6, paint=vanil)

    # ---------------------------------------------------------------- cone holder: chrome ring stand with 6 waffle cones
    hx, hy = -.40, .19
    dv4.lathe("HolderBase", [(0, 0), (.07, 0), (.08, .01), (.08, .02), (.02, .02), (.02, .09), (0, .09)], seg=16, loc=(hx, hy, TZ), paint=chrome)
    dv4.lathe("HolderRing", [(.085, .0), (.10, .0), (.10, .012), (.085, .012)], seg=18, loc=(hx, hy, TZ + .09), paint=chrome, cap=False)
    for j in range(6):
        a = j * math.pi / 3
        cx, cy = hx + math.cos(a) * .072, hy + math.sin(a) * .072
        dv4.lathe("Cone%d" % j, [(0, 0), (.012, .01), (.03, .11), (.034, .13), (.03, .135), (0, .135)], seg=9, loc=(cx, cy, TZ + .03),
                  rot=(math.sin(a) * 10, -math.cos(a) * 10, 0), paint=waffle)

    # ---------------------------------------------------------------- giant cone ornament on a gold bracket at the right end
    ox, oy = .40, .0
    dv4.tube("OrnBracket", [(.50, oy, .60), (.56, oy, .60), (.56, oy, 1.02), (ox + .06, oy, 1.02)], radius=.012, res=8, paint=gold, resolution=3)
    dv4.sphere("OrnBase", .035, loc=(ox + .02, oy, 1.02), seg=10, rings=6, paint=gold)
    F.cone_scoop("Orn", (ox, oy, .86), .32, .11, (1.0, .9, .78), waffle, straw, cherry_p=cherry)
    # second and third scoop in other flavours: overwrite scoop paints by rebuilding them
    for o in list(dv4.PARTS):
        if o.name == "OrnScoop1":
            o.data.materials[0] = mintc
        if o.name == "OrnScoop2":
            o.data.materials[0] = vanil

    # ---------------------------------------------------------------- parasol: chrome pole, striped scalloped canopy, ribs, pennant
    PZ = 1.78                                # rim height
    dv4.tube("Pole", [(PX, 0, .80), (PX, 0, 2.18)], radius=.018, res=10, paint=chrome, kind="POLY", resolution=1)
    dv4.lathe("PoleBase", [(0, 0), (.05, 0), (.055, .01), (.04, .03), (.025, .05), (0, .05)], seg=16, loc=(PX, 0, TZ), paint=chrome)
    dv4.torus("PoleRing", .026, .01, loc=(PX, 0, 1.70), seg=10, minor=5, paint=gold)
    R = .76; RY = .40
    prof = []
    for i in range(8):
        t = i / 7
        r = R * (1 - t)
        z = PZ + .36 * (1 - (1 - t) ** 2) ** .9
        prof.append((r, z))
    prof[-1] = (0.0, PZ + .36)
    can = dv4.lathe("Canopy", prof, seg=36, paint=para, cap=False, scallop=(18, .035), loc=(PX, 0, 0), scale=(1, RY / R, 1))

    F.scallop_ring("ParaValance", PX, 0, R + .005, 18, .085, PZ + .002, para, thickness=0, flare=.01, segs_per=4, ry=RY + .005)
    for j in range(18):
        a = 2 * math.pi * j / 18
        pts = []
        for i in range(0, 8):
            r, z = prof[i]
            rr = r * (1 + .035 * math.cos(18 * a))
            pts.append((PX + math.cos(a) * rr, math.sin(a) * rr, z - .006))
        pts = [(x, y * RY / R, z) for x, y, z in pts[:6]]
        pts = [(PX + (x - PX), y, z) for x, y, z in pts]
        dv4.tube("Rib%d" % j, pts[::-1], radius=.007, res=4, paint=chrome, kind="POLY", resolution=1)
        dv4.sphere("RibTip%d" % j, .013, loc=pts[0], seg=5, rings=3, paint=gold)
    dv4.lathe("Finial", [(0, 0), (.035, 0), (.04, .015), (.025, .04), (.012, .07), (.012, .10), (0, .10)], seg=14, loc=(PX, 0, PZ + .34), paint=gold)
    dv4.sphere("FinialBall", .03, loc=(PX, 0, PZ + .46), seg=10, rings=6, paint=gold)
    sway = "Anim Sway"; dv4.pivot(sway, (PX, 0, PZ + .46))
    F.pennant("Pennant", (PX, 0, PZ + .47), .10, .26, pink, out=sway, rot_z=-25)
    return {"name": "IceCreamCart", "tex": 1024, "budget": 10000, "floor": "C9C3B8"}
