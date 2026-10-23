"""carousel: mini merry-go-round. Static cream-stone step ring with a chaser of bulbs (2 "Anim Blink" phases); everything
else turns on "Anim Spin": plank platform with a gold rim, navy/cream panelled centre column with gold rings, four painted
galloping horses on gold poles, red/cream striped scalloped canopy with gold ribs, a ring of lit bulbs and a finial.
Footprint half 1.30 x 1.30, height <= 2.6 (Blender Z up; radially symmetric)."""
import math, os, sys
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_J as J

CONFIG = {"floor": "C9C3B8", "seed": 25}

RB = 1.29         # base ring outer radius
RP = 1.08         # platform radius
ZP = .26          # platform top
RCAN = 1.22       # canopy radius
ZCAN = 1.86       # canopy eave
SPIN = "Anim Spin"


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.3, light=.36)
    stone = J.paint_cream_stone("Base", blocks=(28, [.08], .0, .17))
    deck = J.paint_planks("Deck", base="C08048", dark="6E4428", light="E4B172", width=.11, axis="X", along="Y", groove="3A2010", scale=2.5)
    gold = dv4.paint_gold("Gold")
    gold_rib = dv4.paint_gold("GoldRib", k_ao=.1, k_light=.3)
    navy = J.paint_gloss("Navy", "1D2B4F", dark="0E1730", light="4A5C8C", variation=.15, highlight=.22)
    cream = J.paint_gloss("Cream", "F4EFE4", dark="C9BFA8", light="FFFFFF", variation=.1, highlight=.15)
    red = J.paint_gloss("Red", "D74A3C", dark="8E2A20", light="F28A7C", variation=.12)
    teal = J.paint_gloss("Teal", "1F9A8E", dark="146A61", light="5CC7BA", variation=.12)
    pink = J.paint_gloss("Pink", "EE8FAE", dark="C2567C", light="FFC9DA", variation=.1)
    canopy = J.paint_stripes("Canopy", cols=("D74A3C", "F4EFE4"), n=16, shade=.15, soft=.003, k_ao=.15, ao_dist=.05)
    canopy_in = J.paint_stripes("CanopyIn", cols=("F4EFE4", "D74A3C"), n=16, shade=.1, soft=.003, k_ao=.4)
    valance = J.paint_stripes("Valance", cols=("F4EFE4", "D74A3C"), n=16, shade=.1, soft=.003)
    coats = [J.paint_dapple("Dapple"), J.paint_gloss("Chestnut", "B5653A", dark="6E3A1E", light="E39A6A", variation=.12, highlight=.25),
             J.paint_gloss("Palomino", "E8C27A", dark="A8783A", light="FFF0C0", variation=.12, highlight=.25),
             J.paint_gloss("Black", "2F2F38", dark="121218", light="7A7A8C", variation=.1, highlight=.35)]
    manes = [J.paint_gloss("ManeGold", "E0B040", dark="A8781F", light="FFE38A", variation=.1), J.paint_gloss("ManeCream", "F4EFE4", dark="C9BFA8", light="FFFFFF", variation=.1),
             J.paint_gloss("ManeBrown", "6B4128", dark="3B2113", light="A5744A", variation=.1), J.paint_gloss("ManeNavy", "1D2B4F", dark="0E1730", light="4A5C8C", variation=.1)]
    saddles = [red, teal, navy, pink]
    blankets = [gold, pink, red, teal]
    hoof = J.paint_gloss("Hoof", "3A3A42", dark="1A1A20", light="8A8A96", variation=.1)
    eye = J.paint_gloss("Eye", "1A1A1A", dark="000000", light="6A6A6A", variation=.0, highlight=.5)
    socket = dv4.paint_iron("Socket", base="2A2F35", mid="3F474F", edge="7C868F", rust_amt=0.0)

    # ---- static base: two cream-stone steps with a gold nosing; bulb chaser around the top step
    dv4.lathe("Base", [(0, 0), (RB, 0), (RB, .08), (RB - .09, .08), (RB - .09, .17), (RP + .03, .17), (RP + .03, .19), (0, .19)], seg=40, paint=stone)
    dv4.torus("Nosing", RB - .09, .012, loc=(0, 0, .17), seg=40, minor=4, paint=gold)
    for i in range(20):
        a = math.radians(i * 18 + 9)
        out = "Anim Blink" + ("" if i % 2 == 0 else ".001")
        p = (math.cos(a) * (RB - .045), math.sin(a) * (RB - .045), .08)
        dv4.lathe("BaseCap%d" % i, [(0, 0), (.02, 0), (.018, .012), (0, .012)], seg=4, loc=p, paint=socket)
        dv4.sphere("BaseBulb%d" % i, .026, loc=(p[0], p[1], .105), seg=6, rings=4, paint=None, out=out, mat_override="E_FFE4A0")
    dv4.pivot("Anim Blink", (0, 0, .1)); dv4.pivot("Anim Blink.001", (0, 0, .1))

    # ---- rotating platform: plank deck, gold rim, red skirt band
    dv4.pivot(SPIN, (0, 0, 0))
    dv4.lathe("Platform", [(0, .19), (RP - .02, .19), (RP, .21), (RP, ZP), (0, ZP)], seg=40, paint=deck, out=SPIN)
    dv4.lathe("Skirt", [(RP + .005, .195), (RP + .02, .205), (RP + .02, ZP - .015), (RP + .005, ZP)], seg=40, paint=red, out=SPIN, cap=False)
    dv4.torus("Rim", RP + .01, .018, loc=(0, 0, ZP), seg=40, minor=5, paint=gold, out=SPIN)

    # ---- centre column: navy drum with 8 cream panels (gold-framed), rings, a cove up to the canopy
    dv4.lathe("Column", [(0, ZP), (.26, ZP), (.27, ZP + .04), (.22, ZP + .08), (.20, ZP + .12), (.20, 1.56), (.23, 1.63), (.30, 1.72), (.34, 1.80), (.34, ZCAN), (0, ZCAN)],
              seg=24, paint=navy, out=SPIN)
    for z in (ZP + .10, .92, 1.57):
        dv4.torus("ColRing%d" % int(z * 100), .205, .018, loc=(0, 0, z), seg=24, minor=5, paint=gold, out=SPIN)
    for i in range(8):
        a = math.radians(i * 45)
        c, s_ = math.cos(a), math.sin(a)
        r = .208
        dv4.cube("Panel%d" % i, (.09, .02, .5), loc=(c * r, s_ * r, 1.28), rot=(0, 0, i * 45 + 90), paint=cream, bevel=.008, segs=1, out=SPIN)
        dv4.cube("PanelFrame%d" % i, (.11, .012, .54), loc=(c * (r - .006), s_ * (r - .006), 1.28), rot=(0, 0, i * 45 + 90), paint=gold, bevel=0, out=SPIN)
        # a little star pictogram on every panel (red on cream)
        if True:
            dv4.lathe("Star%d" % i, [(0, 0), (.036, 0), (.036, .012), (0, .012)], seg=10, loc=(c * (r + .012), s_ * (r + .012), 1.30), rot=(0, 90, i * 45), paint=red, out=SPIN,
                      scallop=(5, .45))

    # ---- canopy: striped cone with a bell curve, scalloped valance, gold ribs and bulbs, finial on top
    prof = [(0, ZCAN - .01), (RCAN, ZCAN - .01), (RCAN + .02, ZCAN + .03), (RCAN - .03, ZCAN + .1), (.95, ZCAN + .2), (.68, ZCAN + .32), (.42, ZCAN + .43),
            (.2, ZCAN + .51), (.06, ZCAN + .55), (0, ZCAN + .56)]
    dv4.lathe("Canopy", prof, seg=40, paint=canopy, out=SPIN, cap=False)
    dv4.lathe("Ceiling", [(0, ZCAN - .02), (RCAN - .02, ZCAN - .02), (RCAN - .02, ZCAN), (0, ZCAN)], seg=40, paint=canopy_in, out=SPIN)
    dv4.torus("EaveRim", RCAN + .02, .022, loc=(0, 0, ZCAN + .02), seg=40, minor=5, paint=gold, out=SPIN)
    J.valance_ring("Valance", RCAN + .02, ZCAN + .01, drop=.11, n=16, per=5, paint=valance, out=SPIN, thickness=.01, flare=.02)
    for i in range(16):
        a = math.radians(i * 22.5 + 11.25)
        c, s_ = math.cos(a), math.sin(a)
        pts = [(c * r, s_ * r, z + .018) for r, z in ((RCAN - .01, ZCAN + .035), (.8, ZCAN + .25), (.42, ZCAN + .42), (.04, ZCAN + .54))]
        dv4.tube("Rib%d" % i, pts, radius=.014, res=6, paint=gold_rib, kind="POLY", resolution=1, out=SPIN)
    for i in range(20):
        a = math.radians(i * 18)
        p = (math.cos(a) * (RCAN - .02), math.sin(a) * (RCAN - .02), ZCAN + .05)
        dv4.sphere("CanBulb%d" % i, .028, loc=(p[0], p[1], ZCAN + .07), seg=6, rings=4, paint=None, out=SPIN, mat_override="E_FFE4A0")
    dv4.lathe("Finial", [(0, ZCAN + .54), (.07, ZCAN + .54), (.075, ZCAN + .565), (.04, ZCAN + .59), (.03, ZCAN + .615), (.05, ZCAN + .635), (0, ZCAN + .65)], seg=12, paint=gold, out=SPIN)
    dv4.sphere("FinialBall", .04, loc=(0, 0, ZCAN + .675), seg=12, rings=8, paint=gold, out=SPIN)
    dv4.lathe("Spike", [(0, ZCAN + .70), (.012, ZCAN + .70), (0, ZCAN + .735)], seg=8, paint=gold, out=SPIN)

    # ---- horses on gold poles (alternating low / high)
    RH = .70
    for i in range(4):
        yaw = i * 90                       # faces along the circle (counter-clockwise gallop)
        a = math.radians(i * 90)
        hx, hy = math.cos(a) * RH, math.sin(a) * RH
        hz = ZP + (.06 if i % 2 == 0 else .14)
        J.horse("H%d" % i, (hx, hy, hz), yaw, coats[i], manes[i], saddles[i], blankets[i], hoof, eye, gold, out=SPIN, s=1.12)
        dv4.tube("Pole%d" % i, [(hx, hy, ZP - .01), (hx, hy, ZCAN)], radius=.02, res=10, paint=gold, kind="POLY", resolution=1, out=SPIN)
        dv4.lathe("PoleFoot%d" % i, [(0, 0), (.045, 0), (.04, .02), (.028, .035), (0, .035)], seg=12, loc=(hx, hy, ZP), paint=gold, out=SPIN)
        dv4.lathe("PoleTop%d" % i, [(0, 0), (.028, 0), (.04, .015), (.045, .035), (0, .035)], seg=12, loc=(hx, hy, ZCAN - .055), paint=gold, out=SPIN)
    return {"name": "Carousel", "tex": 1024, "budget": 15000, "floor": "C9C3B8"}
