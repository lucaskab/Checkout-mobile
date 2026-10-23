"""basket-stack: seven nested red plastic shopping baskets (perforated walls, rolled rims, chrome wire handles with red grips)
on a chrome tube stand with a navy tray; a navy sign with a cream basket pictogram on two chrome posts behind.
Footprint half .30 x .24, height <= 1.2 (Blender: long axis X, front = +Y)."""
import os, sys, math
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_A as lib

CONFIG = {"floor": "F4EFE4", "seed": 7}

BW, BD, BR = .45, .30, .05      # basket rim outline (w x d, corner radius)
H = .215                        # wall top (rim bead above)
BZ, STEP, N = .125, .062, 7     # bottom of the first basket, nesting step, count


def wall(z):
    return -.038 * (1 - z / H)


def rim_profile():
    w = wall(H)
    return [(w + .011, H + .008), (w + .011, H + .020), (w, H + .027), (w - .013, H + .019), (w - .009, H + .003)]


def basket(i, plastic, chrome, grip):
    z0 = BZ + i * STEP
    top, bottom = i == N - 1, i == 0
    prof = []
    if bottom:
        prof += [(wall(0) - .008, 0), (wall(0), .006)]
    else:
        prof += [(wall(.045), .045)]
    prof += [(wall(.10), .10), (wall(.16), .16), (wall(H), H)]
    prof += rim_profile()
    if top:
        prof += [(wall(.12) - .006, .12), (wall(.03) - .006, .03), (wall(.03) - .018, .016)]
    else:
        prof += [(wall(.18) - .006, .18)]
    lib.sweep_rect("Basket%d" % i, prof, BW, BD, BR, cseg=3, cap_first=bottom, cap_last=top, paint=plastic, loc=(0, 0, z0))
    if top:
        # both wire handles raised and meeting above the basket, red grips side by side
        for s in (1, -1):
            y = .085 * s
            pts = [(-.228, y, z0 + .22), (-.226, y * .75, z0 + .33), (-.19, .016 * s, z0 + .45), (-.13, .014 * s, z0 + .48),
                   (.13, .014 * s, z0 + .48), (.19, .016 * s, z0 + .45), (.226, y * .75, z0 + .33), (.228, y, z0 + .22)]
            dv4.tube("Handle%d" % s, pts, radius=.0055, res=6, paint=chrome, resolution=3)
            dv4.cylinder("Grip%d" % s, .013, .21, loc=(-.105, .014 * s, z0 + .48), rot=(0, 90, 0), seg=10, paint=grip, bevel=.005)
    else:
        # handles folded down against the long walls
        for s in (1, -1):
            y = .085 * s
            pts = [(-.228, y, z0 + .22), (-.215, .172 * s, z0 + .19), (-.14, .18 * s, z0 + .165), (.14, .18 * s, z0 + .165),
                   (.215, .172 * s, z0 + .19), (.228, y, z0 + .22)]
            dv4.tube("Fold%d_%d" % (i, s), pts, radius=.0055, res=6, paint=chrome, kind="POLY", resolution=1)
            dv4.cylinder("FGrip%d_%d" % (i, s), .012, .21, loc=(-.105, .18 * s, z0 + .165), rot=(0, 90, 0), seg=6, paint=grip, bevel=.004)


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.2, light=.34)
    holes = [(BZ + i * STEP + .03, BZ + i * STEP + H - .012) for i in range(N)]
    plastic = lib.paint_plastic("Plastic", base="D74A3C", dark="A33125", light="EE7461", hole="4A130E", holes=holes,
                                pitch=.019, half=.0058, floor_holes=[BZ + (N - 1) * STEP + .016], tint=.08)
    grip = dv4.paint_flat("Grip", "C33A2E", dark="6E1C14", variation=.25, scale=20.0, edge="F08A7A", edge_r=.004)
    chrome = lib.paint_chrome("Chrome")
    navy = dv4.paint_flat("Navy", "1D2B4F", dark="0E1630", variation=.3, scale=6.0, edge="5C6E9C", edge_r=.006)
    gold = lib.paint_brass("Gold", base="E0B040", dark="9C7220", light="FFE38A")
    cream = dv4.paint_flat("Cream", "F4EFE4", dark="CDBFA6", variation=.2, scale=12.0, edge="FFFFFF", edge_r=.004)
    rubber = dv4.paint_flat("Rubber", "2F3A40", dark="141A1E", variation=.3, scale=10.0)

    # ---- stand: chrome tube base loop on rubber feet, four posts, navy tray
    bw, bd = .50, .34
    loop = [(-bw / 2 + .04, -bd / 2, .028), (bw / 2 - .04, -bd / 2, .028), (bw / 2, -bd / 2 + .04, .028), (bw / 2, bd / 2 - .04, .028),
            (bw / 2 - .04, bd / 2, .028), (-bw / 2 + .04, bd / 2, .028), (-bw / 2, bd / 2 - .04, .028), (-bw / 2, -bd / 2 + .04, .028)]
    dv4.tube("BaseLoop", loop, radius=.011, res=8, paint=chrome, cyclic=True, resolution=2)
    for x in (-bw / 2 + .06, bw / 2 - .06):
        for y in (-bd / 2 + .05, bd / 2 - .05):
            dv4.cylinder("Foot", .02, .022, loc=(x, y, 0), seg=8, paint=rubber)
            dv4.tube("Post", [(x, y, .03), (x, y, .10)], radius=.009, res=8, paint=chrome, kind="POLY", resolution=1)
    dv4.cube("Tray", (bw - .02, bd - .02, .03), loc=(0, 0, .11), paint=navy, bevel=.012, segs=2)
    dv4.cube("TrayLip", (bw - .06, bd - .06, .006), loc=(0, 0, .127), paint=gold, bevel=.002, segs=1)

    # ---- baskets
    for i in range(N):
        basket(i, plastic, chrome, grip)

    # ---- sign on two chrome posts behind the stack (pictogram of a basket, no text)
    sx, sy, sz, tilt = .36, -.165, 1.085, 10.0
    t = math.radians(tilt)
    def on_sign(dx, dz, out):
        return (dx, sy + out * math.cos(t) - dz * math.sin(t), sz + out * math.sin(t) + dz * math.cos(t))
    for x in (-.14, .14):
        dv4.tube("Upright", [(x, -.165, .03), (x, -.165, .60), (x, -.198, 1.17)], radius=.011, res=6, paint=chrome, resolution=2)
        dv4.sphere("Cap", .017, loc=(x, -.198, 1.182), seg=8, rings=5, paint=gold)
    dv4.tube("CrossBar", [(-.14, -.168, .92), (.14, -.168, .92)], radius=.009, res=6, paint=chrome, kind="POLY", resolution=1)
    dv4.cube("SignFrame", (sx + .024, .016, .20), loc=on_sign(0, 0, -.004), rot=(tilt, 0, 0), paint=gold, bevel=.008, segs=2)
    dv4.cube("Sign", (sx, .016, .176), loc=on_sign(0, 0, .004), rot=(tilt, 0, 0), paint=navy, bevel=.006, segs=2)
    # pictogram: cream basket body (trapezoid), wire handle arc, two dark slots
    body = [(-.052, .034), (.052, .034), (.07, -.034), (-.07, -.034)]
    lib.prism("PictoBody", body, .007, paint=cream, loc=on_sign(0, -.012, .012), rot=(tilt - 90, 0, 0), bevel=.003)
    dv4.torus("PictoHandle", .046, .007, loc=on_sign(0, .028, .016), rot=(90 + tilt, 0, 0), seg=12, minor=5, paint=cream, arc=180)
    for dx in (-.024, .024):
        dv4.cube("PictoSlot", (.009, .006, .044), loc=on_sign(dx, -.012, .021), rot=(tilt, 0, 0), paint=navy, bevel=.002, segs=1)
    dv4.sphere("PictoStar", .013, loc=on_sign(.13, .052, .014), seg=6, rings=4, paint=gold)
    dv4.sphere("PictoStar2", .013, loc=on_sign(-.13, .052, .014), seg=6, rings=4, paint=gold)
    return {"name": "BasketStack", "tex": 1024, "budget": 6000, "floor": "F4EFE4"}
