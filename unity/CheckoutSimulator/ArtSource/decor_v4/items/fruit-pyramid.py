"""fruit-pyramid: three tiers of wooden crates (3 / 2 / 1) on stepped risers, overflowing with apples, oranges and lemons,
a chalk slate on a stake with an apple drawing. Footprint half .70 x .55, height <= 1.4 (front = +Y)."""
import math, os, sys
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib_G as G

CONFIG = {"floor": "F4EFE4", "seed": 17}

CW, CD, CH = .42, .32, .20      # crate outer size


def crate(name, loc, rot, wood, wood2):
    """Slatted wooden crate: 4 corner posts, two slats per side with a gap, a plank bottom. Local origin at the bottom centre."""
    M = dv4.Matrix.LocRotScale(dv4.Vector(loc), dv4.Euler([math.radians(a) for a in rot]), (1, 1, 1))
    def part(n, size, p, paint_, bevel=.004):
        ob = dv4.cube(name + n, size, paint=paint_, bevel=bevel, segs=1)
        ob.matrix_world = M @ dv4.Matrix.Translation(dv4.Vector(p))
        return ob
    t = .016
    for sx in (-1, 1):
        for sy in (-1, 1):
            part("Post%d%d" % (sx, sy), (.03, .03, CH), (sx * (CW / 2 - .015), sy * (CD / 2 - .015), CH / 2), wood2)
    for zc in (.055, .15):
        for sy in (-1, 1):
            part("SlatY%d%.2f" % (sy, zc), (CW, t, .07), (0, sy * (CD / 2 - t / 2), zc), wood)
        for sx in (-1, 1):
            part("SlatX%d%.2f" % (sx, zc), (t, CD - .06, .07), (sx * (CW / 2 - t / 2), 0, zc), wood)
    part("Bottom", (CW - .06, CD - .06, .014), (0, 0, .09), wood2, bevel=.002)


def fruits(name, loc, rot, kind_paints, mound_p, n=13):
    """A heap of fruit in a crate: a bumpy mound plus a jittered top layer of fruit poking above the rim."""
    M = dv4.Matrix.LocRotScale(dv4.Vector(loc), dv4.Euler([math.radians(a) for a in rot]), (1, 1, 1))
    cx, cy = CW - .07, CD - .07
    m = dv4.patch(name + "Mound", cx, cy, 6, 5, paint=kind_paints[0][1])
    dv4.mod_displace(m, strength=.05, size=.09, mid=.3)
    m.matrix_world = M @ dv4.Matrix.Translation((0, 0, .16))
    pts = []
    cols, rows = 4, 3
    k = 0
    for j in range(rows):
        for i in range(cols):
            if k >= n:
                break
            x = (i - (cols - 1) / 2) * (cx / cols) + RNG.uniform(-.012, .012)
            y = (j - (rows - 1) / 2) * (cy / rows) + RNG.uniform(-.012, .012)
            z = .178 + RNG.uniform(-.008, .012) + (.012 if (i + j) % 2 else 0)
            pts.append((x, y, z)); k += 1
    for idx, p in enumerate(pts):
        kind, paint_ = kind_paints[idx % len(kind_paints)]
        r = {"apple": .038, "orange": .04, "lemon": .034}[kind] * RNG.uniform(.92, 1.08)
        sc = {"apple": (1, 1, .88), "orange": (1, 1, 1), "lemon": (1.35, .95, .95)}[kind]
        rotE = dv4.Euler([math.radians(a) for a in (RNG.uniform(-25, 25), RNG.uniform(-25, 25), RNG.uniform(0, 360))])
        Mf = M @ dv4.Matrix.LocRotScale(dv4.Vector(p), rotE, (1, 1, 1))
        ob = dv4.sphere(name + "F%d" % idx, r, seg=10, rings=7, paint=paint_)
        ob.matrix_world = Mf @ dv4.Matrix.Diagonal((*sc, 1))
        if kind == "apple":
            st = dv4.tube(name + "S%d" % idx, [(0, 0, -.006), (.004, .002, .016)], radius=.0025, res=5, paint=STEM, kind="POLY", resolution=1)
            st.matrix_world = Mf @ dv4.Matrix.Translation((0, 0, r * .82))
            if idx % 3 == 0:
                lf = dv4.leaf(name + "L%d" % idx, .032, .017, paint=LEAF, shape="spade", bend=.2, cup=.1, thickness=.002, nl=3, nw=2)
                lf.matrix_world = Mf @ dv4.Matrix.LocRotScale(dv4.Vector((.004, .002, r * .82 + .012)), dv4.Euler((math.radians(-25), 0, math.radians(RNG.uniform(0, 360)))), (1, 1, 1))
        if kind == "lemon":
            tip = dv4.sphere(name + "T%d" % idx, r * .22, seg=6, rings=4, paint=paint_)
            tip.matrix_world = Mf @ dv4.Matrix.LocRotScale(dv4.Vector((r * 1.3, 0, 0)), dv4.Euler((0, 0, 0)), (1.4, .8, .8))


STEM = None
LEAF = None


def build():
    global STEM, LEAF
    dv4.FINISH.update(ao=.62, ao_dist=.16, light=.36)
    wood = dv4.paint_wood("Crate", base="C98B4E", dark="7A4E26", light="E8BE7C", scale=4.0, dist=2.5, along="X", edge="F0CC92", tint=.35)
    wood_d = dv4.paint_wood("Post", base="A26E3B", dark="5E3A1A", light="C99456", scale=5.0, dist=2.0, along="Z", edge="D9A86A", tint=.2)
    riser = dv4.paint_wood("Riser", base="8E5A2F", dark="4E2E12", light="B5804C", scale=3.0, along="X", edge="C9985F", tint=.1)
    STEM = dv4.paint_flat("Stem", "5A3A1E", dark="2E1A0A", variation=.3, scale=40.0)
    LEAF = dv4.paint_leaf("Leaf", base="4E9A3C", dark="2A6A2C", light="8CC860", vein="C6E6A0", veins=3)
    apple = G.paint_fruit("Apple", "C61C17", "6E0E0C", "E04030", blush="E8A52A", blush_amt=.3, speck=.3, hl_amt=.12, tint=.1)
    apple_g = G.paint_fruit("AppleGreen", "7FB522", "3F6F0E", "A8D040", blush="D8462A", blush_amt=.3, speck=.25, hl_amt=.12, tint=.1)
    orange = G.paint_fruit("Orange", "EE7108", "A84606", "FA9420", pores=.35, hl_amt=.12, tint=.08)
    lemon = G.paint_fruit("Lemon", "F2C60C", "B38E08", "F8DE40", blush="A8C020", blush_amt=.3, pores=.25, hl_amt=.12, tint=.1)
    mound_a = dv4.paint_flat("MoundA", "9E2A22", dark="4A110E", variation=.6, scale=14.0)
    mound_o = dv4.paint_flat("MoundO", "C9700F", dark="6E3A06", variation=.6, scale=14.0)
    mound_l = dv4.paint_flat("MoundL", "C8A81A", dark="6B5708", variation=.6, scale=14.0)

    # ---- risers (stepped wooden blocks at the back)
    dv4.cube("Riser1", (1.3, .46, .24), loc=(0, -.3, .12), paint=riser, bevel=.01, segs=2)
    dv4.cube("Riser2", (.5, .26, .24), loc=(0, -.4, .36), paint=riser, bevel=.01, segs=2)
    dv4.cube("Lip1", (1.32, .03, .03), loc=(0, -.08, .255), paint=wood_d, bevel=.006, segs=1)
    dv4.cube("Lip2", (.52, .03, .03), loc=(0, -.28, .495), paint=wood_d, bevel=.006, segs=1)
    # ---- crates: tier 1 (3, front, flat), tier 2 (2, tilted 12 deg), tier 3 (1, tilted 12 deg)
    tiers = [
        [((-.44, .24, 0), (0, 0, 2), [("apple", apple), ("apple", apple_g), ("apple", apple)], mound_a),
         ((0, .25, 0), (0, 0, -1), [("orange", orange)], mound_o),
         ((.44, .24, 0), (0, 0, 1.5), [("lemon", lemon), ("lemon", lemon), ("apple", apple_g)], mound_l)],
        [((-.24, -.17, .24), (12, 0, -2), [("orange", orange), ("apple", apple)], mound_o),
         ((.24, -.17, .24), (12, 0, 1), [("apple", apple), ("lemon", lemon), ("apple", apple)], mound_a)],
        [((0, -.36, .48), (12, 0, 0), [("lemon", lemon), ("orange", orange)], mound_l)],
    ]
    for ti, tier in enumerate(tiers):
        for ci, (loc, rot, kinds, mound) in enumerate(tier):
            nm = "C%d%d" % (ti, ci)
            crate(nm, loc, rot, wood, wood_d)
            fruits(nm, loc, rot, kinds, mound, n=12 if ti == 0 else 11)
    # ---- chalk slate on a stake at the back, apple drawing
    sx, sy = .42, -.5
    slate = G.paint_chalkboard("Slate", drawing=G.chalk_apple(sx, 1.02, .05))
    dv4.cube("Stake", (.025, .018, .9), loc=(sx, sy, .45 + .24), paint=wood_d, bevel=.004, segs=1)
    dv4.cube("Frame", (.2, .02, .16), loc=(sx, sy + .012, 1.02), paint=wood, bevel=.006, segs=2)
    dv4.cube("Board", (.17, .012, .13), loc=(sx, sy + .018, 1.02), paint=slate, bevel=.002, segs=1)
    # a few fallen fruits on the floor in front
    for i, (x, y, p, r, sc) in enumerate(((-.62, .52, apple, .038, (1, 1, .88)), (.1, .55, orange, .04, (1, 1, 1)), (.58, .5, lemon, .034, (1.35, .95, .95)))):
        dv4.sphere("Loose%d" % i, r, loc=(x, y, r * sc[2] * .95), scale=sc, seg=10, rings=7, paint=p, rot=(0, 0, RNG.uniform(0, 360)))
    return {"name": "FruitPyramid", "tex": 1024, "budget": 15000, "floor": "F4EFE4"}
