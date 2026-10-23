"""flower-bed: long wooden planter box (horizontal planks, chunky corner posts, teal trim) packed with tulips, daisies and
petunias, with ivy trailing over the front. Footprint half 1.04 x .44, height <= 1.2 (Blender Z up, front +Y)."""
import math
import sys, os
import dv4
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_E as E
from dv4 import RNG

CONFIG = {"floor": "C9C3B8", "seed": 22}


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.25, light=.36)
    wood = dv4.paint_wood("Plank", base="B06A37", dark="6A3E1E", light="E2A95C", scale=4.0, dist=2.0, along="X", tint=.3, k_light=.3)
    woodz = dv4.paint_wood("Post", base="9A5C30", dark="4A2A12", light="C98D4F", scale=5.0, dist=2.5, along="Z", tint=.1)
    trim = E.paint_painted("Trim", dv4.TEAL, light="8FE0D6", dark="0E5048", variation=.15)
    soil = dv4.paint_soil("Soil")
    leafp = dv4.paint_leaf("Leaf", base="3E8E3B", dark="1E5A2A", light="86C654", veins=5)
    ivyp = dv4.paint_leaf("Ivy", base="2F7A33", dark="174A20", light="6DB84A", vein="A8DB8C", veins=4)
    stemp = dv4.paint_flat("Stem", "4E8A34", "2E5A24", variation=.3)
    vine = dv4.paint_flat("Vine", "3E6A2A", "25451C", variation=.3)
    gold = E.paint_petal("Centre", dv4.GOLD, "B57A18", "FFE58A")
    throat = dv4.paint_flat("Throat", "5A1F3A", "2A0C1A", variation=.2)
    P = {
        "red": E.paint_petal("PetalRed", "D74A3C", "8E2A20", "FF8C7A"),
        "gold": E.paint_petal("PetalGold", "F2C23F", "C08A16", "FFE9A0"),
        "pink": E.paint_petal("PetalPink", "EE8FAE", "C2567E", "FFC6D8"),
        "white": E.paint_petal("PetalWhite", "FBF8F1", "C9BFAE", "FFFFFF"),
        "purple": E.paint_petal("PetalPurple", "8E6CCF", "5A3E96", "C7AEF0"),
        "orange": E.paint_petal("PetalOrange", "EC862E", "B85A14", "FFC078"),
    }

    # ---- box: 4 corner posts, 3 horizontal planks per side, teal cap rail, feet
    L, Dp, H = 1.98, .80, .40
    for sx in (-1, 1):
        for sy in (-1, 1):
            dv4.cube("Post", (.10, .10, .44), loc=(sx * (L / 2 - .05), sy * (Dp / 2 - .05), .22), paint=woodz, bevel=.012, segs=1)
            dv4.sphere("PostCap", .052, loc=(sx * (L / 2 - .05), sy * (Dp / 2 - .05), .44), scale=(1, 1, .55), seg=8, rings=4, paint=woodz)
    for i in range(3):
        z = .085 + i * .125
        for sy in (-1, 1):
            dv4.cube("PlankF", (L - .16, .035, .118), loc=(0, sy * (Dp / 2 - .02), z), paint=wood, bevel=.008, segs=1)
        for sx in (-1, 1):
            dv4.cube("PlankS", (.035, Dp - .16, .118), loc=(sx * (L / 2 - .02), 0, z), paint=wood, bevel=.008, segs=1)
    # cap rails (teal painted) along the four rims
    for sy in (-1, 1):
        dv4.cube("RailF", (L - .22, .075, .035), loc=(0, sy * (Dp / 2 - .03), H + .017), paint=trim, bevel=.009, segs=2)
    for sx in (-1, 1):
        dv4.cube("RailS", (.075, Dp - .22, .035), loc=(sx * (L / 2 - .03), 0, H + .017), paint=trim, bevel=.009, segs=2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            dv4.cube("Foot", (.09, .09, .03), loc=(sx * (L / 2 - .10), sy * (Dp / 2 - .10), .015), paint=woodz, bevel=.006, segs=1)
    ground = dv4.patch("Soil", L - .1, Dp - .1, 18, 8, loc=(0, 0, .395), paint=soil)
    dv4.mod_displace(ground, strength=.025, size=.1, mid=.45)

    # ---- flowers: back row of tall tulips, middle daisies + petunias, front low petunias; big leaves fill the gaps
    for i in range(9):
        x = -.80 + i * .20 + RNG.uniform(-.03, .03); y = -.20 + RNG.uniform(-.05, .05)
        h = RNG.uniform(.30, .40)
        col = ("red", "gold", "pink", "orange")[i % 4]
        top = (x + RNG.uniform(-.03, .03), y + RNG.uniform(-.02, .02), .40 + h)
        E.stem("TS%d" % i, (x, y, .39), top, stemp, radius=.008)
        E.tulip("Tulip%d" % i, .085, top, P[col], rot=(RNG.uniform(-12, 12), RNG.uniform(-12, 12), RNG.uniform(0, 360)))
        dv4.leaf("TL%d" % i, .26, .07, loc=(x, y, .40), rot=(30 + RNG.uniform(-10, 10), 0, RNG.uniform(0, 360)), paint=leafp,
                 shape="ellipse", bend=.35, cup=.3, thickness=.003, nl=4, nw=2)
    for i in range(9):
        x = -.80 + i * .20 + RNG.uniform(-.03, .03); y = .02 + RNG.uniform(-.05, .05)
        h = RNG.uniform(.17, .24)
        top = (x + RNG.uniform(-.02, .02), y + RNG.uniform(-.02, .02), .40 + h)
        E.stem("MS%d" % i, (x, y, .39), top, stemp, radius=.007)
        if i % 3 == 0:
            E.daisy("Daisy%d" % i, .075, top, P["white"], gold, rot=(RNG.uniform(-20, 20), RNG.uniform(-20, 20), RNG.uniform(0, 360)))
        else:
            E.petunia("Pet%d" % i, .07, top, P["purple" if i % 3 == 1 else "pink"], throat,
                      rot=(RNG.uniform(-20, 20), RNG.uniform(-20, 20), RNG.uniform(0, 360)))
        for j in range(2):
            dv4.leaf("ML%d_%d" % (i, j), RNG.uniform(.13, .16), .09, loc=(x, y, .40), rot=(45 + RNG.uniform(-10, 10), 0, RNG.uniform(0, 360)), paint=leafp,
                     shape="spade", bend=.3, cup=.15, thickness=.003, nl=3, nw=2)
    for i in range(9):
        x = -.80 + i * .20 + .08 + RNG.uniform(-.03, .03); y = .20 + RNG.uniform(-.03, .03)
        h = RNG.uniform(.10, .15)
        top = (x, y + .03, .40 + h)
        E.stem("FS%d" % i, (x, y, .39), top, stemp, radius=.007)
        E.petunia("FPet%d" % i, .065, top, P[("pink", "white", "purple", "gold")[i % 4]], throat,
                  rot=(35 + RNG.uniform(-10, 10), 0, RNG.uniform(-10, 10)))
        dv4.leaf("FL%d" % i, RNG.uniform(.12, .14), .09, loc=(x, y, .40), rot=(50, 0, RNG.uniform(140, 220)), paint=leafp, shape="spade", bend=.3, cup=.15,
                 thickness=.003, nl=3, nw=2)
    # ---- ivy trailing over the front rim (sways from the rim), heart leaves lying flat on the planks
    sway = "Anim Sway"; dv4.pivot(sway, (0, Dp / 2, H + .02))
    for i, x0 in enumerate((-.72, -.30, .14, .58)):
        zend = .10 + i * .05
        pts = [(x0, .26, .42), (x0 + .03, Dp / 2 + .015, H + .04), (x0 + .06, Dp / 2 + .03, .28), (x0 + .02, Dp / 2 + .028, zend)]
        dv4.tube("Vine%d" % i, pts, radius=.007, res=5, paint=vine, out=sway, resolution=3, taper=[(0, 1.0), (1, .6)])
        n = 4
        for j in range(n):
            u = (j + .6) / (n + .2)
            z = H + .03 - (H + .03 - zend) * u
            xx = x0 + .03 + .035 * math.sin(u * math.pi) + RNG.uniform(-.015, .015)
            dv4.leaf("IvyL%d_%d" % (i, j), RNG.uniform(.095, .12), RNG.uniform(.085, .10), loc=(xx, Dp / 2 + .028, z),
                     rot=(90 + RNG.uniform(-6, 6), 180 + RNG.uniform(-55, 55), 0), paint=ivyp, out=sway, shape="heart",
                     bend=.15, cup=.08, thickness=.003, nl=3, nw=2)
        dv4.leaf("IvyT%d" % i, .10, .09, loc=(x0 + .01, .28, .43), rot=(40, 0, RNG.uniform(-30, 30)), paint=ivyp, out=sway, shape="heart",
                 bend=.2, cup=.1, thickness=.003, nl=3, nw=2)
    return {"name": "FlowerBed", "tex": 1024, "budget": 10000, "floor": "C9C3B8"}
