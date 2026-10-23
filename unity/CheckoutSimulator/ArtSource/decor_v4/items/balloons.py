"""balloons: festive bouquet of eleven glossy latex balloons (teardrop shapes with knots and curly ribbon tails), each on its own
"Anim Bob" node, tied with cream ribbons to a gold polka-dot gift-box weight with a red ribbon and bow.
Footprint half .34 x .34, height <= 2.3 (Blender Z up, front +Y)."""
import os, sys, math
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_A as lib

CONFIG = {"floor": "F4EFE4", "seed": 21}

COLS = {
    "red": ("D74A3C", "F49080", "8E2318"),
    "gold": ("EDB13A", "FFE08A", "9A7118"),
    "teal": ("1FA89A", "7ADCCF", "0E5C55"),
    "pink": ("F285AA", "FFC9DA", "B0587A"),
    "orange": ("EC862E", "FFB877", "A6531A"),
    "blue": ("3E8FD6", "93CBF4", "1F5A95"),
    "cream": ("F7F1E4", "FFFFFF", "C2B59E"),
}

K = 1.13
PROFILE = [(r * K, z * K) for r, z in [(0, -.027), (.011, -.027), (.015, -.014), (.010, -.003), (.022, .006), (.052, .022), (.086, .05),
           (.112, .09), (.127, .14), (.13, .19), (.122, .245), (.1, .29), (.065, .322), (.03, .338), (0, .343)]]


def build():
    dv4.FINISH.update(ao=.5, ao_dist=.2, light=.3)
    paints = {k: lib.paint_latex("Latex" + k.capitalize(), base=v[0], light=v[1], dark=v[2]) for k, v in COLS.items()}
    wrap = lib.paint_wrap("Wrap", base="E0B040", dot="F4EFE4", pitch=.046, half=.009)
    red = dv4.paint_flat("Ribbon", "D74A3C", dark="8E2318", variation=.25, scale=14.0, edge="F49080", edge_r=.004)
    string = dv4.paint_flat("String", "FBF1D2", dark="D9C89A", variation=.15, scale=30.0, k_ao=.2, k_light=.15)

    # ---- weight: gift box with a red ribbon cross and a bow on top
    bz = .17
    dv4.cube("Box", (.22, .22, bz), loc=(0, 0, bz / 2), paint=wrap, bevel=.012, segs=3)
    dv4.cube("BandX", (.236, .036, .007), loc=(0, 0, bz + .001), paint=red, bevel=.002, segs=1)
    dv4.cube("BandY", (.036, .236, .007), loc=(0, 0, bz + .001), paint=red, bevel=.002, segs=1)
    for s in (1, -1):
        dv4.cube("BandSX", (.007, .036, bz + .002), loc=(.113 * s, 0, bz / 2), paint=red, bevel=.002, segs=1)
        dv4.cube("BandSY", (.036, .007, bz + .002), loc=(0, .113 * s, bz / 2), paint=red, bevel=.002, segs=1)
    for az in (0, 90):
        a = math.radians(az)
        for s in (1, -1):
            c = (math.cos(a) * .036 * s, math.sin(a) * .036 * s, bz + .034)
            dv4.torus("Loop", .03, .011, loc=c, rot=(90, 0, az), seg=16, minor=6, paint=red)
    dv4.sphere("Knot", .02, loc=(0, 0, bz + .028), scale=(1, 1, .8), seg=12, rings=8, paint=red)
    for s in (1, -1):
        dv4.cube("Tail", (.03, .006, .07), loc=(.055 * s, .065 * s, bz - .02), rot=(10 * s, 0, 25 * s), paint=red, bevel=.002, segs=1)

    # ---- balloons: lower ring of six, middle ring of four, one on top
    spots = []
    for i in range(5):
        a = math.radians(20 + i * 72)
        spots.append((math.cos(a) * .157, math.sin(a) * .157, 1.28 + (i % 2) * .12, 9, math.degrees(a)))
    for i in range(4):
        a = math.radians(56 + i * 90)
        spots.append((math.cos(a) * .105, math.sin(a) * .105, 1.58 + (i % 2) * .07, 7, math.degrees(a)))
    spots.append((0, 0, 1.84, 0, 0))
    names = ["red", "gold", "teal", "pink", "blue", "orange", "cream", "red", "teal", "gold"]
    for k, ((x, y, z, tilt, az), cname) in enumerate(zip(spots, names)):
        node = "Anim Bob" if k == 0 else "Anim Bob.%03d" % k
        rot = (0, tilt, az)
        dv4.lathe("Balloon%d" % k, PROFILE, seg=16, loc=(x, y, z), rot=rot, paint=paints[cname], out=node)
        dv4.pivot(node, (x, y, z + .19))
        # curly ribbon tail hanging from the knot (moves with the balloon)
        tail = lib.helix((x + .008, y, z - .03), .011, 1.75, .065, n=8, a0=k * 1.1, r1=.016)
        dv4.tube("Curl%d" % k, tail, radius=.0028, res=4, paint=string, out=node, resolution=2)
        # ribbon from the bow up into the balloon neck (ends hidden inside the balloon)
        top = (x, y, z + .05)
        mid = (x * .45 + RNG.uniform(-.02, .02), y * .45 + RNG.uniform(-.02, .02), (z + bz + .04) * .5)
        dv4.tube("String%d" % k, [(0, 0, bz + .03), mid, top], radius=.0045, res=4, paint=string, resolution=6)
    return {"name": "Balloons", "tex": 1024, "budget": 10000, "floor": "F4EFE4"}
