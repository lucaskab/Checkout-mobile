"""gazebo: octagonal bandstand - cream-stone plinth with a plank deck and front steps, ornate cast-iron columns with scroll
brackets and scrollwork railings, pointed shingled roof with gold ribs and finial, string lights (3 "Anim Blink" phases).
Footprint half 1.50 x 1.50, height <= 3.2 (Blender: steps face the customer at +Y)."""
import math, os, sys
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_J as J

CONFIG = {"floor": "C9C3B8", "seed": 24}

RD = 1.25         # deck circumradius (octagon vertices)
ZD = .36          # deck top
RC = 1.16         # column circle
ZC = 2.30         # column top / eave
RR = 1.48         # roof circumradius at the eave
ZA = 3.05         # roof apex
ROT = 22.5        # octagon rotated so flats face +-X / +-Y


def vert(i, r, z, rot=ROT):
    a = math.radians(rot + i * 45)
    return (math.cos(a) * r, math.sin(a) * r, z)


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.3, light=.36)
    stone = J.paint_cream_stone("Plinth", blocks=(24, [.12, .24], .0, .3))
    deck = J.paint_planks("Deck", base="B9743F", dark="6B4128", light="DDA55F", width=.13, axis="X", along="Y", groove="3A2010", scale=2.5)
    step = dv4.paint_wood("Step", base="B06A37", dark="5A3418", light="DDA55F", along="X", scale=3.0, tint=.2)
    iron = dv4.paint_iron("Iron", base="1E2A33", mid="36444F", edge="9AA7B0", rust_amt=.2)
    iron_g = dv4.paint_iron("IronGreen", base="17655D", mid="1F9A8E", edge="8ED3C9", rust="7A4423", rust_amt=.15)
    gold = dv4.paint_gold("Gold")
    shingle = J.paint_shingles("Shingles", base="C4613F", dark="8A3E2A", light="E3876A", gap="4A2218", row_h=.125, n_around=44, z0=ZC + .02)
    cream = J.paint_gloss("Cream", "F4EFE4", dark="C9BFA8", light="FFFFFF", variation=.1, highlight=.15)
    ceiling = J.paint_painted_wood("Ceiling", base="F1E7D2", dark="CDBE9E", light="FFFBF2", along="X", wear="D9C9A8", wear_amt=.2)
    wire = dv4.paint_iron("Wire", base="1A1A1A", mid="2E2E2E", edge="4A4A4A", rust_amt=0.0)
    socket = dv4.paint_iron("Socket", base="2A2F35", mid="3F474F", edge="7C868F", rust_amt=0.0)

    # ---- plinth (stone, 8-sided), deck slab (planks), fascia, front steps
    dv4.lathe("Plinth", [(0, 0), (RD + .05, 0), (RD + .07, .03), (RD + .05, .06), (RD, .06), (RD, ZD - .06), (0, ZD - .06)], seg=8, rot=(0, 0, ROT), paint=stone)
    dv4.lathe("Deck", [(0, ZD - .06), (RD + .02, ZD - .06), (RD + .02, ZD), (0, ZD)], seg=8, rot=(0, 0, ROT), paint=deck)
    # steps on the +Y flat (apothem of the octagon)
    ap = RD * math.cos(math.radians(22.5))
    for i in range(3):
        d = .10 * (i + 1); h = ZD - .09 * (i + 1)
        dv4.cube("Step%d" % i, (1.0 - i * .02, .11, .05), loc=(0, ap + d - .02, h), paint=step, bevel=.012, segs=2)
        dv4.cube("Riser%d" % i, (1.0 - i * .02, .05, .09), loc=(0, ap + d - .075, h - .07), paint=stone, bevel=.006, segs=1)
    # step handrails: a post at the bottom step, the rail sloping up to the deck, ending in a scroll; brass balls on top
    for sx in (-.52, .52):
        dv4.tube("StepPost%s" % sx, [(sx, ap + .30, 0), (sx, ap + .30, ZD + .40)], radius=.018, res=8, paint=iron, kind="POLY", resolution=1)
        dv4.sphere("StepBall%s" % sx, .032, loc=(sx, ap + .30, ZD + .42), seg=10, rings=7, paint=gold)
        rail = [(sx, ap + .30, ZD + .36), (sx, ap + .12, ZD + .62), (sx, ap - .02, ZD + .85)]
        rail += dv4.spiral((sx, ap - .08, ZD + .80), .06, .012, .8, 6, a0=math.radians(45), plane="YZ", ccw=True)[1:]
        dv4.tube("StepRail%s" % sx, rail, radius=.016, res=8, paint=iron, resolution=2)
        dv4.tube("StepRail2%s" % sx, [(sx, ap + .14, ZD - .14), (sx, ap + .14, ZD + .60)], radius=.012, res=6, paint=iron, kind="POLY", resolution=1)

    # ---- columns with base, capital and a scroll bracket toward the roof; railing between columns except the front
    for i in range(8):
        x, y, _ = vert(i, RC, 0)
        dv4.lathe("ColBase%d" % i, [(0, 0), (.085, 0), (.085, .05), (.065, .07), (.05, .1), (.045, .13), (0, .13)], seg=10, loc=(x, y, ZD), paint=iron)
        dv4.tube("Col%d" % i, [(x, y, ZD + .1), (x, y, ZC - .1)], radius=.038, res=12, paint=iron_g, kind="POLY", resolution=1)
        dv4.lathe("ColRing%d" % i, [(.04, 0), (.05, .01), (.05, .03), (.04, .04)], seg=12, loc=(x, y, ZD + .95), paint=gold, cap=False)
        dv4.lathe("Capital%d" % i, [(0, 0), (.045, 0), (.05, .04), (.07, .08), (.09, .12), (.09, .15), (0, .15)], seg=10, loc=(x, y, ZC - .16), paint=iron)
        # scroll brackets: two S-scrolls leaning inward under the eave (in the radial plane), one per side of the column
        a = math.radians(ROT + i * 45)
        ux, uy = -math.cos(a), -math.sin(a)                  # inward
        tx, ty = -uy, ux                                     # tangent
        for sg in (-1, 1):
            pts = []
            for k in range(5):
                t = k / 4
                r0 = .05 + t * .24
                zz = ZC - .17 - (1 - t) ** 1.6 * .32
                pts.append((x + tx * sg * r0, y + ty * sg * r0, zz))
            pts += dv4.spiral((x + tx * sg * .33, y + ty * sg * .33, ZC - .25), .06, .012, .85, 5, a0=math.radians(90), plane="XY", ccw=(sg > 0))[1:]
            dv4.tube("Bracket%d%d" % (i, sg), pts, radius=.015, res=6, paint=iron, resolution=1)
        # railing to the next column (skip the front side, which is between vertices 1 and 2 ... the +Y flat)
        j = (i + 1) % 8
        if i == 1:
            continue
        x2, y2, _ = vert(j, RC, 0)
        for zr, rr in ((ZD + .92, .02), (ZD + .14, .016)):
            dv4.tube("Rail%d_%d" % (i, int(zr * 100)), [(x, y, zr), (x2, y2, zr)], radius=rr, res=8, paint=iron, kind="POLY", resolution=1)
        for k in range(1, 6):
            t = k / 6
            px, py = x + (x2 - x) * t, y + (y2 - y) * t
            dv4.tube("Bal%d_%d" % (i, k), [(px, py, ZD + .14), (px, py, ZD + .92)], radius=.011, res=6, paint=iron, kind="POLY", resolution=1)
        # central ring + heart-like double scroll motif in the panel
        mx, my = (x + x2) / 2, (y + y2) / 2
        dv4.torus("Ring%d" % i, .09, .011, loc=(mx, my, ZD + .53), rot=(90, 0, math.degrees(math.atan2(y2 - y, x2 - x))), seg=16, minor=5, paint=gold)
        dv4.sphere("RingBall%d" % i, .02, loc=(mx, my, ZD + .53), seg=8, rings=6, paint=gold)

    # ---- roof: 8-sided shingled pyramid with a slight bell curve, cream ceiling, fascia, gold ribs, finial
    prof = [(0, ZC - .02), (RR, ZC - .02), (RR + .02, ZC + .02), (RR - .02, ZC + .08), (1.15, ZC + .22), (.82, ZC + .40), (.52, ZC + .56), (.26, ZC + .68),
            (.07, ZC + .74), (0, ZC + .75)]
    dv4.lathe("Roof", prof, seg=8, rot=(0, 0, ROT), paint=shingle)
    dv4.lathe("Ceiling", [(0, ZC - .03), (RR - .1, ZC - .03), (RR - .1, ZC - .01), (0, ZC - .01)], seg=8, rot=(0, 0, ROT), paint=ceiling)
    dv4.lathe("Fascia", [(RR + .03, ZC - .06), (RR + .04, ZC - .05), (RR + .04, ZC + .03), (RR + .03, ZC + .04)], seg=8, rot=(0, 0, ROT), paint=cream, cap=False)
    for i in range(8):
        a, b = vert(i, RR + .02, ZC + .01), vert((i + 1) % 8, RR + .02, ZC + .01)
        J.valance_line("Trim%d" % i, a, b, drop=.09, n=7, per=4, paint=cream, thickness=.012, flare=.0)
        pts = [vert(i, r, z) for r, z in ((RR + .01, ZC + .015), (1.15, ZC + .225), (.82, ZC + .405), (.52, ZC + .565), (.26, ZC + .685), (.04, ZC + .75))]
        dv4.tube("Rib%d" % i, pts, radius=.018, res=6, paint=gold, kind="POLY", resolution=1)
    dv4.lathe("Finial", [(0, ZC + .72), (.07, ZC + .72), (.075, ZC + .76), (.045, ZC + .79), (.035, ZC + .84), (.06, ZC + .88), (.02, ZC + .90), (0, ZC + .90)],
              seg=14, paint=gold)
    dv4.sphere("FinialBall", .045, loc=(0, 0, ZA + .07), seg=14, rings=10, paint=gold)
    dv4.lathe("Spike", [(0, ZA + .10), (.012, ZA + .10), (0, ZA + .15)], seg=8, paint=gold)

    # ---- string lights: swags under the eave between the columns, bulbs on 3 blink phases (chaser)
    n = 0
    for i in range(8):
        a, b = vert(i, RC + .02, ZC - .22), vert((i + 1) % 8, RC + .02, ZC - .22)
        pts = J.swag("Wire%d" % i, a, b, sag=.10, n=8, radius=.006, paint=wire)
        for k in (2, 4, 6):
            p = pts[k]
            out = "Anim Blink" + ("" if n % 3 == 0 else ".%03d" % (n % 3))
            J.bulb("Bulb%d" % n, (p[0], p[1], p[2] - .01), r=.022, out=out, color="FFE4A0", cap_paint=socket)
            n += 1
    for k in range(3):
        dv4.pivot("Anim Blink" + ("" if k == 0 else ".%03d" % k), (0, 0, ZC - .3))
    # a pendant lantern hanging from the roof centre (always lit, same E_ slot)
    dv4.tube("Chain", [(0, 0, ZC - .02), (0, 0, ZC - .32)], radius=.006, res=6, paint=wire, kind="POLY", resolution=1)
    dv4.lathe("Shade", [(0, 0), (.04, 0), (.09, -.06), (.2, -.14), (.2, -.16), (.17, -.16), (.1, -.1), (.06, -.06), (0, -.06)], seg=16, loc=(0, 0, ZC - .32), paint=iron_g)
    dv4.lathe("LampGlass", [(0, 0), (.055, 0), (.065, -.05), (.05, -.1), (0, -.12)], seg=12, loc=(0, 0, ZC - .36), paint=None, mat_override="E_FFE4A0")
    return {"name": "Gazebo", "tex": 1024, "budget": 15000, "floor": "C9C3B8", "sharp_angle": 42}
