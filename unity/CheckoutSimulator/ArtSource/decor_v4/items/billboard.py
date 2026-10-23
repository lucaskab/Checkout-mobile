"""billboard: freestanding promo sign - navy steel posts on bolted foot plates, a navy frame with gold trim around a printed
poster (fruit pictograms, pink price tag with a star, gold starburst with a red %), three goose-neck lamps with glowing
bulbs on top, and a wooden planter with a flowering bush ("Anim Sway") at the base.
Footprint half .94 x .30, height <= 2.8 (Blender: poster faces +Y, Z up)."""
import math
import dv4
from dv4 import RNG
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib_F as F

CONFIG = {"floor": "C9C3B8", "seed": 25}
NAVY, GOLD = "1D2B4F", "E0B040"

# poster plate: world x in [PX0, PX1], z in [PZ0, PZ1]
PX0, PX1, PZ0, PZ1 = -.84, .84, 1.42, 2.44


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.25, light=.34)
    navy = F.paint_enamel("Navy", NAVY, dark="0C1328", light="6C7FB0", variation=.12, scratch=.1)
    gold = F.paint_brass("Gold")
    iron = dv4.paint_iron("Iron", base="23282E", mid="3C444C", edge="8A949C", rust_amt=.2)
    chrome = F.paint_chrome("Chrome")
    poster = F.paint_poster("Poster", PX0, PX1, PZ0, PZ1)
    wood = dv4.paint_wood("Wood", base="B06A37", dark="4E2C14", light="E2A95C", scale=4.0, along="X", edge="E6BE86", tint=.3)
    soil = dv4.paint_soil("Soil")
    foliage = F.paint_foliage("Foliage")
    petal = F.paint_petal("Petal", ["F45B5B", "F2B33D", "EE8FAE", "FFF1C4"], dark="7A3A2A")
    leaf = dv4.paint_leaf("Leaf", base="3F8F3A", dark="23602A", light="8CCB55", veins=5)

    # ---------------------------------------------------------------- posts, foot plates, cross brace
    for sx in (-.70, .70):
        dv4.cube("Foot%s" % sx, (.22, .22, .03), loc=(sx, 0, .015), paint=iron, bevel=.008, segs=2)
        for bx in (-.075, .075):
            for by in (-.075, .075):
                dv4.sphere("Bolt%s%s%s" % (sx, bx, by), .014, loc=(sx + bx, by, .03), seg=8, rings=5, paint=chrome, scale=(1, 1, .6))
        dv4.lathe("Post%s" % sx, [(0, .03), (.045, .03), (.045, .14), (.038, .16), (.038, 2.50), (.03, 2.55), (0, 2.55)], seg=16, loc=(sx, 0, 0), paint=navy)
        dv4.torus("PostRing%s" % sx, .041, .009, loc=(sx, 0, 1.30), seg=16, minor=6, paint=gold)
        dv4.sphere("PostCap%s" % sx, .04, loc=(sx, 0, 2.56), seg=12, rings=8, paint=gold, scale=(1, 1, .8))
    dv4.tube("Brace", [(-.70, 0, 1.0), (.70, 0, 1.0)], radius=.02, res=8, paint=navy, kind="POLY", resolution=1)
    for sx in (-.35, .35):
        dv4.tube("Diag%s" % sx, [(sx * 2, 0, 1.0), (0, 0, 1.36)], radius=.014, res=6, paint=navy, kind="POLY", resolution=1)

    # ---------------------------------------------------------------- sign frame + poster plate
    FZ = (PZ0 + PZ1) / 2
    dv4.cube("GoldFrame", (PX1 - PX0 + .20, .06, PZ1 - PZ0 + .20), loc=(0, -.012, FZ), paint=gold, bevel=.02, segs=3)
    dv4.cube("Frame", (PX1 - PX0 + .14, .08, PZ1 - PZ0 + .14), loc=(0, 0, FZ), paint=navy, bevel=.025, segs=3)
    dv4.cube("Plate", (PX1 - PX0, .02, PZ1 - PZ0), loc=(0, .035, FZ), paint=poster, bevel=.004, segs=1)
    dv4.cube("BackPlate", (PX1 - PX0, .012, PZ1 - PZ0), loc=(0, -.038, FZ), paint=navy, bevel=.004, segs=1)
    # corner rosettes
    for sx in (-1, 1):
        for sz in (-1, 1):
            dv4.sphere("Rosette%d%d" % (sx, sz), .026, loc=(sx * (PX1 + .035), .04, FZ + sz * ((PZ1 - PZ0) / 2 + .035)), seg=10, rings=6, paint=gold, scale=(1, .6, 1))

    # ---------------------------------------------------------------- three goose-neck lamps on top
    for lx in (-.56, 0.0, .56):
        dv4.lathe("LampBase%s" % lx, [(0, 0), (.035, 0), (.04, .01), (.03, .03), (.018, .04), (0, .04)], seg=12, loc=(lx, -.02, PZ1 + .07), paint=iron)
        dv4.tube("LampArm%s" % lx, [(lx, -.02, PZ1 + .10), (lx, -.02, PZ1 + .26), (lx, .10, PZ1 + .30), (lx, .22, PZ1 + .22)], radius=.013, res=8, paint=iron, resolution=4)
        dv4.lathe("Shade%s" % lx, [(0, 0), (.025, 0), (.03, -.02), (.06, -.07), (.085, -.11), (.09, -.12), (.078, -.12), (.055, -.085), (.02, -.03), (0, -.025)],
                  seg=20, loc=(lx, .22, PZ1 + .22), rot=(-35, 0, 0), paint=iron)
        dv4.sphere("Bulb%s" % lx, .03, loc=(lx, .19, PZ1 + .15), seg=10, rings=6, paint=None, mat_override="E_FFF1C4")

    # ---------------------------------------------------------------- planter with a flowering bush (sway)
    PY = .10
    dv4.cube("Planter", (1.0, .34, .30), loc=(0, PY, .15), paint=wood, bevel=.012, segs=2)
    dv4.cube("PlanterLip", (1.04, .38, .035), loc=(0, PY, .30), paint=wood, bevel=.01, segs=2)
    for sx in (-.52, .52):
        dv4.cube("PlanterPost%s" % sx, (.05, .36, .33), loc=(sx * 1.0, PY, .165), paint=wood, bevel=.01, segs=2)
    for z in (.08, .20):
        dv4.cube("PlanterBand%s" % z, (1.02, .36, .025), loc=(0, PY, z), paint=iron, bevel=.006, segs=2)
    s = dv4.patch("Soil", .94, .28, 12, 5, loc=(0, PY, .285), paint=soil)
    dv4.mod_displace(s, strength=.025, size=.08, mid=.45)
    sway = "Anim Sway"; dv4.pivot(sway, (0, PY, .29))
    k = 0
    for i in range(9):
        x = -.40 + i * .10 + RNG.uniform(-.02, .02); y = PY + RNG.uniform(-.07, .07)
        r = RNG.uniform(.085, .115)
        dv4.icosphere("Bush%d" % i, r, loc=(x, y, .30 + r * .6), subdiv=1, paint=foliage, out=sway, scale=(1.1, 1, .9), rot=(0, 0, RNG.uniform(0, 360)))
    for i in range(12):
        x = -.44 + i * .08 + RNG.uniform(-.03, .03); y = PY + RNG.uniform(-.09, .09)
        z = .40 + RNG.uniform(.0, .08)
        dv4.tube("Stem%d" % i, [(x, y, .30), (x + .01, y, z)], radius=.004, res=5, paint=leaf, out=sway, kind="POLY", resolution=1)
        for j in range(5):
            b = j * 2 * math.pi / 5
            dv4.sphere("Petal%d%d" % (i, j), .016, loc=(x + .01 + math.cos(b) * .017, y + math.sin(b) * .017, z + .003), seg=7, rings=4, paint=petal, out=sway,
                       scale=(1.2, 1.2, .5), rot=(0, 0, math.degrees(b)))
        dv4.sphere("Heart%d" % i, .009, loc=(x + .01, y, z + .012), seg=7, rings=4, paint=gold, out=sway)
        k += 1
    for i in range(10):
        x = RNG.uniform(-.44, .44); y = PY + RNG.uniform(-.1, .1)
        dv4.leaf("Leaf%d" % i, .08, .045, loc=(x, y, .30), rot=(55 + RNG.uniform(-10, 10), 0, RNG.uniform(0, 360)), paint=leaf, out=sway,
                 shape="spade", bend=.3, cup=.2, thickness=.003, nl=4, nw=2)
    return {"name": "Billboard", "tex": 1024, "budget": 10000, "floor": "C9C3B8"}
