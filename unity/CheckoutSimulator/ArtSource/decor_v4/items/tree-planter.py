"""tree-planter: deciduous shade tree in a raised round brick planter with a stone bench rim and a ring of flowers.
Footprint half .72 x .72, height <= 3.2 (Blender Z up, front +Y; radially symmetric)."""
import math
import sys, os
import dv4
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_E as E
from dv4 import RNG

CONFIG = {"floor": "C9C3B8", "seed": 21}


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.3, light=.36)
    brick = E.paint_brick("Brick", n=30, h=.068, z0=.06, z1=.40)
    stone = dv4.paint_stone("Cap", base="E2D6C0", dark="B4A080", light="F5EEE0", moss_amt=.25)
    plinth = dv4.paint_stone("Plinth", base="8E8780", dark="5E5852", light="B3ACA3", moss_amt=.5)
    soil = dv4.paint_soil("Soil")
    bark = dv4.paint_wood("Bark", base="6E4B33", dark="38241A", light="97714E", scale=7.0, along="Z", dist=5.0, edge="A88761", tint=.1)
    canopy = E.paint_canopy("Canopy", k_ao=.75, ao_dist=.5)
    canopy2 = E.paint_canopy("Canopy2", base="5BA83E", dark="2A6A2E", light="A3DB58", k_ao=.75, ao_dist=.5)
    canopy3 = E.paint_canopy("Canopy3", base="68B23C", dark="2E6E2A", light="B9E062", spk="E4F5A0", k_ao=.75, ao_dist=.5)
    leafp = dv4.paint_leaf("Leaf", base="3F8F3A", dark="1F5A2A", light="86C654", veins=5)
    stemp = dv4.paint_flat("Stem", "4E8A34", "2E5A24", variation=.3)
    petals = {
        "pink": E.paint_petal("PetalPink", "EE8FAE", "C2567E", "FFC6D8"),
        "orange": E.paint_petal("PetalOrange", "EC862E", "B85A14", "FFC078"),
        "red": E.paint_petal("PetalRed", "D74A3C", "8E2A20", "FF8C7A"),
        "cream": E.paint_petal("PetalCream", "F7EFD6", "C9B88A", "FFFFFF"),
    }

    # ---- planter: dark stone plinth, brick wall, cream stone cap ring at bench height, soil
    dv4.lathe("Plinth", [(0, 0), (.70, 0), (.715, .012), (.715, .05), (.69, .065), (0, .065)], seg=40, paint=plinth)
    dv4.lathe("Wall", [(0, .06), (.655, .06), (.655, .42), (.565, .42), (.565, .44), (0, .44)], seg=40, paint=brick)
    cap = [(.56, .41), (.69, .41), (.715, .43), (.72, .46), (.705, .49), (.66, .50), (.60, .50), (.565, .49), (.555, .46), (.56, .41)]
    dv4.lathe("Cap", cap, seg=40, paint=stone, cap=False)
    ground = dv4.patch("Soil", 1.13, 1.13, 14, 14, loc=(0, 0, .445), paint=soil, disk=True)
    dv4.mod_displace(ground, strength=.03, size=.12, mid=.45)

    # ---- flowers around the trunk (ring of tufts, 4 colour families)
    names = list(petals)
    for i in range(18):
        a = math.radians(i * 360 / 18 + RNG.uniform(-6, 6))
        r = RNG.uniform(.33, .50)
        x, y = math.cos(a) * r, math.sin(a) * r
        pet = petals[names[(i * 3) % 4]]
        h = RNG.uniform(.11, .18)
        E.stem("FS%d" % i, (x, y, .43), (x + RNG.uniform(-.02, .02), y + RNG.uniform(-.02, .02), .44 + h), stemp, radius=.008)
        E.flower_head("FH%d" % i, RNG.uniform(.058, .075), (x + RNG.uniform(-.02, .02), y + RNG.uniform(-.02, .02), .43 + h), pet,
                      rot=(RNG.uniform(-15, 15), RNG.uniform(-15, 15), RNG.uniform(0, 360)))
        for k in range(3):
            aa = math.degrees(a) + k * 120 + RNG.uniform(-25, 25)
            dv4.leaf("FL%d_%d" % (i, k), RNG.uniform(.10, .13), .07, loc=(x, y, .445), rot=(50 + RNG.uniform(-10, 10), 0, aa),
                     paint=leafp, shape="spade", bend=.3, cup=.15, thickness=.003, nl=4, nw=2)

    # ---- trunk (static): root flare, bending trunk
    dv4.lathe("Flare", [(0, .43), (.185, .43), (.16, .50), (.13, .60), (.115, .72)], seg=20, paint=bark, scallop=(5, .08))
    dv4.tube("Trunk", [(0, 0, .60), (.02, -.015, 1.0), (-.01, .02, 1.42)], radius=.112, res=16, paint=bark, resolution=6,
             taper=[(0, 1.0), (.5, .85), (1, .72)])
    # ---- the crown sways around the fork
    sway = "Anim Sway"; dv4.pivot(sway, (0, 0, 1.36))
    branches = [((.0, .0, 1.30), (.20, -.26, 1.75), (.36, -.38, 2.15)), ((.0, .0, 1.30), (-.28, -.10, 1.8), (-.42, -.18, 2.25)),
                ((.0, .0, 1.32), (.10, .30, 1.8), (.22, .44, 2.25)), ((.0, .0, 1.34), (-.05, .05, 1.9), (-.12, .12, 2.6)),
                ((.0, .0, 1.33), (.28, .16, 1.75), (.42, .25, 2.05))]
    for i, pts in enumerate(branches):
        dv4.tube("Branch%d" % i, list(pts), radius=.062, res=10, paint=bark, out=sway, resolution=4, taper=[(0, 1.0), (.6, .7), (1, .4)])
    # canopy: three big smooth lobes + smaller lobes filling the dome, a few low ones on the branches
    clumps = [((0, 0, 2.5), .55, (1.1, 1.1, .95), canopy, 3), ((.26, -.26, 2.3), .40, (1.05, 1.05, .9), canopy2, 3),
              ((-.25, .22, 2.42), .40, (1.05, 1.05, .9), canopy2, 3),
              ((.22, .30, 2.25), .32, (1.05, 1.0, .9), canopy, 2), ((-.30, -.20, 2.2), .32, (1.0, 1.05, .9), canopy, 2),
              ((.1, -.05, 2.85), .28, (1.1, 1.05, .85), canopy2, 2), ((-.15, .1, 2.8), .30, (1.0, 1.0, .9), canopy, 2),
              ((.33, .1, 2.65), .30, (1.0, 1.0, .9), canopy, 2), ((0, -.35, 2.6), .30, (1.0, 1.0, .9), canopy2, 2),
              ((.1, -.3, 1.95), .20, (1.1, 1.0, .9), canopy2, 2), ((-.33, .3, 2.0), .20, (1.0, 1.1, .9), canopy, 2),
              ((.45, -.05, 2.4), .24, (1.0, 1.0, .9), canopy3, 2), ((-.42, -.3, 2.45), .24, (1.0, 1.0, .9), canopy3, 2),
              ((-.1, .45, 2.55), .24, (1.0, 1.0, .9), canopy3, 2), ((.2, .05, 2.98), .18, (1.0, 1.0, .8), canopy3, 2)]
    for i, (loc, r, sc, p, sd) in enumerate(clumps):
        ob = dv4.icosphere("Clump%d" % i, r, loc=loc, scale=sc, subdiv=sd, paint=p, out=sway, rot=(RNG.uniform(0, 90), RNG.uniform(0, 90), 0))
        dv4.mod_displace(ob, strength=.055 * r / .4, size=.11, mid=.5)
    return {"name": "TreePlanter", "tex": 1024, "budget": 15000, "floor": "C9C3B8"}
