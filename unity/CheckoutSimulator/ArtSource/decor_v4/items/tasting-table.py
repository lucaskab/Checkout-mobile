"""tasting-table: rectangular tasting table with turned wooden legs and a red gingham cloth; on top a round board with a waxed
cheese wheel (wedge cut out) and cheese cubes with toothpicks under a glass dome, a long board with bread slices and a
baguette, two bunches of grapes, a toothpick cup and a little brass bell. Footprint half .70 x .40, height <= 1.2 (front = +Y)."""
import math, os, sys
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib_G as G

CONFIG = {"floor": "F4EFE4", "seed": 23}

TOP = .76       # table top height (cloth top sits at TOP + .006)


def grapes(name, loc, rot, paint_, stem_p, n=18, r=.013):
    """A bunch lying on its side: rows of berries tapering along +Y, a woody stem at the wide end."""
    M = dv4.Matrix.LocRotScale(dv4.Vector(loc), dv4.Euler([math.radians(a) for a in rot]), (1, 1, 1))
    rows = [(0, 4), (1, 4), (2, 3), (3, 3), (4, 2), (5, 1)]
    k = 0
    for j, cnt in rows:
        y = j * r * 1.55
        for i in range(cnt):
            x = (i - (cnt - 1) / 2) * r * 1.7 + RNG.uniform(-.002, .002)
            z = r * (1 if (i + j) % 2 == 0 else 1.6) + RNG.uniform(-.001, .002)
            ob = dv4.sphere(name + "B%d" % k, r * RNG.uniform(.9, 1.1), seg=8, rings=6, paint=paint_)
            ob.matrix_world = M @ dv4.Matrix.Translation((x, y, z)); k += 1
            if k >= n:
                break
    st = dv4.tube(name + "Stem", [(0, -r * 2.2, r * 1.2), (0, -r * .5, r * 1.6), (0, r * 2.5, r * 2.0)], radius=.0025, res=5, paint=stem_p, resolution=3)
    st.matrix_world = M


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.14, light=.36)
    wood = dv4.paint_wood("Leg", base="8E5A32", dark="4A2C12", light="B98455", scale=5.0, along="Z", edge="D9A86A", tint=.1)
    board = dv4.paint_wood("Board", base="C99A5E", dark="7E5A2E", light="E8C48C", scale=5.0, dist=2.0, along="X", edge="F1D6A4", tint=.2)
    cloth = G.paint_gingham("Cloth", base="F8F3E8", check="D4402F", scale=14.0, amt=1.0)
    cheese = G.paint_cheese("Cheese", holes=.7)
    wheel = G.paint_cheese("Wheel", holes=.5, wax="C43A2E")
    bread = G.paint_bread("Bread", crust="B86A2E", crust_dark="7A3F12", crust_light="E0A862", slashes=0.0)
    bag = G.paint_bread("Baguette", crust="D08A43", crust_dark="8E4D1C", crust_light="F0C47C", slashes=9.0)
    loaf = G.paint_bread("Loaf", crust="B86A2E", crust_dark="7A3F12", crust_light="E0A862", slashes=5.0, flour=.4)
    grape_p = G.paint_grape("Grape")
    grape_g = G.paint_grape("GrapeGreen", base="A9C84A", dark="6F8F22", light="D2E57C", bloom="E6F0B0")
    stem_p = dv4.paint_flat("Stem", "6A4A2A", dark="3A2510", variation=.3, scale=40.0)
    brass = G.paint_brass("Brass", hammered=.0)
    pick = dv4.paint_flat("Pick", "E8D6A8", dark="B59A62", variation=.3, scale=30.0)
    cream = dv4.paint_flat("Cup", "F4EFE4", dark="D5CBB4", variation=.2, scale=8.0, edge="FFFFFF", edge_k=.5, edge_r=.003)
    teal = dv4.paint_flat("Teal", "1F9A8E", dark="155F58", variation=.25, scale=8.0, edge="7FD4CA", edge_k=.6, edge_r=.003)

    # ---- table: four turned legs, aprons, top slab, gingham cloth with a wavy hem
    W, D = 1.3, .72
    for sx in (-1, 1):
        for sy in (-1, 1):
            prof = [(0, 0), (.028, 0), (.03, .02), (.024, .05), (.03, .09), (.036, .16), (.03, .24), (.024, .3), (.034, .34), (.036, .4),
                    (.03, .47), (.026, .55), (.03, .62), (.034, .7), (.034, TOP - .02), (0, TOP - .02)]
            dv4.lathe("Leg%d%d" % (sx, sy), prof, seg=14, loc=(sx * (W / 2 - .07), sy * (D / 2 - .07), 0), paint=wood)
    dv4.cube("ApronX", (W - .1, .03, .07), loc=(0, 0, TOP - .055), paint=wood, bevel=.004, segs=1)
    dv4.cube("ApronY", (.03, D - .1, .07), loc=(0, 0, TOP - .055), paint=wood, bevel=.004, segs=1)
    dv4.cube("Top", (W, D, .03), loc=(0, 0, TOP - .015), paint=wood, bevel=.006, segs=2)
    G.cloth_box("Cloth", W + .06, D + .06, TOP + .004, .22, paint=cloth, nx=16, ny=9, nz=4, waves=7, amp=.014, flare=.035)

    z0 = TOP + .012
    # ---- round board (left): waxed wheel with a wedge cut out, the wedge, cheese cubes on toothpicks
    bx, by = -.38, .02
    dv4.lathe("RoundBoard", [(0, 0), (.2, 0), (.205, .006), (.2, .016), (0, .016)], seg=28, loc=(bx, by, z0), paint=board)
    dv4.lathe("BoardHandle", [(0, 0), (.035, 0), (.035, .014), (0, .014)], seg=12, loc=(bx - .215, by, z0 + .001), paint=board)
    G.pie("Wheel", .105, .065, 40, 360, seg=26, loc=(bx - .04, by + .05, z0 + .016), rot=(0, 0, 200), paint=wheel)
    G.wedge("Wedge", .1, .06, ang=38, loc=(bx + .11, by - .02, z0 + .016), rot=(0, 0, 160), paint=cheese)
    for i in range(5):
        a = math.radians(225 + i * 24); rr = .145
        cx, cy = bx + math.cos(a) * rr, by + math.sin(a) * rr
        dv4.cube("Cube%d" % i, (.022, .022, .022), loc=(cx, cy, z0 + .027), rot=(0, 0, RNG.uniform(0, 90)), paint=cheese, bevel=.003, segs=1)
        tilt = RNG.uniform(-12, 12)
        dv4.tube("Pick%d" % i, [(cx, cy, z0 + .03), (cx + math.sin(math.radians(tilt)) * .05, cy, z0 + .08)], radius=.0015, res=4, paint=pick, kind="POLY", resolution=1)
    # ---- small glass cloche (centre back) over a plate of cheese cubes, brass knob
    dx_, dy_ = -.02, -.17
    dv4.lathe("Plate", [(0, 0), (.09, 0), (.1, .004), (.098, .012), (.09, .012), (.085, .006), (0, .006)], seg=24, loc=(dx_, dy_, z0), paint=cream)
    for i in range(4):
        a = math.radians(45 + i * 90)
        dv4.cube("DomeCube%d" % i, (.024, .024, .024), loc=(dx_ + math.cos(a) * .035, dy_ + math.sin(a) * .035, z0 + .018), rot=(0, 0, i * 25), paint=cheese, bevel=.003, segs=1)
    dv4.cube("DomeCube4", (.024, .024, .024), loc=(dx_, dy_, z0 + .042), rot=(0, 0, 30), paint=cheese, bevel=.003, segs=1)
    dome = [(.095, 0), (.095, .02), (.093, .06), (.082, .095), (.062, .122), (.035, .138), (0, .143)]
    dv4.lathe("Dome", dome, seg=24, loc=(dx_, dy_, z0 + .012), paint=None, mat_override="G_Glass", cap=False)
    dv4.torus("DomeRim", .096, .005, loc=(dx_, dy_, z0 + .015), seg=24, minor=5, paint=brass)
    dv4.lathe("Knob", [(0, 0), (.01, 0), (.012, .006), (.008, .016), (.013, .024), (.011, .032), (0, .034)], seg=12, loc=(dx_, dy_, z0 + .153), paint=brass)

    # ---- long board (right) with bread slices, a baguette and grapes
    lx, ly = .33, 0.0
    dv4.cube("LongBoard", (.5, .3, .018), loc=(lx, ly, z0 + .009), paint=board, bevel=.006, segs=2)
    dv4.cube("BoardGroove", (.46, .006, .004), loc=(lx, ly + .12, z0 + .02), paint=dv4.paint_flat("Groove", "7E5A2E", variation=.2), bevel=.001, segs=1)
    # fanned bread slices leaning on each other
    # a round country loaf with three thick slices cut off and leaning against it (crumb faces to the front)
    dv4.sphere("Loaf", .08, loc=(lx - .12, ly + .0, z0 + .018 + .05), scale=(1.1, 1.0, .68), seg=14, rings=9, paint=loaf)
    for i in range(3):
        G.pie("Slice%d" % i, .058, .016, 0, 180, seg=12, loc=(lx - .12 - .03 + i * .03, ly - .09 - i * .018, z0 + .018), rot=(72 - i * 9, 0, 0), paint=bread)
    G.pie("Slice3", .056, .016, 0, 180, seg=12, loc=(lx + .02, ly - .1, z0 + .018), rot=(0, 0, 200), paint=bread)
    # baguette along the back of the board, with diagonal slashes
    pts = [(lx - .2, ly + .1, z0 + .045), (lx - .05, ly + .11, z0 + .05), (lx + .1, ly + .1, z0 + .05), (lx + .24, ly + .06, z0 + .045)]
    dv4.tube("Baguette", pts, radius=.038, res=10, paint=bag, resolution=4, taper=[(0, .25), (.12, .95), (.5, 1.0), (.88, .95), (1, .25)])
    grapes("GrapeP", (lx + .14, ly - .1, z0 + .018), (0, 0, 15), grape_p, stem_p)
    grapes("GrapeG", (lx + .08, ly - .01, z0 + .018), (0, 0, -110), grape_g, stem_p, n=16, r=.012)

    # ---- toothpick cup and a brass bell at the front, a folded napkin stack at the back
    cx, cy = .02, .25
    dv4.lathe("PickCup", [(0, 0), (.025, 0), (.027, .005), (.024, .05), (.028, .055), (.026, .06), (.022, .058), (.02, .01), (0, .01)], seg=14, loc=(cx, cy, z0), paint=teal)
    for i in range(7):
        a = RNG.uniform(0, 2 * math.pi); rr = RNG.uniform(0, .012)
        dv4.tube("CupPick%d" % i, [(cx + math.cos(a) * rr, cy + math.sin(a) * rr, z0 + .012), (cx + math.cos(a) * rr * 1.8, cy + math.sin(a) * rr * 1.8, z0 + .085)],
                 radius=.0015, res=4, paint=pick, kind="POLY", resolution=1)
    bell = [(0, 0), (.03, 0), (.034, .006), (.033, .012), (.028, .03), (.02, .048), (.015, .056), (.01, .06), (.012, .068), (.008, .076), (0, .078)]
    dv4.lathe("Bell", bell, seg=16, loc=(-.08, .24, z0), paint=brass)
    dv4.sphere("BellKnob", .01, loc=(-.08, .24, z0 + .082), seg=8, rings=6, paint=wood)
    dv4.cube("Napkins", (.12, .12, .03), loc=(-.1, -.26, z0 + .015), rot=(0, 0, 8), paint=cream, bevel=.006, segs=2)
    dv4.cube("NapkinBand", (.126, .03, .032), loc=(-.1, -.26, z0 + .015), rot=(0, 0, 8), paint=teal, bevel=.003, segs=1)
    return {"name": "TastingTable", "tex": 1024, "budget": 10000, "floor": "F4EFE4"}
