"""watermelon-pile: rustic wooden market bin (corner posts, slatted sides, top rails) heaped with striped watermelons on a
bed of straw, two cut halves showing red flesh with seeds, a small sign with a melon-slice pictogram on the front rail.
Footprint half .72 x .56, height <= 1.3 (front +Y)."""
import os, sys, math
import dv4
from dv4 import RNG, MATH, MIX, RAMP, NOISE, SMOOTH
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_B as lib

lib.install_fixes()

CONFIG = {"floor": "F4EFE4", "seed": 21}


def paint_sign(name, center):
    """Cream card with a watermelon-slice pictogram (half disc: green rind, pale ring, red flesh with seed dots)."""
    def r(c):
        nt = c.nt
        u, v = lib.rel(c, center[0], center[1], "xz")
        col = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 8.0, 2.0), .1), "F6EEDC", "000000")
        front = lib.face_mask(c, "y", 1.0, .5, .9)
        v2 = MATH(nt, "ADD", v, .028)
        lower = SMOOTH(nt, v2, .003, -.003)
        R = .062
        d = lib.dist2(c, u, v2)
        rind = MATH(nt, "MULTIPLY", lib.inside(c, d, R), lower)
        col = MIX(nt, MATH(nt, "MULTIPLY", rind, front), col, "3E8A33")
        pale = MATH(nt, "MULTIPLY", lib.inside(c, d, R * .86), lower)
        col = MIX(nt, MATH(nt, "MULTIPLY", pale, front), col, "EDF3D2")
        flesh = MATH(nt, "MULTIPLY", lib.inside(c, d, R * .76), lower)
        col = MIX(nt, MATH(nt, "MULTIPLY", flesh, front), col, "E8433F")
        seeds = None
        for (su, sv) in ((-.02, -.03), (.0, -.045), (.02, -.028), (-.008, -.015), (.012, -.012)):
            m = lib.m_circle(c, MATH(nt, "SUBTRACT", u, su), MATH(nt, "SUBTRACT", v2, sv), .0035, .0015)
            seeds = m if seeds is None else MATH(nt, "MAXIMUM", seeds, m)
        col = MIX(nt, MATH(nt, "MULTIPLY", seeds, front), col, "2B1A12")
        return col
    return dv4.paint(name, r, edge="FFFFFF", edge_k=.5, edge_r=.003)


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.25, light=.34)
    post = dv4.paint_wood("Post", base="8F5A33", dark="4A2E18", light="B8834F", scale=5.0, along="Z", edge="C89A68", tint=.15)
    slat = dv4.paint_wood("Slat", base="C48A4C", dark="7A4C27", light="E6B878", scale=4.0, dist=2.5, along="X", edge="F0CD98", tint=.35)
    slat_y = dv4.paint_wood("SlatY", base="C48A4C", dark="7A4C27", light="E6B878", scale=4.0, dist=2.5, along="Y", edge="F0CD98", tint=.35)
    rail = dv4.paint_wood("Rail", base="A86B3B", dark="5E3A1D", light="D9A264", scale=4.0, along="X", edge="EBC18A", tint=.2)
    straw = lib.paint_straw("Straw")
    melon = lib.paint_melon("Melon", stripes=11)
    seedp = dv4.paint_flat("Seed", "2B1A12", variation=.0)
    stem = dv4.paint_flat("Stem", "7A5A2E", dark="3E2B12", variation=.5, scale=30.0)

    # ---- bin: posts, slatted sides with gaps, floor, top rails
    for x in (-.65, .65):
        for y in (-.485, .485):
            dv4.cube("Post%s%s" % (x, y), (.075, .075, .64), loc=(x, y, .32), paint=post, bevel=.008, segs=2)
            dv4.cube("Cap%s%s" % (x, y), (.09, .09, .025), loc=(x, y, .655), paint=post, bevel=.006, segs=2)
    for z in (.10, .27, .44):
        for y in (-.515, .515):
            dv4.cube("SlatF%s%s" % (z, y), (1.30, .03, .13), loc=(0, y, z), paint=slat, bevel=.006, segs=2)
        for x in (-.675, .675):
            dv4.cube("SlatS%s%s" % (z, x), (.03, .95, .13), loc=(x, 0, z), paint=slat_y, bevel=.006, segs=2)
    dv4.cube("Floor", (1.3, .96, .03), loc=(0, 0, .505), paint=post, bevel=.004, segs=1)
    for y in (-.515, .515):
        dv4.cube("RailF%s" % y, (1.42, .075, .045), loc=(0, y, .60), paint=rail, bevel=.01, segs=3)
    for x in (-.675, .675):
        dv4.cube("RailS%s" % x, (.075, 1.08, .045), loc=(x, 0, .60), paint=rail, bevel=.01, segs=3)
    # ---- straw bed (displaced patch) + tufts spilling over the rails
    bed = dv4.patch("Straw", 1.30, .98, 14, 12, loc=(0, 0, .55), paint=straw)
    dv4.mod_displace(bed, strength=.06, size=.12, mid=.45)
    for i in range(10):
        x = RNG.uniform(-.6, .6); y = RNG.choice((-.5, .5)); s = 1 if y > 0 else -1
        pts = [(x, y - s * .12, .60), (x + RNG.uniform(-.03, .03), y + s * .03, .64), (x + RNG.uniform(-.05, .05), y + s * .07, .57)]
        dv4.tube("Tuft%d" % i, pts, radius=.006, res=4, paint=straw, resolution=3, taper=[(0, 1.0), (1, .5)])
    for i in range(6):
        y = RNG.uniform(-.4, .4); x = RNG.choice((-.65, .65)); s = 1 if x > 0 else -1
        pts = [(x - s * .1, y, .60), (x + s * .03, y + RNG.uniform(-.03, .03), .64), (x + s * .07, y + RNG.uniform(-.05, .05), .57)]
        dv4.tube("TuftS%d" % i, pts, radius=.006, res=4, paint=straw, resolution=3, taper=[(0, 1.0), (1, .5)])
    # ---- the mound: three layers of striped melons (long axis horizontal, random yaw), stem nubs on the poles
    melons = [((-.42, -.22, .70), 0), ((0, -.24, .70), 40), ((.42, -.22, .70), 100), ((-.40, .22, .70), 70), ((.02, .24, .70), 150), ((.42, .22, .70), 20),
              ((-.22, .0, .95), 120), ((.22, .0, .95), 30), ((0, .0, 1.145), 80)]
    for i, (p, yaw) in enumerate(melons):
        r = .165 * RNG.uniform(.96, 1.04)
        sc = (RNG.uniform(1.22, 1.3), 1.0, 1.0)
        tilt = RNG.uniform(-6, 6)
        lib.sphere_attr("Melon%d" % i, r, loc=p, scale=sc, rot=(tilt, 0, yaw), seg=18, rings=11, paint=melon, axis="X")
        a = math.radians(yaw); L = r * sc[0] - .004
        dv4.sphere("Stem%d" % i, .011, loc=(p[0] + math.cos(a) * L, p[1] + math.sin(a) * L, p[2] + .002), seg=7, rings=5, paint=stem, scale=(1.4, 1, 1), rot=(0, 0, yaw))
    # ---- cut halves: one flat on the front right, one tilted on the front left; red flesh with painted seeds
    for j, (p, tilt, yaw) in enumerate((((.40, .40, .83), (-8, 6), 0), ((-.46, .38, .84), (-14, -10), 0))):
        R = .16
        cz = p[2]
        rind = lib.paint_melon_pos("Rind%d" % j, p, stripes=11)
        flesh = lib.paint_flesh("Flesh%d" % j, p, R)
        prof = [(R * math.cos(math.radians(a)), -R * math.sin(math.radians(a))) for a in (0, 15, 30, 45, 60, 75, 90)]
        prof[-1] = (0, -R)
        dv4.lathe("Half%d" % j, prof, seg=26, loc=p, rot=(tilt[0], tilt[1], yaw), paint=rind, cap=False)
        dv4.patch("Face%d" % j, R * 2, R * 2, 6, 6, loc=p, rot=(tilt[0], tilt[1], yaw), paint=flesh, disk=True)
    # ---- sign hanging on the front rail: cream card with a melon-slice pictogram, two strings
    sc = (0.0, .552, .49)
    signp = paint_sign("Sign", (sc[0], sc[2]))
    dv4.cube("Sign", (.22, .010, .15), loc=sc, paint=signp, bevel=.012, segs=3)
    for x in (-.08, .08):
        dv4.tube("String%s" % x, [(x, .548, .56), (x, .556, .60)], radius=.003, res=4, paint=straw, kind="POLY", resolution=1)
    return {"name": "WatermelonPile", "tex": 1024, "budget": 10000, "floor": "F4EFE4"}
