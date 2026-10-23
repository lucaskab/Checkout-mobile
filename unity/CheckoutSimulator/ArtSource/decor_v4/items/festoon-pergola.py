"""festoon-pergola: timber pergola (outside) with chunky chamfered posts on stone plinths, double beams, rafters and lattice,
climbing vines with leaves and pink/red blossoms up two posts and over the beams, festoon strings of warm bulbs (three
"Anim Blink" nodes for a gentle twinkle), glazed terracotta planters with bushes and flowers at the posts, a hanging lantern.
Footprint half 1.35 x 1.27, height <= 2.7 (Blender: X across, front = +Y)."""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
import _lib_D as L
from dv4 import RNG

CONFIG = {"floor": "C9C3B8", "seed": 13}


def vine(name, pts, bark, leaf, bloom, out="Body", leaves=14, blooms=5, r=.014):
    """Woody vine along pts with leaves and a few blossoms."""
    dv4.tube(name, pts, radius=r, res=6, paint=bark, out=out, resolution=3, taper=[(0, 1.0), (1, .55)])
    n = len(pts)
    for k in range(leaves):
        t = (k + .5) / leaves
        i = min(n - 2, int(t * (n - 1))); f = t * (n - 1) - i
        p = [pts[i][j] + (pts[i + 1][j] - pts[i][j]) * f for j in range(3)]
        a = math.degrees(math.atan2(-p[1], -p[0])) + RNG.uniform(-80, 80)      # leaves grow toward the inside of the pergola
        dv4.leaf(name + "L%d" % k, RNG.uniform(.14, .2), RNG.uniform(.1, .14), loc=(p[0] + RNG.uniform(-.02, .02), p[1] + RNG.uniform(-.02, .02), p[2] + RNG.uniform(-.03, .03)),
                 rot=(RNG.uniform(-30, 30), RNG.uniform(-30, 30), a - 90), paint=leaf, out=out, shape="heart", bend=.35, cup=.15, thickness=0, nl=3, nw=2)
    for k in range(blooms):
        t = (k + .7) / blooms
        i = min(n - 2, int(t * (n - 1))); f = t * (n - 1) - i
        p = [pts[i][j] + (pts[i + 1][j] - pts[i][j]) * f for j in range(3)]
        b = dv4.lathe(name + "B%d" % k, [(0, 0), (.025, .005), (.045, .025), (.048, .05), (.035, .065), (0, .058)], seg=8, loc=(p[0] + RNG.uniform(-.04, .04), p[1] + RNG.uniform(-.04, .04), p[2] + .02),
                      rot=(RNG.uniform(-40, 40), RNG.uniform(-40, 40), 0), paint=bloom, out=out, scallop=(5, .12))
        L.tag(b, "z")


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.3, light=.36)
    wood = dv4.paint_wood("Timber", base="8E5A34", dark="4A2C17", light="C08A52", scale=2.5, along="Z", edge="D9A872", tint=.2)
    woodx = dv4.paint_wood("TimberX", base="8E5A34", dark="4A2C17", light="C08A52", scale=2.5, along="X", edge="D9A872", tint=.2)
    stone = dv4.paint_stone("Plinth", base="D9CDB4", dark="A08E6F", light="EFE6D4", moss_amt=.5, moss_z=.08)
    iron = dv4.paint_iron("Iron", base="1C2430", mid="35414E", edge="9AA6B0", rust_amt=.25)
    bark = dv4.paint_wood("Bark", base="6B4A32", dark="3E2A1A", light="93714E", scale=8.0, along="Z", edge="A08664", tint=.1)
    leaf = dv4.paint_leaf("Leaf", base="3F8F3A", dark="23602A", light="8CCB55", vein="B9E08A", veins=4)
    hedge = dv4.paint_leaf("Hedge", base="2F7A3A", dark="1B4A24", light="6DB24A", vein="9ED87A", veins=5)
    pink = L.paint_petal("Pink", "EE8FAE", tip="FFD3E0", center="C7507A")
    red = L.paint_petal("Red", "D74A3C", tip="F58A7E", center="8E1E14")
    yellow = L.paint_petal("Yellow", "F2C23F", tip="FFE9A0", center="D07A10")
    white = L.paint_petal("White", "F6F2EA", tip="FFFFFF", center="D9CDA8")
    daisy_c = L.paint_petal("DaisyC", "F2C23F", tip="FFDE70", center="D89A10")
    pot = dv4.paint_terracotta("Planter", glaze=dv4.TEAL, glaze_z=.28, drip=.05)
    soil = dv4.paint_soil("Soil")
    stemp = dv4.paint_flat("Stem", "4E8E3A", dark="2C5A22", variation=.25, scale=20.0, k_light=.25)
    cord = dv4.paint_flat("Cord", "2F3A40", variation=0)
    bulb_off = L.paint_plastic("BulbOff", "E8DDC0", light="FFFBEA", dark="A89A78", gloss=.5)
    glass = L.paint_glass_fake("LanternGlass", base="FFE7B0", light="FFFFFF")

    X, Y, H = 1.15, 1.07, 2.25
    posts = [(sx * X, sy * Y) for sx in (-1, 1) for sy in (-1, 1)]
    # ---- posts: stone plinth, chamfered timber post with a collar, capital block
    for i, (px, py) in enumerate(posts):
        dv4.lathe("Plinth%d" % i, [(0, 0), (.17, 0), (.175, .04), (.15, .07), (.13, .09), (0, .09)], seg=8, loc=(px, py, 0), paint=stone, rot=(0, 0, 22.5))
        dv4.cube("Post%d" % i, (.13, .13, H - .09), loc=(px, py, .09 + (H - .09) / 2), paint=wood, bevel=.02, segs=2)
        dv4.cube("Collar%d" % i, (.17, .17, .05), loc=(px, py, .5), paint=wood, bevel=.01, segs=1)
        dv4.cube("Capital%d" % i, (.2, .2, .06), loc=(px, py, H - .03), paint=wood, bevel=.01, segs=1)
        for dx, dy in ((.085, 0), (-.085, 0), (0, .085), (0, -.085)):
            dv4.sphere("Bolt%d%s%s" % (i, dx, dy), .012, loc=(px + dx, py + dy, .5), seg=6, rings=4, paint=iron)
    # ---- double beams along X (front/back) with shaped ends, rafters along Y, lattice slats on top
    for sy in (-1, 1):
        for dz in (0, .12):
            dv4.cube("Beam%d%s" % (sy, dz), (2 * X + .3, .09, .13), loc=(0, sy * Y, H + .05 + dz), paint=woodx, bevel=.012, segs=1)
        for sx in (-1, 1):   # shaped beam ends (angled blocks)
            dv4.cube("BeamEnd%d%d" % (sy, sx), (.1, .09, .09), loc=(sx * (X + .12), sy * Y, H + .14), rot=(0, sx * 35, 0), paint=woodx, bevel=.01, segs=1)
    for i in range(7):
        x = -X + i * 2 * X / 6
        dv4.cube("Rafter%d" % i, (.07, 2 * Y + .3, .12), loc=(x, 0, H + .28), paint=wood, bevel=.01, segs=1)
    for i in range(5):
        y = -Y + .2 + i * (2 * Y - .4) / 4
        dv4.cube("Lattice%d" % i, (2 * X + .1, .04, .04), loc=(0, y, H + .36), paint=woodx, bevel=.006, segs=1)
    # corner braces (45 degree struts under the beams)
    for i, (px, py) in enumerate(posts):
        sx, sy = (1 if px > 0 else -1), (1 if py > 0 else -1)
        dv4.cube("Brace%d" % i, (.06, .06, .6), loc=(px - sx * .22, py, H - .22), rot=(0, -sx * 45, 0), paint=wood, bevel=.008, segs=1)
    # ---- climbing vines (kept on the inner faces of the posts / beams so the leaves stay inside the footprint)
    p0 = (-X, Y)
    v1 = [(p0[0] + .09, p0[1] - .02, .3), (p0[0] + .1, p0[1] - .06, .9), (p0[0] + .08, p0[1] + .02, 1.5), (p0[0] + .1, p0[1] - .04, 2.1), (p0[0] + .16, p0[1] - .07, H + .06),
          (-.6, Y - .08, H + .3), (-.1, Y - .1, H + .32), (.45, Y - .08, H + .3)]
    vine("Vine1", v1, bark, leaf, pink, leaves=60, blooms=14)
    v1b = [(p0[0] + .02, p0[1] - .09, .4), (p0[0] - .03, p0[1] - .1, 1.0), (p0[0] + .03, p0[1] - .09, 1.7), (p0[0] - .02, p0[1] - .1, 2.2)]
    vine("Vine1b", v1b, bark, leaf, pink, leaves=22, blooms=5, r=.01)
    p1 = (X, -Y)
    v2 = [(p1[0] - .09, p1[1] + .02, .3), (p1[0] - .1, p1[1] + .06, 1.0), (p1[0] - .08, p1[1] - .02, 1.7), (p1[0] - .1, p1[1] + .04, 2.2), (p1[0] - .16, p1[1] + .07, H + .06),
          (.5, -Y + .08, H + .3), (0, -Y + .1, H + .32)]
    vine("Vine2", v2, bark, leaf, red, leaves=50, blooms=12)
    v2b = [(p1[0] - .02, p1[1] + .09, .5), (p1[0] + .03, p1[1] + .1, 1.2), (p1[0] - .03, p1[1] + .09, 1.9)]
    vine("Vine2b", v2b, bark, leaf, red, leaves=18, blooms=4, r=.01)
    # ---- festoon strings: three across (X) under the rafters + two along the beams; bulbs alternate over 3 Blink nodes + static
    nodes = ["Anim Blink", "Anim Blink.001", "Anim Blink.002"]
    for i, nd in enumerate(nodes):
        dv4.pivot(nd, (0, -.7 + i * .7, H - .2))
        L.ballast("Ballast%d" % i, nd, (-X - .1, -Y, H + .05 + i * .04), (X + .1, -Y, H + .05 + i * .04), woodx)   # hidden in the back beam (UV balance)
    k = 0
    strings = [((-X + .05, -.7, H - .02), (X - .05, -.7, H - .02), .16, 10), ((-X + .05, 0, H - .02), (X - .05, 0, H - .02), .18, 10),
               ((-X + .05, .7, H - .02), (X - .05, .7, H - .02), .16, 10),
               ((-X + .1, -Y + .1, H - .06), (-X + .1, Y - .1, H - .06), .12, 8), ((X - .1, -Y + .1, H - .06), (X - .1, Y - .1, H - .06), .12, 8)]
    for (a, b, sag, n) in strings:
        pts = L.catenary(a, b, sag, n)
        dv4.tube("Cord%d" % k, pts, radius=.005, res=4, paint=cord, kind="POLY", resolution=1)
        for j in range(1, n):
            p = pts[j]
            dv4.cylinder("Socket%d" % k, .012, .024, loc=(p[0], p[1], p[2] - .028), seg=6, paint=cord)
            # a dim "off" bulb in the body + the lit bulb on a blink node (3 phases) => chaser twinkle
            dv4.sphere("BulbOff%d" % k, .024, loc=(p[0], p[1], p[2] - .056), scale=(1, 1, 1.25), seg=6, rings=4, paint=bulb_off)
            dv4.sphere("Bulb%d" % k, .03, loc=(p[0], p[1], p[2] - .058), scale=(1, 1, 1.25), seg=7, rings=4, paint=None, mat_override="E_FFE6A8", out=nodes[k % 3])
            k += 1
    # ---- planters at the two front posts (inside the bay) with a clipped bush + flowers; a small bench-like trough at the back
    for sx in (-1, 1):
        px, py = sx * (X - .16), Y - .5
        dv4.lathe("Planter%d" % sx, [(0, 0), (.2, 0), (.21, .01), (.25, .3), (.28, .32), (.285, .36), (.27, .37), (.245, .35), (.24, .3), (0, .3)], seg=12, loc=(px, py, 0), paint=pot)
        sl = dv4.patch("Soil%d" % sx, .46, .46, 6, 6, loc=(px, py, .31), paint=soil, disk=True)
        dv4.mod_displace(sl, strength=.02, size=.08, mid=.4)
        bush = dv4.icosphere("Bush%d" % sx, .24, loc=(px, py, .5), scale=(1, 1, .8), subdiv=2, paint=hedge)
        dv4.mod_displace(bush, strength=.06, size=.12, mid=.5)
        for q in range(8):
            a = q * 45 + RNG.uniform(-12, 12)
            dv4.leaf("BushLf%d%d" % (sx, q), .12, .07, loc=(px + math.cos(math.radians(a)) * .18, py + math.sin(math.radians(a)) * .18, .52),
                     rot=(RNG.uniform(20, 45), 0, a - 90), paint=hedge, shape="heart", bend=.3, cup=.1, thickness=0, nl=3, nw=2)
        for q, (pp, kind) in enumerate(((red, "tulip"), (yellow, "daisy"), (pink, "rose"), (white, "daisy"), (red, "rose"), (yellow, "tulip"))):
            a = math.radians(q * 60 + 20); rr = .13
            top = (px + math.cos(a) * rr, py + math.sin(a) * rr, .74 + RNG.uniform(0, .05))
            L.stem("FlS%d%d" % (sx, q), (px + math.cos(a) * rr * .5, py + math.sin(a) * rr * .5, .45), top, stemp, "Body")
            if kind == "tulip":
                L.tulip("Fl%d%d" % (sx, q), top, .075, pp, "Body", rot=(RNG.uniform(-15, 15), RNG.uniform(-15, 15), 0))
            elif kind == "rose":
                L.rose("Fl%d%d" % (sx, q), top, .07, pp, "Body", rot=(RNG.uniform(-15, 15), RNG.uniform(-15, 15), 0))
            else:
                L.daisy("Fl%d%d" % (sx, q), top, .07, pp, daisy_c, "Body", rot=(RNG.uniform(-15, 15), RNG.uniform(-15, 15), 0))
    # ---- hanging lantern from the centre rafter (iron cage, warm glass, glowing candle)
    dv4.tube("LanternChain", [(0, 0, H + .22), (0, 0, H - .25)], radius=.005, res=4, paint=iron, kind="POLY", resolution=1)
    dv4.lathe("LanternTop", [(0, H - .25), (.03, H - .25), (.09, H - .33), (.1, H - .35), (0, H - .35)], seg=10, loc=(0, 0, 0), paint=iron)
    dv4.lathe("LanternGlass", [(0, H - .35), (.075, H - .35), (.075, H - .55), (0, H - .55)], seg=8, loc=(0, 0, 0), paint=glass)
    for q in range(4):
        a = math.radians(q * 90 + 45)
        dv4.cylinder("LanternBar%d" % q, .006, .2, loc=(math.cos(a) * .078, math.sin(a) * .078, H - .55), seg=5, paint=iron)
    dv4.lathe("LanternBase", [(0, H - .59), (.09, H - .59), (.095, H - .56), (.08, H - .55), (0, H - .55)], seg=10, loc=(0, 0, 0), paint=iron)
    dv4.sphere("Candle", .035, loc=(0, 0, H - .45), scale=(1, 1, 1.3), seg=6, rings=4, paint=None, mat_override="E_FFD98A")
    return {"name": "FestoonPergola", "tex": 1024, "budget": 15000, "floor": "C9C3B8"}
