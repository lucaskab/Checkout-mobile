"""flower-stand: florist corner (inside). Timber pergola with a pink scalloped valance and a festoon, three plank tiers across
the back full of zinc buckets with roses / tulips / peonies / daisies / lavender / hydrangea / sunflowers, wrapped kraft cones,
crates with terracotta pots in front, a wrapping counter with paper rolls, a chalkboard with flower drawings (no words).
Footprint half 1.13 x .71, height <= 2.45 (Blender: X across, front = +Y). 18 "Anim Sway" bouquets (pivot at the bucket mouth)."""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
import _lib_D as L
from dv4 import RNG

CONFIG = {"floor": "F4EFE4", "seed": 21}

SWAY = [0]


def sway_node(p):
    name = "Anim Sway" if SWAY[0] == 0 else "Anim Sway.%03d" % SWAY[0]
    SWAY[0] += 1
    dv4.pivot(name, p)
    return name


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.22, light=.34)
    dark = dv4.paint_wood("Dark", base="6E4529", dark="3C2314", light="9A6A40", scale=3.0, along="Z", edge="A98054", tint=.15)
    plank = dv4.paint_wood("Plank", base="B5753F", dark="5E3A1D", light="DDA55F", scale=4.0, along="X", edge="E6BE86", tint=.3)
    crate = dv4.paint_wood("Crate", base="C9A06A", dark="7A5A32", light="E8C890", scale=5.0, along="X", edge="F0D8A8", tint=.35)
    zinc = L.paint_zinc("Zinc")
    pot = dv4.paint_terracotta("Pot", glaze=dv4.TEAL, glaze_z=.16, drip=.04)
    pot2 = dv4.paint_terracotta("Pot2", glaze="EE8FAE", glaze_light="F7BBD0", glaze_z=.52, drip=.04)
    soil = dv4.paint_soil("Soil")
    kraft = L.paint_kraft("Kraft")
    kraftd = L.paint_kraft("KraftDots", base="F4D9E2", dark="D9B2C2", light="FFF0F5", dots="EE8FAE", dot_scale=35.0)
    pinkc = L.paint_stripes("Valance", a="EE8FAE", b="FBF8F1", width=.12, along="X")
    board = L.paint_chalkboard("Board")
    chalk = L.paint_plastic("Chalk", "F4EFE4", light="FFFFFF", dark="C8C2B4", gloss=.1)
    chalkp = L.paint_plastic("ChalkP", "F2B8C6", light="FFE0E8", dark="C08898", gloss=.1)
    chalky = L.paint_plastic("ChalkY", "F2D06B", light="FFF0B0", dark="C0A040", gloss=.1)
    leaf = dv4.paint_leaf("Leaf", base="3F8F3A", dark="23602A", light="8CCB55", vein="B9E08A", veins=4)
    stemp = dv4.paint_flat("Stem", "4E8E3A", dark="2C5A22", variation=.25, scale=20.0, k_light=.25)
    fern = dv4.paint_leaf("Fern", base="2F7A3A", dark="1B4A24", light="6DB24A", vein="9ED87A", veins=9)
    cord = dv4.paint_flat("Cord", "2F3A40", variation=0)
    ribbon = L.paint_plastic("Ribbon", "1F9A8E", light="6ED2C6", dark="12605A", gloss=.3)
    # petal palettes
    P = {
        "red": L.paint_petal("RoseRed", "D7343A", tip="F27A80", center="7A1218"),
        "pink": L.paint_petal("Pink", "EE8FAE", tip="FFD3E0", center="C7507A"),
        "yellow": L.paint_petal("Yellow", "F2C23F", tip="FFE9A0", center="D07A10"),
        "orange": L.paint_petal("Orange", "EC862E", tip="FFC27A", center="B84E0E"),
        "white": L.paint_petal("White", "F6F2EA", tip="FFFFFF", center="D9CDA8"),
        "purple": L.paint_petal("Purple", "8E6CCF", tip="C9B2F0", center="4E2E8A"),
        "blue": L.paint_petal("Blue", "7BAFE0", tip="C5DDF6", center="3F6FB0"),
        "sun": L.paint_petal("Sun", "F2B21E", tip="FFE066", center="C97A0A"),
    }
    seeds = L.paint_seeds("Seeds")
    daisy_c = L.paint_petal("DaisyC", "F2C23F", tip="FFDE70", center="D89A10")

    W, D = 1.10, .68          # half extents used by the structure
    # ---------------------------------------------------------------- pergola: 4 posts, 2 beams, 5 slats, valance, festoon
    for sx in (-1, 1):
        for sy in (-1, 1):
            dv4.cube("Post%d%d" % (sx, sy), (.085, .085, 2.26), loc=(sx * (W - .04), sy * (D - .05), 1.13), paint=dark, bevel=.01, segs=1)
            dv4.cube("PostCap%d%d" % (sx, sy), (.12, .12, .03), loc=(sx * (W - .04), sy * (D - .05), 2.28), paint=dark, bevel=.008, segs=1)
    for sy in (-1, 1):
        dv4.cube("Beam%d" % sy, (2 * W, .09, .1), loc=(0, sy * (D - .05), 2.32), paint=dark, bevel=.01, segs=1)
    for i in range(5):
        dv4.cube("Slat%d" % i, (.05, 2 * D - .02, .07), loc=(-.88 + i * .44, 0, 2.395), paint=dark, bevel=.006, segs=1)
    # pink scalloped valance along the front beam (flat band + half-discs)
    dv4.cube("Valance", (2 * W + .02, .02, .1), loc=(0, D, 2.24), paint=pinkc, bevel=.004, segs=1)
    for i in range(14):
        x = -W + .08 + i * (2 * W - .16) / 13
        dv4.sphere("Scallop%d" % i, .078, loc=(x, D + .005, 2.19), scale=(1, .25, 1), seg=6, rings=3, paint=pinkc)
    # festoon under the front beam: black cord + warm bulbs (static, lit look is baked)
    pts = L.catenary((-W + .05, D - .08, 2.26), (W - .05, D - .08, 2.26), .1, 14)
    dv4.tube("Cord", pts, radius=.004, res=4, paint=cord, resolution=1, kind="POLY")
    for k in range(1, 14, 2):
        p = pts[k]
        dv4.sphere("Socket%d" % k, .013, loc=(p[0], p[1], p[2] - .025), scale=(1, 1, 1.6), seg=6, rings=3, paint=cord)
        dv4.sphere("Bulb%d" % k, .03, loc=(p[0], p[1], p[2] - .06), scale=(1, 1, 1.25), seg=7, rings=4, paint=None, mat_override="E_FFE6A8")
    # ---------------------------------------------------------------- rear tiers: three stepped plank benches with front edge boards
    tiers = [(.30, .20, .40), (.60, .40, .44), (.90, .56, .22)]   # (height, back-y centre, depth)
    for i, (h, yc, dp) in enumerate(tiers):
        y = -yc
        dv4.cube("Tier%d" % i, (1.9, dp, h if i == 0 else .3), loc=(0, y, h / 2 if i == 0 else h - .15), paint=plank, bevel=.01, segs=1)
        if i:
            dv4.cube("TierFoot%d" % i, (1.8, dp - .06, h - .3), loc=(0, y, (h - .3) / 2), paint=dark, bevel=.006, segs=1)
    # ---------------------------------------------------------------- buckets with bouquets (18 sway nodes)
    plan = [
        # (x, y, z_floor, r, h, kinds, palettes, n, height, s)
        (-.78, -.22, .30, .075, .2, ("rose",), ("red", "pink"), 5, .17, 1.0),
        (-.47, -.22, .30, .075, .2, ("tulip",), ("yellow", "orange"), 5, .18, 1.0),
        (-.16, -.22, .30, .075, .2, ("peony",), ("pink", "white"), 4, .17, 1.0),
        (.16, -.22, .30, .075, .2, ("rose",), ("white", "yellow"), 5, .17, 1.0),
        (.47, -.22, .30, .075, .2, ("tulip",), ("purple", "pink"), 5, .18, 1.0),
        (.78, -.22, .30, .075, .2, ("daisy",), ("white",), 4, .16, 1.0),
        (-.78, -.44, .60, .075, .2, ("lavender",), ("purple",), 4, .2, 1.0),
        (-.47, -.44, .60, .075, .2, ("hydrangea",), ("blue", "purple"), 2, .15, 1.0),
        (-.16, -.44, .60, .075, .2, ("daisy",), ("white", "pink"), 4, .16, 1.0),
        (.16, -.44, .60, .075, .2, ("rose",), ("orange", "yellow"), 5, .17, 1.0),
        (.47, -.44, .60, .075, .2, ("lavender",), ("purple",), 4, .2, 1.0),
        (.78, -.44, .60, .075, .2, ("peony",), ("pink",), 4, .17, 1.0),
        (-.72, -.58, .90, .09, .24, ("sunflower",), ("sun",), 3, .3, 1.0),
        (.0, -.58, .90, .09, .24, ("sunflower",), ("sun",), 3, .32, 1.0),
        (.72, -.58, .90, .09, .24, ("sunflower",), ("sun",), 3, .3, 1.0),
        (-.36, .40, .0, .12, .3, ("rose", "peony"), ("red", "pink", "yellow"), 5, .3, 1.3),
        (.0, .40, .0, .12, .3, ("tulip", "daisy"), ("white", "pink", "orange"), 5, .3, 1.3),
    ]
    for i, (x, y, z, r, h, kinds, pals, n, hh, s) in enumerate(plan):
        L.bucket("Bucket%d" % i, (x, y, z), r, h, paint=zinc, seg=8, handle=math.radians(RNG.uniform(0, 360)) if i in (0, 5, 12, 15) else None, rim=False)
        node = sway_node((x, y, z + h))
        L.ballast("Ballast%d" % i, node, (-.9, -.2, .15), (.9, -.2, .15), dark)
        L.bouquet("Bq%d" % i, (x, y, z + h), node, kinds, [P[k] for k in pals], leaf, stemp, n=n, h=hh, spread=r * .75, s=s,
                  center_paint=seeds if "sunflower" in kinds else daisy_c, leaves=3 if "sunflower" in kinds else 4)
    # 18th: tall bucket of kraft-wrapped cone bouquets by the counter (front right)
    bx, by = .36, .42
    L.bucket("BucketK", (bx, by, 0), .12, .34, paint=zinc, seg=10, rim=False)
    node = sway_node((bx, by, .34))
    L.ballast("BallastK", node, (-.9, -.2, .15), (.9, -.2, .15), dark)
    for k in range(3):
        a = math.radians(k * 120 + 30); rr = .055
        cx, cy = bx + math.cos(a) * rr, by + math.sin(a) * rr
        tip = (cx * .6 + bx * .4, cy * .6 + by * .4, .18)
        topc = (cx + math.cos(a) * .06, cy + math.sin(a) * .06, .60)
        cone = dv4.lathe("Cone%d" % k, [(0, 0), (.012, 0), (.07, .36), (.085, .42), (.075, .43), (.06, .38), (0, .36)], seg=8, loc=tip,
                         rot=(math.degrees(-math.sin(a)) * .22, math.degrees(math.cos(a)) * .22, 0), paint=kraft if k != 1 else kraftd)
        dv4.torus("Bow%d" % k, .022, .008, loc=(tip[0] + math.cos(a) * .07, tip[1] + math.sin(a) * .07, .34), seg=8, minor=3, paint=ribbon, out=node, rot=(80, 0, math.degrees(a)))
        L.bouquet("Kq%d" % k, (tip[0] + math.cos(a) * .045, tip[1] + math.sin(a) * .045, .40), node, ("rose", "daisy", "tulip")[k:k + 1] or ("rose",),
                  [P[("red", "pink", "yellow", "white")[(k + j) % 4]] for j in range(2)], leaf, stemp, n=2, h=.16, spread=.035, s=.9, center_paint=daisy_c, leaves=1)
    # ---------------------------------------------------------------- front-left: two stacked crates with terracotta pots + ferns / small bushes
    for j, (y, zc) in enumerate(((.42, .07), (.16, .07))):
        dv4.cube("Crate%d" % j, (.56, .30, .14), loc=(-.80, y, zc), paint=crate, bevel=.006, segs=1)
        dv4.cube("CrateSlot%d" % j, (.58, .31, .018), loc=(-.80, y, zc + .035), paint=dark, bevel=.003, segs=1)
    pots = [(-.95, .42, .14), (-.78, .44, .14), (-.62, .40, .14), (-.92, .16, .14), (-.72, .14, .14)]
    for i, (x, y, z) in enumerate(pots):
        pp = pot if i % 2 else pot2
        dv4.lathe("Pot%d" % i, [(0, 0), (.05, 0), (.065, .1), (.074, .105), (.074, .12), (.06, .105), (0, .095)], seg=8, loc=(x, y, z), paint=pp)
        dv4.sphere("PotSoil%d" % i, .058, loc=(x, y, z + .085), scale=(1, 1, .2), seg=8, rings=3, paint=soil)
        if i % 3 == 0:
            for k in range(5):
                a = k * 72 + RNG.uniform(-15, 15)
                dv4.leaf("Fern%d%d" % (i, k), .14, .05, loc=(x, y, z + .1), rot=(RNG.uniform(30, 55), 0, a), paint=fern, shape="ellipse", bend=.5, cup=.0, thickness=0, nl=3, nw=2)
        elif i % 3 == 1:
            dv4.icosphere("Bush%d" % i, .07, loc=(x, y, z + .14), scale=(1, 1, .8), subdiv=1, paint=leaf)
            for k in range(2):
                a = k * 120 + RNG.uniform(-20, 20)
                dv4.leaf("BushLf%d%d" % (i, k), .09, .05, loc=(x, y, z + .12), rot=(RNG.uniform(30, 60), 0, a), paint=leaf, shape="heart", bend=.4, cup=.15, thickness=.003, nl=3, nw=2)
        else:
            for k in range(4):
                a = k * 90 + RNG.uniform(-10, 10)
                dv4.leaf("Succ%d%d" % (i, k), .07, .035, loc=(x, y, z + .1), rot=(RNG.uniform(40, 70), 0, a), paint=fern, shape="spade", bend=.2, cup=.3, thickness=.006, nl=2, nw=2)
            dv4.sphere("SuccC%d" % i, .025, loc=(x, y, z + .115), seg=7, rings=4, paint=fern)
    # ---------------------------------------------------------------- front-right: wrapping counter with paper rolls, ribbon spools
    cx, cy = .78, .33
    dv4.cube("Counter", (.56, .5, .84), loc=(cx, cy, .42), paint=plank, bevel=.012, segs=1)
    dv4.cube("CounterTop", (.62, .56, .04), loc=(cx, cy, .86), paint=dark, bevel=.008, segs=1)
    dv4.cube("CounterRail", (.58, .52, .04), loc=(cx, cy, .16), paint=dark, bevel=.005, segs=1)
    for sx in (-1, 1):
        L.bar("RollPost%d" % sx, [(cx + sx * .26, cy - .16, .88), (cx + sx * .26, cy - .16, 1.3)], r=.012, paint=dark, res=6)
    L.bar("RollRod", [(cx - .27, cy - .16, 1.26), (cx + .27, cy - .16, 1.26)], r=.008, paint=zinc, res=6)
    L.bar("RollRod2", [(cx - .27, cy - .16, 1.06), (cx + .27, cy - .16, 1.06)], r=.008, paint=zinc, res=6)
    dv4.cylinder("Roll1", .05, .44, loc=(cx - .22, cy - .16, 1.26), rot=(0, 90, 0), seg=10, paint=kraft)
    dv4.cylinder("Roll2", .045, .44, loc=(cx - .22, cy - .16, 1.06), rot=(0, 90, 0), seg=10, paint=kraftd)
    dv4.cube("Sheet", (.4, .25, .006), loc=(cx - .02, cy + .02, .885), rot=(0, 0, 12), paint=kraft, bevel=.002, segs=1)
    for i, col in enumerate(("1F9A8E", "EE8FAE", "E0B040")):
        dv4.cylinder("Spool%d" % i, .035, .03, loc=(cx + .18, cy + .12 - i * .1, .88), seg=10, paint=L.paint_plastic("Spool%d" % i, col))
    # ---------------------------------------------------------------- chalkboard on the back-left post pair: flower drawings only
    bz = 1.75
    dv4.cube("BoardFrame", (.6, .035, .5), loc=(-.5, -D + .04, bz), paint=dark, bevel=.01, segs=2)
    dv4.cube("Board", (.54, .012, .44), loc=(-.5, -D + .06, bz), paint=board, bevel=.003, segs=1)
    for sx in (-1, 1):
        L.wire("BoardChain%d" % sx, (-.5 + sx * .24, -D + .04, bz + .25), (-.5 + sx * .24, -D + .04, 2.27), r=.003, paint=zinc)
    L.picto_flower("Draw1", (-.65, -D + .07, bz + .08), .3, chalk, chalky, r=.005)
    L.picto_flower("Draw2", (-.5, -D + .07, bz + .1), .36, chalkp, chalky, r=.005, petals=6)
    L.picto_flower("Draw3", (-.35, -D + .07, bz + .06), .28, chalk, chalkp, r=.005)
    L.picto_heart("DrawH", (-.3, -D + .07, bz - .13), .18, chalkp, r=.005)
    # tulip drawing: cup outline + stem
    L.bar("DrawT", [(-.54, -D + .07, bz - .18), (-.55, -D + .07, bz - .1), (-.5, -D + .07, bz - .06), (-.45, -D + .07, bz - .1), (-.46, -D + .07, bz - .18), (-.54, -D + .07, bz - .18)], r=.005, paint=chalky, res=6)
    # ---------------------------------------------------------------- hanging baskets from the slats (trailing greenery)
    for i, (x, y) in enumerate(((.0, .05),)):
        for k in range(3):
            a = math.radians(k * 120)
            L.wire("Chain%d%d" % (i, k), (x + math.cos(a) * .1, y + math.sin(a) * .1, 2.0), (x, y, 2.36), r=.003, paint=zinc)
        dv4.lathe("HBasket%d" % i, [(0, 1.86), (.08, 1.86), (.13, 1.95), (.145, 2.0), (.13, 2.01), (0, 2.01)], seg=10, loc=(x, y, 0), paint=crate if i % 2 else pot)
        dv4.icosphere("HGreen%d" % i, .13, loc=(x, y, 2.02), scale=(1, 1, .7), subdiv=1, paint=leaf)
        for k in range(5):
            a = k * 72 + RNG.uniform(-15, 15)
            dv4.leaf("HLeaf%d%d" % (i, k), .14, .05, loc=(x + math.cos(math.radians(a)) * .1, y + math.sin(math.radians(a)) * .1, 1.99),
                     rot=(RNG.uniform(-50, -70), 0, a - 90), paint=leaf, shape="heart", bend=.3, cup=.1, thickness=0, nl=3, nw=2)
        for k in range(4):
            a = k * 90 + 45
            fl = dv4.sphere("HFl%d%d" % (i, k), .022, loc=(x + math.cos(math.radians(a)) * .09, y + math.sin(math.radians(a)) * .09, 2.08), seg=5, rings=3, paint=P[("pink", "red")[i]])
            L.tag(fl, "z")
    return {"name": "FlowerStand", "tex": 1024, "budget": 15000, "floor": "F4EFE4"}
