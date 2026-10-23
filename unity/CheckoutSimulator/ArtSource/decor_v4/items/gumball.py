"""gumball: classic cast-iron gumball machine - fluted navy pedestal with gold rings, glossy red cast body with chrome bands,
coin mechanism (plate, turning knob, slot) and chute door on the front (+Y), glass globe full of gumballs, chrome crown.
Footprint half .22 x .22, height <= 1.5."""
import os, sys, math
import dv4
from dv4 import RNG, MATH, MIX, RAMP, NOISE, SMOOTH, ATTR
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_B as lib

lib.install_fixes()

CONFIG = {"floor": "F4EFE4", "seed": 7}


def paint_candy(name="Candy"):
    cols = ("E8392B", "F5B000", "1E8FD0", "4FB030", "F0569C", "FFFFFF", "7A4BD6", "FF7A00")
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        stops = [(i / (len(cols) - 1), h) for i, h in enumerate(cols)]
        col = RAMP(nt, rnd, stops, "CONSTANT")
        hl = SMOOTH(nt, c.nz, .3, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, .3), col, "FFFFFF")
        sh = SMOOTH(nt, c.nz, -.2, -.9)
        return MIX(nt, MATH(nt, "MULTIPLY", sh, .3), col, "000000")
    return dv4.paint(name, r, k_ao=.25, k_light=.25)


def paint_body(name="RedBody"):
    """Glossy red enamel with a cream star on each side (faces +/-X)."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 8.0, 2.0)
        col = RAMP(nt, mot, [(.3, "B8322A"), (.7, "DA4336")])
        hl = SMOOTH(nt, c.nz, .2, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, .4), col, "FF8E7A")
        side = MATH(nt, "MAXIMUM", lib.face_mask(c, "x", 1.0, .5, .85), lib.face_mask(c, "x", -1.0, .5, .85))
        u, v = lib.rel(c, 0.0, .81, "yz")
        star = lib.m_star(c, u, v, .055, n=5)
        col = MIX(nt, MATH(nt, "MULTIPLY", star, side), col, "FFE59A")
        ring = lib.m_ring(c, u, v, .072, .064)
        col = MIX(nt, MATH(nt, "MULTIPLY", ring, side), col, "FFE59A")
        return col
    return dv4.paint(name, r, edge="FF9F8C", edge_k=.8, edge_r=.005)


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.2, light=.36)
    navy = dv4.paint_iron("Navy", base="182542", mid="2B3F6E", edge="8FA3D0", rust="000000", rust_amt=0.0)
    gold = dv4.paint_gold("Gold")
    chrome = lib.paint_chrome("Chrome")
    red = paint_body("RedBody")
    candy = paint_candy("Candy")
    dark = dv4.paint_flat("Dark", "1B1F24", variation=.0)

    # ---- pedestal: scalloped foot, gold rope ring, fluted column, gold collar
    dv4.lathe("Foot", [(0, 0), (.195, 0), (.215, .012), (.21, .04), (.185, .055), (.14, .07), (.1, .085), (.085, .1), (0, .1)],
              seg=30, paint=navy, scallop=(10, .05))
    dv4.torus("FootRing", .095, .011, loc=(0, 0, .1), seg=24, minor=4, paint=gold)
    dv4.lathe("Column", [(.08, .1), (.072, .22), (.066, .42), (.07, .56), (.085, .62)], seg=30, paint=navy, scallop=(10, .07), cap=False)
    dv4.lathe("Collar", [(.078, .62), (.1, .635), (.105, .655), (.09, .675), (0, .675)], seg=24, paint=gold)
    # ---- chrome cup, red cast body with chrome bands, decorative rivets
    dv4.lathe("Cup", [(0, .675), (.13, .675), (.16, .69), (.168, .72), (.168, .745), (.16, .755), (0, .755)], seg=24, paint=chrome)
    dv4.lathe("Body", [(.155, .755), (.165, .78), (.168, .86), (.168, .92), (.162, .95), (.15, .965)], seg=28, paint=red, cap=False)
    dv4.torus("BandLo", .166, .011, loc=(0, 0, .758), seg=24, minor=4, paint=chrome)
    dv4.torus("BandHi", .158, .011, loc=(0, 0, .962), seg=24, minor=4, paint=chrome)
    # ---- coin mechanism on the front (+Y): chrome plate, slot, turning knob with handle, chute door with a flap
    dv4.cube("Plate", (.115, .022, .095), loc=(0, .165, .895), paint=chrome, bevel=.008, segs=2)
    dv4.cube("Slot", (.03, .006, .004), loc=(0, .178, .93), paint=dark, bevel=.001, segs=1)
    dv4.cylinder("Knob", .03, .018, loc=(0, .176, .885), rot=(-90, 0, 0), seg=14, paint=chrome, bevel=.004)
    dv4.cube("Handle", (.056, .012, .013), loc=(0, .196, .885), rot=(0, 25, 0), paint=chrome, bevel=.004, segs=1)
    dv4.sphere("HandleTip", .009, loc=(.027, .196, .897), seg=8, rings=5, paint=dark)
    dv4.cube("ChuteFrame", (.08, .014, .055), loc=(0, .164, .80), rot=(-8, 0, 0), paint=chrome, bevel=.005, segs=2)
    dv4.cube("ChuteFlap", (.062, .006, .036), loc=(0, .173, .797), rot=(-16, 0, 0), paint=dark, bevel=.002, segs=1)
    dv4.cube("FlapLip", (.05, .006, .006), loc=(0, .176, .783), rot=(-16, 0, 0), paint=chrome, bevel=.002, segs=1)
    # ---- globe: chrome seat, glass sphere, gumballs, chrome crown with finial
    dv4.lathe("Seat", [(0, .965), (.14, .965), (.178, .975), (.186, .995), (.18, 1.015), (.15, 1.025), (0, 1.025)], seg=24, paint=chrome)
    GC, GR = 1.195, .185
    dv4.sphere("A_Glass", GR, loc=(0, 0, GC), seg=20, rings=12, paint=None, mat_override="G_Glass")
    pts = []
    rb = .031
    tries = 0
    while len(pts) < 36 and tries < 6000:
        tries += 1
        x, y, z = RNG.uniform(-.17, .17), RNG.uniform(-.17, .17), GC - .165 + .25 * RNG.random() ** 1.5
        if math.sqrt(x * x + y * y + (z - GC) ** 2) > GR - rb - .006:
            continue
        if any((x - p[0]) ** 2 + (y - p[1]) ** 2 + (z - p[2]) ** 2 < (2 * rb * .93) ** 2 for p in pts):
            continue
        pts.append((x, y, z))
    for i, p in enumerate(pts):
        dv4.sphere("Gum%d" % i, rb, loc=p, seg=7, rings=5, paint=candy)
    dv4.lathe("Crown", [(.1, GC + GR - .025), (.118, GC + GR - .01), (.118, GC + GR + .01), (.1, GC + GR + .03), (.06, GC + GR + .045),
                        (.045, GC + GR + .06), (.03, GC + GR + .075), (0, GC + GR + .08)], seg=24, paint=chrome)
    dv4.torus("CrownRing", .105, .008, loc=(0, 0, GC + GR + .02), seg=24, minor=4, paint=gold)
    dv4.sphere("Finial", .028, loc=(0, 0, GC + GR + .098), seg=12, rings=8, paint=gold)
    return {"name": "Gumball", "tex": 1024, "budget": 6000, "floor": "F4EFE4"}
