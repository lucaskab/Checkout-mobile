"""hotdog-cart: stainless hot-dog cart with a griddle full of sausages, bun basket, condiment bottles, spoked wheels,
a navy front panel with a hot-dog pictogram badge and a red/cream striped rectangular umbrella.
Footprint half .80 x .45, height <= 2.4 (Blender: X across, customers at +Y, vendor pushes from -Y)."""
import math, os, sys
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_J as J

CONFIG = {"floor": "C9C3B8", "seed": 22}

BW, BD = 1.26, .60        # body width / depth
Z0, Z1 = .40, 1.00        # body bottom / counter top


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.22, light=.36)
    steel = J.paint_steel("Steel", brush="X")
    steel_d = J.paint_steel("SteelDark", base="8F999F", dark="5B656C", light="C9D2D7", brush="Z")
    navy = J.paint_gloss("Navy", "1D2B4F", dark="0E1730", light="4A5C8C", variation=.15, highlight=.22)
    cream = J.paint_gloss("Cream", "F4EFE4", dark="C9BFA8", light="FFFFFF", variation=.1, highlight=.15)
    gold = dv4.paint_gold("Gold")
    red = J.paint_gloss("Red", "D74A3C", dark="8E2A20", light="F28A7C", variation=.12)
    yellow = J.paint_gloss("Yellow", "E8B52E", dark="A8781A", light="FFE07A", variation=.12)
    green = J.paint_gloss("Green", "5A9D33", dark="2F6F2C", light="9BD36A", variation=.12)
    tire = dv4.paint_iron("Tire", base="23272B", mid="3B4248", edge="7E878E", rust_amt=0.0)
    griddle = J.paint_griddle("Griddle")
    sausage = J.paint_sausage("Sausage", axis="Y")
    bun = J.paint_bun("Bun")
    wood = dv4.paint_wood("Handle", base="B06A37", dark="5A3418", light="DDA55F", along="X", scale=4.0)
    cloth = J.paint_stripes("Canopy", cols=("D74A3C", "F4EFE4"), axis="X", width=.195, phase=.5, shade=.15)
    cloth_v = J.paint_stripes("Valance", cols=("F4EFE4", "D74A3C"), axis="X", width=.195, phase=.5, shade=.1)

    # ---- body: stainless box with a navy front panel, skirt, counter top with a rolled rim
    dv4.cube("Body", (BW, BD, Z1 - Z0 - .05), loc=(0, 0, (Z0 + Z1 - .05) / 2), paint=steel, bevel=.02, segs=3)
    dv4.cube("Counter", (BW + .06, BD + .06, .05), loc=(0, 0, Z1 - .025), paint=steel_d, bevel=.018, segs=3)
    dv4.cube("Skirt", (BW - .08, BD - .08, .06), loc=(0, 0, Z0 - .02), paint=steel_d, bevel=.01, segs=2)
    dv4.cube("FrontPanel", (BW - .16, .03, Z1 - Z0 - .18), loc=(0, BD / 2 + .005, (Z0 + Z1) / 2 - .02), paint=navy, bevel=.01, segs=2)
    dv4.cube("PanelTrim", (BW - .12, .012, Z1 - Z0 - .14), loc=(0, BD / 2 - .006, (Z0 + Z1) / 2 - .02), paint=gold, bevel=.004, segs=1)
    # pictogram badge on the front: cream rounded plate with a 3D hot dog (bun halves + sausage + mustard squiggle)
    bz = (Z0 + Z1) / 2 - .02; by = BD / 2 + .03
    dv4.cube("Badge", (.42, .025, .26), loc=(0, by, bz), paint=cream, bevel=.012, segs=3)
    dv4.torus("BadgeRing", .17, .012, loc=(0, by + .01, bz), rot=(90, 0, 0), seg=24, minor=5, paint=gold)
    for sz in (-1, 1):
        dv4.sphere("BadgeBun%d" % sz, .05, loc=(0, by + .028, bz + sz * .036), scale=(2.6, .5, .75), seg=16, rings=8, paint=bun)
    dv4.tube("BadgeDog", [(-.13, by + .04, bz), (0, by + .045, bz + .01), (.13, by + .04, bz)], radius=.03, res=8, paint=sausage, resolution=4,
             taper=[(0, .6), (.2, 1), (.8, 1), (1, .6)])
    sq = [(-.11 + i * .022, by + .07, bz + .012 * (1 if i % 2 else -1)) for i in range(11)]
    dv4.tube("BadgeMustard", sq, radius=.008, res=6, paint=yellow, resolution=3)
    # ---- wheels: two big spoked wheels on an axle at the back, two casters at the front
    for sx in (-1, 1):
        J.spoke_wheel("Wheel%d" % sx, (sx * (BW / 2 + .06), -.12, .30), R=.30, rim=.032, spokes=8, paint_tire=tire, paint_rim=red, paint_hub=gold, axis="X")
        dv4.lathe("Caster%d" % sx, [(0, -.03), (.07, -.03), (.07, .03), (0, .03)], seg=16, loc=(sx * .42, .20, .07), rot=(0, 90, 0), paint=tire)
        dv4.cube("CasterFork%d" % sx, (.03, .05, .12), loc=(sx * .42 + .045 * sx, .20, .13), paint=steel_d, bevel=.006, segs=1)
    dv4.tube("Axle", [(-BW / 2 - .06, -.12, .30), (BW / 2 + .06, -.12, .30)], radius=.018, res=8, paint=steel_d, kind="POLY", resolution=1)
    dv4.cube("AxleMount", (BW - .2, .08, .08), loc=(0, -.12, .36), paint=steel_d, bevel=.012, segs=2)
    # ---- push handle at the back (vendor side), wooden grip
    for sx in (-.45, .45):
        dv4.tube("HandleArm%s" % sx, [(sx, -BD / 2, .82), (sx, -BD / 2 - .10, .88), (sx, -BD / 2 - .13, 1.02)], radius=.016, res=8, paint=steel_d, resolution=4)
    dv4.tube("Grip", [(-.47, -BD / 2 - .13, 1.02), (.47, -BD / 2 - .13, 1.02)], radius=.024, res=10, paint=wood, kind="POLY", resolution=1)
    # ---- counter: griddle (left) with sausages, bun basket (right), condiment caddy, steam pot
    gx, gy = -.30, .02
    dv4.cube("GriddleRim", (.56, .44, .035), loc=(gx, gy, Z1 + .017), paint=steel_d, bevel=.01, segs=2)
    dv4.cube("GriddlePlate", (.50, .38, .03), loc=(gx, gy, Z1 + .03), paint=griddle, bevel=.006, segs=1)
    for i in range(6):
        x = gx - .20 + i * .08
        y0 = gy + RNG.uniform(-.03, .03)
        dv4.tube("Sausage%d" % i, [(x, y0 - .13, Z1 + .07), (x + .006, y0, Z1 + .075), (x, y0 + .13, Z1 + .07)], radius=.024, res=8, paint=sausage,
                 resolution=3, taper=[(0, .55), (.12, 1), (.88, 1), (1, .55)])
    dv4.tube("Spatula", [(gx - .05, gy - .17, Z1 + .05), (gx - .12, gy - .25, Z1 + .06), (gx - .20, gy - .33, Z1 + .09)], radius=.009, res=6, paint=steel_d, resolution=3)
    dv4.cube("SpatulaBlade", (.09, .1, .006), loc=(gx - .02, gy - .14, Z1 + .05), paint=steel_d, bevel=.003, segs=1)
    # bun basket: a shallow wicker-coloured steel tray with 5 buns
    bx, byy = .30, .06
    dv4.cube("BunTray", (.48, .40, .05), loc=(bx, byy, Z1 + .025), paint=steel_d, bevel=.012, segs=2)
    dv4.cube("BunCloth", (.42, .34, .03), loc=(bx, byy, Z1 + .045), paint=cream, bevel=.01, segs=2)
    for i in range(5):
        x = bx - .17 + i * .085
        dv4.sphere("Bun%d" % i, .045, loc=(x, byy, Z1 + .085), scale=(.85, 2.9, .95), seg=10, rings=6, paint=bun, rot=(0, 0, RNG.uniform(-5, 5)))
        dv4.cube("BunSlit%d" % i, (.006, .22, .02), loc=(x, byy, Z1 + .125), paint=griddle, bevel=.002, segs=1)
    # condiment caddy at the front edge: red / yellow / green squeeze bottles
    cx, cy = .05, BD / 2 - .10
    dv4.cube("Caddy", (.30, .12, .10), loc=(cx, cy, Z1 + .05), paint=navy, bevel=.012, segs=2)
    for i, pcol in enumerate((red, yellow, green)):
        x = cx - .095 + i * .095
        dv4.lathe("Bottle%d" % i, [(0, 0), (.033, 0), (.036, .03), (.036, .15), (.028, .18), (.02, .19), (.02, .215), (.008, .25), (0, .25)],
                  seg=12, loc=(x, cy, Z1 + .06), paint=pcol)
    # steam pot with lid at the back of the counter
    dv4.lathe("Pot", [(0, 0), (.10, 0), (.105, .02), (.105, .16), (.11, .17), (.11, .19), (.0, .19)], seg=16, loc=(-.38, -.22, Z1), paint=steel)
    dv4.lathe("Lid", [(0, .19), (.115, .19), (.11, .21), (.06, .24), (.02, .25), (.02, .29), (.0, .29)], seg=16, loc=(-.38, -.22, Z1), paint=steel_d)
    dv4.torus("LidKnob", .02, .012, loc=(-.38, -.22, Z1 + .30), seg=12, minor=6, paint=gold)
    # ---- umbrella: pole from the back corner of the body, rectangular striped canopy, scalloped valance, finial
    px, py = .35, -.22
    dv4.tube("Pole", [(px, py, Z1), (px, py, 2.12)], radius=.02, res=10, paint=steel_d, kind="POLY", resolution=1)
    dv4.lathe("PoleCollar", [(0, 0), (.035, 0), (.035, .05), (.025, .06), (0, .06)], seg=12, loc=(px, py, Z1), paint=gold)
    W, Dd, ZE, PK = .78, .43, 2.00, .28
    canopy = J.rect_canopy("Canopy", W, Dd, ZE, PK, nx=16, ny=10, sag=.04, paint=cloth, thickness=.012)
    canopy.location = (0, 0, 0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            dv4.tube("Rib%d%d" % (sx, sy), [(0, 0, ZE + PK - .01), (sx * W * .55, sy * Dd * .55, ZE + PK * .4), (sx * W, sy * Dd, ZE - .01)],
                     radius=.011, res=6, paint=steel_d, resolution=4)
    corners = [(-W, -Dd), (W, -Dd), (W, Dd), (-W, Dd)]
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        n = 8 if abs(a[0] - b[0]) > .1 else 5
        J.valance_line("Valance%d" % i, (a[0], a[1], ZE), (b[0], b[1], ZE), drop=.10, n=n, per=6, paint=cloth_v, thickness=.008)
    dv4.lathe("Finial", [(0, ZE + PK - .02), (.03, ZE + PK), (.028, ZE + PK + .03), (.015, ZE + PK + .05), (0, ZE + PK + .06)], seg=12, paint=gold)
    dv4.sphere("FinialBall", .032, loc=(0, 0, ZE + PK + .07), seg=12, rings=8, paint=gold)
    # pole is offset from the canopy centre, so a short angled strut joins them (real market umbrellas tilt on a knuckle)
    dv4.tube("PoleArm", [(px, py, 2.12), (px * .5, py * .5, 2.22), (0, 0, ZE + PK - .05)], radius=.02, res=10, paint=steel_d, resolution=4)
    return {"name": "HotdogCart", "tex": 1024, "budget": 10000, "floor": "C9C3B8"}
