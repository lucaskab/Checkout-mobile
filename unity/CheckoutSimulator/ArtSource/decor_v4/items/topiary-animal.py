"""topiary-animal: a clipped box-hedge elephant (cute, chunky, dense leaf texture) standing in a round glazed planter
ringed with flowers. The whole bush sways gently from the soil ("Anim Sway").
Footprint half .60 x .45, height <= 1.5 (Blender: elephant faces the customer at +Y)."""
import math, os, sys
from mathutils import Vector, Matrix
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_J as J

CONFIG = {"floor": "C9C3B8", "seed": 23}

ZS = .31      # soil level


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.22, light=.36)
    hedge = J.paint_hedge("Hedge", base="4E9A3A", dark="21531F", light="97D45C", scale=58.0)
    hedge_d = J.paint_hedge("HedgeDark", base="3F8530", dark="1B4619", light="7FC24C", scale=58.0)
    pot = dv4.paint_terracotta("Pot", base="C9683E", dark="94482C", glaze="1F9A8E", glaze_light="5BC2B4", glaze_z=.17, drip=.05)
    soil = dv4.paint_soil("Soil")
    leaf = dv4.paint_leaf("Leaf", base="3F9A3C", dark="21602A", light="8BD055", vein="C7EA9E", veins=5)
    eye = J.paint_gloss("Eye", "1A1A1A", dark="000000", light="6A6A6A", variation=.0, highlight=.5)
    tusk = J.paint_gloss("Tusk", "F4EFE4", dark="C9BFA8", light="FFFFFF", variation=.08)
    petal = [J.paint_gloss("Petal%d" % i, h, dark=d, light=l, variation=.1, highlight=.35)
             for i, (h, d, l) in enumerate((("EE8FAE", "C2567C", "FFC9DA"), ("D74A3C", "8E2A20", "F28A7C"), ("E0B040", "A8781F", "FFE38A"), ("F4EFE4", "C9BFA8", "FFFFFF")))]
    centre = J.paint_gloss("Centre", "E8B52E", dark="A8781A", light="FFE07A", variation=.1)

    # ---- planter: glazed terracotta bowl on a foot, soil disc, flower ring
    prof = [(0, 0), (.30, 0), (.32, .01), (.31, .05), (.34, .06), (.40, .27), (.43, .29), (.44, .32), (.43, .35), (.40, .35), (.39, .32), (.37, .30),
            (.36, .29), (0, .29)]
    dv4.lathe("Pot", prof, seg=36, paint=pot)
    sp = dv4.patch("Soil", .78, .78, 14, 14, loc=(0, 0, ZS), paint=soil, disk=True)
    dv4.mod_displace(sp, strength=.02, size=.08, mid=.45)
    for i in range(12):
        a = math.radians(i * 30 + RNG.uniform(-8, 8)); r = RNG.uniform(.31, .36)
        x, y = math.cos(a) * r, math.sin(a) * r
        pc = petal[i % 4]
        h = RNG.uniform(.06, .09)
        dv4.tube("Stem%d" % i, [(x, y, ZS - .01), (x + .005, y, ZS + h)], radius=.005, res=5, paint=leaf, kind="POLY", resolution=1)
        dv4.lathe("Flower%d" % i, [(0, 0), (.034, .0), (.05, .014), (.036, .024), (0, .022)], seg=20, loc=(x, y, ZS + h), rot=(RNG.uniform(-15, 15), RNG.uniform(-15, 15), 0),
                  paint=pc, scallop=(5, .3))
        dv4.sphere("Centre%d" % i, .012, loc=(x, y, ZS + h + .02), seg=8, rings=5, paint=centre)
        dv4.leaf("FLeaf%d" % i, .07, .04, loc=(x, y, ZS + .005), rot=(25, 0, math.degrees(a) + RNG.uniform(60, 120)), paint=leaf, shape="spade",
                 bend=.3, cup=.15, thickness=.003, nl=3, nw=2)

    # ---- the elephant (clipped hedge), swaying from the soil.  E = overall scale, YS squeezes the depth into the footprint
    E, YS = 1.12, .86
    P = lambda x, y, z: (x * E, y * E * YS, ZS + (z - ZS) * E)
    sway = "Anim Sway"; dv4.pivot(sway, (0, 0, ZS))
    kw = dict(paint=hedge, out=sway)
    belly = dv4.sphere("Belly", .30 * E, loc=P(0, -.05, .82), scale=(.88, 1.1 * YS, .9), seg=24, rings=16, **kw)
    dv4.mod_displace(belly, strength=.03, size=.07, mid=.5)
    head = dv4.sphere("Head", .21 * E, loc=P(0, .22, .98), scale=(1.0, .95 * YS, .95), seg=22, rings=14, **kw)
    dv4.mod_displace(head, strength=.025, size=.06, mid=.5)
    dv4.sphere("Brow", .16 * E, loc=P(0, .27, 1.06), scale=(1.1, .8 * YS, .7), seg=16, rings=10, **kw)
    # trunk: curls down and out, tip lifted (happy)
    dv4.tube("Trunk", [P(0, .36, .92), P(0, .44, .80), P(0, .455, .62), P(0, .42, .48), P(0, .34, .40)], radius=.064 * E, res=12, paint=hedge, out=sway,
             resolution=4, taper=[(0, 1.0), (.5, .8), (1, .5)])
    # ears: two big heart-leaf fans of hedge flaring out and back from the head
    for sx in (-1, 1):
        # ear hangs beside the head: grows down/outward/slightly back, its face pointing sideways
        g = Vector((sx * .45, -.15, -.88)).normalized()
        nrm = Vector((sx * .85, .1, .45)); nrm = (nrm - g * nrm.dot(g)).normalized()
        xa = g.cross(nrm)
        rot = [math.degrees(v) for v in Matrix((xa, g, nrm)).transposed().to_euler()]
        ear = dv4.leaf("Ear%d" % sx, .38 * E, .36 * E, loc=P(sx * .15, .17, 1.13), rot=rot, paint=hedge_d, out=sway,
                       shape="heart", bend=.12, cup=.1, thickness=.045 * E, nl=6, nw=5)
        dv4.mod_displace(ear, strength=.015, size=.05, mid=.5)
        dv4.sphere("Eye%d" % sx, .024 * E, loc=P(sx * .10, .385, 1.03), seg=10, rings=7, paint=eye, out=sway)
        dv4.sphere("Glint%d" % sx, .008 * E, loc=P(sx * .09, .405, 1.042), seg=6, rings=4, paint=tusk, out=sway)
        dv4.tube("Tusk%d" % sx, [P(sx * .07, .36, .86), P(sx * .10, .44, .80), P(sx * .12, .49, .78)], radius=.022 * E, res=8, paint=tusk, out=sway,
                 resolution=3, taper=[(0, 1.0), (1, .35)])
    # legs: chunky clipped columns with a rounded top
    for sx in (-1, 1):
        for sy in (-.21, .13):
            leg = dv4.lathe("Leg%d%s" % (sx, sy), [(0, 0), (.10 * E, 0), (.105 * E, .07), (.10 * E, (.62 - ZS) * E), (.08 * E, (.70 - ZS) * E), (0, (.72 - ZS) * E)],
                            seg=14, loc=(sx * .16 * E, sy * E * YS, ZS - .02), paint=hedge, out=sway)
            dv4.mod_displace(leg, strength=.018, size=.06, mid=.5)
    # tail: a little tuft
    dv4.tube("Tail", [P(0, -.34, .85), P(.03, -.40, .74), P(.02, -.40, .62)], radius=.025 * E, res=8, paint=hedge_d, out=sway, resolution=3,
             taper=[(0, .8), (.6, 1.0), (1, .4)])
    return {"name": "TopiaryAnimal", "tex": 1024, "budget": 10000, "floor": "C9C3B8"}
