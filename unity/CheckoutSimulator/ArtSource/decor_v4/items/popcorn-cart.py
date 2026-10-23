"""popcorn-cart: vintage red & cream popcorn wagon - big spoked wheels, brass rails, glass cabinet heaped with popcorn and a
steel kettle, striped scalloped canopy with a swaying pennant, striped paper bags on the side shelf.
Footprint half .80 x .42, height <= 2.5 (Blender: X across, front = +Y, Z up)."""
import math
import dv4
from dv4 import RNG
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib_F as F

CONFIG = {"floor": "C9C3B8", "seed": 21}

RED, CREAM, GOLD = "D74A3C", "F4EFE4", "E0B040"


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.22, light=.36)
    red = F.paint_enamel("Red", RED, dark="8F2A20", light="FF9A8C", variation=.16, scratch=.08)
    cream = F.paint_enamel("Cream", CREAM, dark="C9BFA8", light="FFFFFF", variation=.1, scratch=.05)
    navy = F.paint_enamel("Navy", "1D2B4F", dark="0C1328", light="6C7FB0", variation=.12)
    brass = F.paint_brass("Brass")
    iron = dv4.paint_iron("Iron", base="23282E", mid="3C444C", edge="8A949C", rust_amt=.15)
    steel = F.paint_chrome("Steel")
    wood = dv4.paint_wood("Wood", base="C98B4E", dark="7A4F2A", light="E8B870", scale=5.0, along="Y", edge="F0CB8A", tint=.2)
    pop = F.paint_popcorn("Popcorn")
    awn = F.paint_stripes("Awning", [RED, CREAM], .30, axis="X", origin=-.075, dark="4A1A14")
    bag = F.paint_stripes("Bag", [RED, "FBF8F1"], .05, axis="X", origin=0.0, cloth=False, dark="000000", edge="FFFFFF", edge_k=.4, edge_r=.004)
    glow = "E_FFE2A8"

    # ---------------------------------------------------------------- undercarriage, wheels, handle
    dv4.cube("Frame", (.98, .52, .07), loc=(0, 0, .215), paint=iron, bevel=.012)
    dv4.tube("Axle", [(-.66, 0, .30), (.66, 0, .30)], radius=.018, res=8, paint=iron, kind="POLY", resolution=1)
    for sx in (-1, 1):
        F.spoked_wheel("W%d" % sx, (sx * .60, 0, .30), .29, .022, .045, 12, iron, brass, wood, axis="X", rim_minor=6, rim_seg=28)
    # small swivel casters at the front corners
    for sx in (-.34, .34):
        dv4.cylinder("Caster%s" % sx, .055, .035, loc=(sx - .0175, .20, .055), rot=(0, 90, 0), seg=10, paint=iron, bevel=.008)
        dv4.cube("Fork%s" % sx, (.05, .03, .11), loc=(sx, .20, .13), paint=iron, bevel=.006)
    # push handle on the left end: two bent brass tubes + wooden grip
    for y in (-.17, .17):
        dv4.tube("Handle%s" % y, [(-.50, y, .62), (-.66, y, .66), (-.73, y, .80), (-.76, y, .98)], radius=.015, res=8, paint=brass, resolution=3)
    dv4.cylinder("Grip", .024, .40, loc=(-.76, -.20, .98), rot=(-90, 0, 0), seg=12, paint=wood, bevel=.008)
    for y in (-.22, .22):
        dv4.sphere("GripCap%s" % y, .028, loc=(-.76, y, .98), seg=8, rings=5, paint=brass)

    # ---------------------------------------------------------------- cabinet body
    dv4.cube("Cabinet", (1.06, .62, .54), loc=(0, 0, .52), paint=red, bevel=.025, segs=3)
    # cream panels on all four faces, framed by brass trim
    for (x, y, w, rz) in ((-.25, .312, .40, 0), (.25, .312, .40, 0), (-.25, -.312, .40, 0), (.25, -.312, .40, 0), (-.532, 0, .44, 90), (.532, 0, .44, 90)):
        dv4.cube("Panel%s%s" % (x, y), (w, .012, .36), loc=(x, y, .50), rot=(0, 0, rz), paint=cream, bevel=.01, segs=1)
        dv4.cube("PanelFrame%s%s" % (x, y), (w + .035, .010, .395), loc=(x, y, .50), rot=(0, 0, rz), paint=brass, bevel=.006, segs=1)
    for z in (.28, .77):
        for y in (.318, -.318):
            dv4.tube("Rail%s%s" % (z, y), [(-.54, y, z), (.54, y, z)], radius=.011, res=6, paint=brass, kind="POLY", resolution=1)
        for x in (.538, -.538):
            dv4.tube("RailS%s%s" % (z, x), [(x, -.32, z), (x, .32, z)], radius=.011, res=6, paint=brass, kind="POLY", resolution=1)
    # counter top with a brass lip
    dv4.cube("Counter", (1.12, .68, .045), loc=(0, 0, .81), paint=cream, bevel=.014, segs=3)
    dv4.cube("CounterEdge", (1.12, .68, .012), loc=(0, 0, .835), paint=brass, bevel=.005, segs=2)

    # ---------------------------------------------------------------- glass cabinet (left 2/3) with popcorn + kettle
    X0, X1, Y0, Y1, Z0, Z1 = -.52, .22, -.30, .30, .835, 1.46
    for x in (X0, X1):
        for y in (Y0, Y1):
            dv4.tube("Post%s%s" % (x, y), [(x, y, Z0), (x, y, Z1 + .02)], radius=.016, res=8, paint=brass, kind="POLY", resolution=1)
    for (a, b) in (((X0, Y0), (X1, Y0)), ((X0, Y1), (X1, Y1)), ((X0, Y0), (X0, Y1)), ((X1, Y0), (X1, Y1))):
        dv4.tube("TopRail%s%s" % (a, b), [(a[0], a[1], Z1), (b[0], b[1], Z1)], radius=.014, res=6, paint=brass, kind="POLY", resolution=1)
    # glass panes (G_Glass, not baked)
    dv4.patch("GlassF", X1 - X0 - .03, Z1 - Z0 - .03, 1, 1, loc=((X0 + X1) / 2, Y1, (Z0 + Z1) / 2), rot=(-90, 0, 0), paint=None, mat_override="G_Glass")
    dv4.patch("GlassB", X1 - X0 - .03, Z1 - Z0 - .03, 1, 1, loc=((X0 + X1) / 2, Y0, (Z0 + Z1) / 2), rot=(90, 0, 0), paint=None, mat_override="G_Glass")
    dv4.patch("GlassL", Z1 - Z0 - .03, Y1 - Y0 - .03, 1, 1, loc=(X0, 0, (Z0 + Z1) / 2), rot=(0, -90, 0), paint=None, mat_override="G_Glass")
    dv4.patch("GlassR", Z1 - Z0 - .03, Y1 - Y0 - .03, 1, 1, loc=(X1, 0, (Z0 + Z1) / 2), rot=(0, 90, 0), paint=None, mat_override="G_Glass")
    # cabinet roof plate (red) + bulb
    dv4.cube("CabRoof", (X1 - X0 + .06, Y1 - Y0 + .06, .03), loc=((X0 + X1) / 2, 0, Z1 + .035), paint=red, bevel=.01, segs=2)
    dv4.sphere("Bulb", .028, loc=(-.02, 0, Z1 - .06), seg=10, rings=6, paint=None, mat_override=glow)
    dv4.cylinder("BulbSocket", .018, .04, loc=(-.02, 0, Z1 - .04), seg=8, paint=iron)
    # popcorn heap: displaced bed + loose kernels on top (deeper on the right, below the kettle on the left)
    bed = dv4.patch("PopBed", X1 - X0 - .05, Y1 - Y0 - .05, 10, 8, loc=((X0 + X1) / 2, 0, Z0 + .17), paint=pop)
    dv4.mod_displace(bed, strength=.07, size=.09, mid=.45)
    dv4.cube("PopBedSide", (X1 - X0 - .05, Y1 - Y0 - .05, .17), loc=((X0 + X1) / 2, 0, Z0 + .085), paint=pop, bevel=0)
    k = 0
    for i in range(30):
        x = RNG.uniform(X0 + .05, X1 - .05); y = RNG.uniform(Y0 + .05, Y1 - .05) * (1.12 if i % 2 else 1.0)
        hill = .06 * math.exp(-((x + .12) / .22) ** 2 - (y / .25) ** 2)
        z = Z0 + .19 + hill + RNG.uniform(-.015, .02)
        s = RNG.uniform(.028, .04)
        dv4.sphere("Kernel%d" % k, s, loc=(x, y, z), scale=(RNG.uniform(.85, 1.2), RNG.uniform(.85, 1.2), RNG.uniform(.7, .9)),
                   seg=7, rings=4, paint=pop, rot=(RNG.uniform(0, 40), RNG.uniform(0, 40), RNG.uniform(0, 360)))
        k += 1
    # steel kettle hanging from a cross rod, lid ajar, stirrer crank on top
    kx, kz = -.30, 1.22
    dv4.tube("KettleRod", [(kx, Y0 + .02, kz + .13), (kx, Y1 - .02, kz + .13)], radius=.009, res=6, paint=iron, kind="POLY", resolution=1)
    dv4.lathe("Kettle", [(0, 0), (.09, 0), (.115, .02), (.125, .07), (.125, .17), (.118, .19), (.105, .19), (.105, .185), (0, .185)],
              seg=22, loc=(kx, 0, kz - .09), paint=steel)
    dv4.lathe("KettleRim", [(.118, 0), (.132, .006), (.132, .02), (.118, .026)], seg=22, loc=(kx, 0, kz + .095), paint=brass, cap=False)
    dv4.lathe("Lid", [(0, 0), (.11, 0), (.115, .012), (.06, .03), (.02, .04), (0, .04)], seg=18, loc=(kx + .03, 0, kz + .11), rot=(0, -18, 0), paint=steel)
    dv4.tube("Crank", [(kx, 0, kz + .13), (kx, 0, kz + .19), (kx + .05, 0, kz + .19), (kx + .05, 0, kz + .22)], radius=.007, res=6, paint=iron, resolution=3)
    for y in (-.1, .1):
        dv4.tube("KettleArm%s" % y, [(kx, y, kz + .13), (kx, y * 1.0, kz + .04)], radius=.008, res=6, paint=iron, kind="POLY", resolution=1)
    # red scoop resting in the popcorn
    dv4.lathe("ScoopCup", [(0, 0), (.045, 0), (.05, .01), (.05, .06), (0, .06)], seg=14, loc=(.05, .12, Z0 + .22), rot=(0, 60, -30), paint=red)
    dv4.tube("ScoopHandle", [(.07, .10, Z0 + .26), (.14, .05, Z0 + .34)], radius=.009, res=6, paint=wood, kind="POLY", resolution=1)

    # ---------------------------------------------------------------- right shelf: striped bags of popcorn + salt shaker
    bz = .835
    for i, (bx, by, rz) in enumerate(((.36, .17, 8), (.44, -.05, -12), (.33, -.19, 20))):
        b = dv4.cube("Bag%d" % i, (.10, .07, .16), loc=(bx, by, bz + .08), rot=(0, 0, rz), paint=bag, bevel=.012, segs=2)
        for j in range(4):
            dv4.sphere("BagPop%d%d" % (i, j), RNG.uniform(.024, .03), loc=(bx + RNG.uniform(-.03, .03), by + RNG.uniform(-.02, .02), bz + .16 + RNG.uniform(0, .02)),
                       seg=6, rings=4, paint=pop, scale=(1.1, 1, .8), rot=(0, 0, RNG.uniform(0, 360)))
    dv4.lathe("Shaker", [(0, 0), (.025, 0), (.028, .01), (.028, .07), (.024, .08), (.014, .095), (0, .1)], seg=12, loc=(.49, .22, bz), paint=steel)
    dv4.cylinder("ShakerGlass", .027, .06, loc=(.49, .22, bz + .012), seg=12, paint=None, mat_override="G_Glass")

    # ---------------------------------------------------------------- canopy: four brass posts, arched striped roof, scalloped valance
    CX0, CX1, CY0, CY1, CZ = -.60, .60, -.37, .37, 1.62
    for x, y in ((-.52, -.30), (-.52, .30), (.52, -.30), (.52, .30)):
        dv4.tube("CPost%s%s" % (x, y), [(x, y, .84), (x, y, CZ + .02)], radius=.013, res=8, paint=brass, kind="POLY", resolution=1)
    F.arched_roof("Roof", CX0, CX1, CY0, CY1, CZ, .17, awn, nx=8, ny=14, thickness=.02, bow="Y")
    F.scallop_strip_rect("Valance", CX0, CX1, CY0, CY1, CZ + .004, .085, awn, n_w=8, n_d=5, thickness=.008, segs_per=4)
    dv4.tube("RidgeRail", [(CX0, 0, CZ + .17), (CX1, 0, CZ + .17)], radius=.012, res=8, paint=brass, kind="POLY", resolution=1)
    for x in (CX0, CX1):
        dv4.sphere("RidgeBall%s" % x, .03, loc=(x, 0, CZ + .17), seg=8, rings=5, paint=brass)
    # finial pole + pennant
    dv4.tube("Pole", [(0, 0, CZ + .15), (0, 0, CZ + .42)], radius=.009, res=8, paint=brass, kind="POLY", resolution=1)
    dv4.sphere("PoleBall", .022, loc=(0, 0, CZ + .42), seg=10, rings=6, paint=brass)
    sway = "Anim Sway"; dv4.pivot(sway, (0, 0, CZ + .40))
    F.pennant("Pennant", (0, 0, CZ + .40), .10, .27, red, out=sway, rot_z=-20)
    return {"name": "PopcornCart", "tex": 1024, "budget": 10000, "floor": "C9C3B8"}
