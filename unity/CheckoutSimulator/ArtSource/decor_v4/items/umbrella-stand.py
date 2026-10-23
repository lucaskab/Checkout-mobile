"""umbrella-stand: hammered brass bucket with four furled, colourful umbrellas (crook handles up). Footprint half .20 x .20, height <= 1.1."""
import math, os, sys
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib_G as G

CONFIG = {"floor": "F4EFE4", "seed": 21}


def umbrella(i, a_deg, tilt, h, colours, pattern, handle_p, canopy_p, steel_p):
    """One furled umbrella standing in the bucket: ferrule at the bottom, canopy widening upwards, crook handle on top.
    Built along local Z then tilted outwards by `tilt` degrees around the bucket centre."""
    a = math.radians(a_deg)
    base = (math.cos(a) * .046, math.sin(a) * .046, .045)
    # yaw so the crook handle curls out tangentially, then tilt outward (Euler XYZ: X, Y first, then Z)
    rz = a_deg + 135
    ap = math.radians(a_deg - rz)
    rot = (-math.sin(ap) * tilt, math.cos(ap) * tilt, rz)
    # the parts share a parent transform: emulate it by placing everything with loc/rot of the same frame
    def place(name, builder):
        ob = builder(name)
        ob.location = base; ob.rotation_euler = [math.radians(x) for x in rot]
        return ob
    # ferrule (metal tip) + lower shaft
    place("Ferrule%d" % i, lambda n: G.lathe_uv(n, [(0, 0), (.007, 0), (.0075, .05), (.006, .09), (.006, .1)], seg=10, paint=steel_p))
    # furled canopy: narrow at the ferrule, fullest just below the rib tips, 8 pleats
    cz0, cz1 = .09, h - .26
    L = cz1 - cz0
    prof = [(.0065, cz0), (.016, cz0 + L * .12), (.03, cz0 + L * .35), (.042, cz0 + L * .62), (.05, cz0 + L * .8),
            (.052, cz0 + L * .9), (.045, cz0 + L * .97), (.022, cz0 + L * 1.0), (.009, cz0 + L * 1.02)]
    place("Canopy%d" % i, lambda n: G.lathe_uv(n, prof, seg=16, paint=canopy_p, scallop=(8, .14)))
    # rib tips peeking out at the top of the canopy
    for k in range(8):
        b = 2 * math.pi * k / 8
        r_ = .044
        place("Tip%d_%d" % (i, k), lambda n: dv4.sphere(n, .005, loc=(math.cos(b) * r_, math.sin(b) * r_, cz0 + L * .94), seg=5, rings=3, paint=steel_p))
    # upper shaft to the handle
    top = cz0 + L * 1.02
    place("Shaft%d" % i, lambda n: dv4.tube(n, [(0, 0, top - .02), (0, 0, h - .09)], radius=.0055, res=6, paint=steel_p, kind="POLY", resolution=1))
    # crook handle: rises, curls over 180 degrees and ends slightly downward (wood)
    pts = [(0, 0, h - .1), (0, 0, h - .055)]
    pts += dv4.spiral((-.034, 0, h - .055), .034, .034, .5, 5, a0=0.0, plane="XZ", ccw=True)[1:]
    pts += [(-.068, 0, h - .075)]
    place("Handle%d" % i, lambda n: dv4.tube(n, pts, radius=.011, res=8, paint=handle_p, resolution=2, taper=[(0, .85), (.3, 1.0), (1, .9)]))
    place("HandleCap%d" % i, lambda n: dv4.sphere(n, .012, loc=(-.068, 0, h - .077), seg=8, rings=6, paint=handle_p))
    # ferrule collar where the shaft meets the handle
    place("Collar%d" % i, lambda n: G.lathe_uv(n, [(.0055, h - .1), (.008, h - .098), (.008, h - .088), (.0055, h - .086)], seg=10, paint=steel_p))
    # strap button
    place("Button%d" % i, lambda n: dv4.sphere(n, .005, loc=(.0, .052, cz0 + L * .85), seg=6, rings=4, paint=steel_p))


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.18, light=.36)
    brass = G.paint_brass("Brass", hammered=.0)
    brass_d = G.paint_brass("BrassDark", base="A3782A", dark="5A3E10", light="E8C56A", hammered=.0)
    steel = G.paint_steel("Steel")
    wood = dv4.paint_wood("Handle", base="7A4A2A", dark="40230F", light="A8703F", scale=5.0, along="Z", edge="C08F5E", tint=.15)
    wood2 = dv4.paint_wood("Handle2", base="2B2420", dark="15100D", light="4A3B33", scale=5.0, along="Z", edge="6B5A4E", tint=.1)
    # ---- bucket: foot ring, waisted body swelling toward a rolled rim, two raised bands, ring handles
    prof = [(0, 0), (.11, 0), (.12, .006), (.122, .02), (.113, .03), (.108, .05), (.112, .14), (.12, .26), (.128, .36), (.132, .39),
            (.142, .405), (.145, .42), (.138, .432), (.126, .432), (.12, .415), (.116, .39), (.108, .26), (.1, .09), (.09, .05), (0, .05)]
    dv4.lathe("Bucket", prof, seg=24, paint=brass)
    dv4.torus("Band1", .1165, .009, loc=(0, 0, .13), seg=24, minor=6, paint=brass_d)
    dv4.torus("Band2", .1245, .009, loc=(0, 0, .30), seg=24, minor=6, paint=brass_d)
    for k in range(10):
        b = 2 * math.pi * k / 10 + .3
        dv4.sphere("Rivet%d" % k, .006, loc=(math.cos(b) * .1215, math.sin(b) * .1215, .215), seg=6, rings=4, paint=brass_d)
    # lion-ish ring handles: a boss and a hanging ring on each side (x = +/-)
    for sx in (-1, 1):
        dv4.sphere("Boss%d" % sx, .018, loc=(sx * .122, 0, .34), scale=(.6, 1, 1), seg=10, rings=6, paint=brass_d)
        dv4.torus("Ring%d" % sx, .026, .006, loc=(sx * .136, 0, .318), rot=(0, 90, 0), seg=16, minor=6, paint=brass_d)
    # inside: a dark drip tray so the bucket does not read as a solid
    dv4.cylinder("Tray", .095, .004, loc=(0, 0, .05), seg=24, paint=dv4.paint_flat("Tray", "2A2422", variation=.2))
    # ---- umbrellas
    sets = [
        (0, 35, 3.5, 1.04, "panels", dict(a="D74A3C", b="F4EFE4"), wood),
        (1, 125, 3.0, .98, "dots", dict(a="1F9A8E", dots="F4EFE4"), wood2),
        (2, 215, 3.8, 1.07, "panels", dict(a="1D2B4F", b="E0B040"), wood),
        (3, 305, 3.2, 1.00, "stripes", dict(a="EE8FAE", b="1D2B4F"), wood2),
    ]
    for i, az, tilt, h, pattern, cols, hp in sets:
        cp = G.paint_canopy("Canopy%d" % i, pattern=pattern, strap="2A2E3A" if pattern != "panels" or i == 0 else "E0B040", **cols)
        umbrella(i, az, tilt, h, cols, pattern, hp, cp, steel)
    return {"name": "UmbrellaStand", "tex": 1024, "budget": 6000, "floor": "F4EFE4"}
