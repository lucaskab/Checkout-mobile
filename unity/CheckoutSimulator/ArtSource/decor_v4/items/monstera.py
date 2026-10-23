"""monstera: big Monstera deliciosa (split, fenestrated leaves on long petioles, coir moss pole) in a speckled stoneware pot
on a terracotta saucer. Footprint half .45 x .45, height <= 1.6. Leaves + petioles on "Anim Sway" (pivot at the soil)."""
import math, os, sys
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib_G as G

CONFIG = {"floor": "F4EFE4", "seed": 7}


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.22, light=.34)
    pot_p = G.paint_speckle("Pot", base="EFE3CB", dark="D6C7A8", speck="5E4030", speck_amt=.8, glaze_z=.13)
    saucer_p = dv4.paint_terracotta("Saucer", base="C8744A", dark="99532F", glaze_z=5.0)
    soil_p = dv4.paint_soil("Soil")
    bark_p = dv4.paint_wood("Chips", base="7A5234", dark="3F2816", light="A77A4E", scale=12.0, along="X", edge="B08A62", tint=.4)
    coir_p = G.paint_coir("Coir", cx=.02, cy=-.03, twine="C09A62", twine_w=.01)
    stem_p = dv4.paint_flat("Stem", "3F7D37", dark="24501F", variation=.35, scale=6.0, edge="7DB35E", edge_k=.6, edge_r=.004)
    leaf_p = dv4.paint_leaf("Leaf", base="2F7D35", dark="194A22", light="5FAE49", vein="A8D986", veins=5)
    leaf_y = dv4.paint_leaf("LeafYoung", base="4A9A3E", dark="2A6A2C", light="8CC860", vein="C6E6A0", veins=4)

    # ---- saucer + pot (stoneware: speckled oatmeal glaze, unglazed clay foot)
    dv4.lathe("Saucer", [(0, 0), (.2, 0), (.215, .006), (.235, .03), (.242, .036), (.232, .04), (.22, .036), (.205, .012), (0, .012)], seg=28, paint=saucer_p)
    prof = [(0, .012), (.16, .012), (.172, .02), (.178, .06), (.196, .22), (.212, .36), (.222, .395), (.232, .405), (.235, .425), (.228, .44),
            (.214, .44), (.208, .415), (.2, .39), (.192, .35), (.184, .31), (0, .31)]
    dv4.lathe("Pot", prof, seg=24, paint=pot_p)
    dv4.torus("PotRing", .205, .007, loc=(0, 0, .30), seg=24, minor=5, paint=pot_p)
    soil = dv4.patch("Soil", .38, .38, 10, 10, loc=(0, 0, .312), paint=soil_p, disk=True)
    dv4.mod_displace(soil, strength=.02, size=.06, mid=.45)
    for i in range(10):
        a = RNG.uniform(0, 2 * math.pi); r = RNG.uniform(.06, .17)
        dv4.cube("Chip%d" % i, (RNG.uniform(.025, .045), RNG.uniform(.014, .022), .008), loc=(math.cos(a) * r, math.sin(a) * r, .318),
                 rot=(RNG.uniform(-12, 12), RNG.uniform(-12, 12), RNG.uniform(0, 180)), paint=bark_p, bevel=.003, segs=1)

    # ---- moss pole (slightly leaning), with jute ties
    pole_top = 1.34
    dv4.lathe("Pole", [(0, .29), (.034, .29), (.035, .5), (.034, .9), (.033, pole_top - .02), (.027, pole_top), (0, pole_top)], seg=12,
              loc=(.02, -.03, 0), rot=(2, -3, 0), paint=coir_p)
    tie_p = dv4.paint_flat("Jute", "D2B077", dark="9A7B4A", variation=.4, scale=40.0)
    for z in (.55, .85, 1.15):
        dv4.torus("Tie%.2f" % z, .037, .005, loc=(.02 + (z - .29) * .052, -.03 - (z - .29) * .035, z), rot=(2, -3, 0), seg=14, minor=4, paint=tie_p)

    # ---- the plant: leaves + petioles sway from the soil
    sway = "Anim Sway"; dv4.pivot(sway, (0, 0, .31))
    # (azimuth, height where the petiole leaves the pole, leaf length, pitch deg (negative = tip down), young?)
    leaves = [
        (20, .60, .46, -24, False),
        (95, .80, .43, -18, False),
        (160, .52, .45, -28, False),
        (230, 1.0, .42, -12, False),
        (300, .70, .44, -20, False),
        (60, .92, .40, -14, False),
        (355, 1.14, .40, -4, False),
        (130, 1.26, .32, 14, True),
        (265, 1.34, .28, 24, True),
    ]
    for k, (az, h, L, pitch, young) in enumerate(leaves):
        a = math.radians(az + RNG.uniform(-8, 8))
        ca, sa = math.cos(a), math.sin(a)
        # petiole: from the base of the pole, up along it, then arching outwards
        r_out = .06 + L * .1
        p0 = (ca * .035 + .02, sa * .035 - .03, .30)
        p1 = (ca * .045 + .02, sa * .045 - .03, .30 + (h - .30) * .55)
        p2 = (ca * .07 + .02, sa * .07 - .03, h)
        p3 = (ca * r_out, sa * r_out, h + .06 + L * .08)
        dv4.tube("Petiole%d" % k, [p0, p1, p2, p3], radius=.011 if not young else .008, res=5, paint=stem_p, out=sway, resolution=3,
                 taper=[(0, 1.0), (.7, .9), (1, .7)])
        # leaf: starts at the petiole end, pointing outwards, tip dropping
        tilt = pitch + RNG.uniform(-4, 4)
        G.big_leaf("Leaf%d" % k, L, L * .95, loc=p3, rot=(tilt, RNG.uniform(-12, 12), math.degrees(a) - 90),
                   paint=leaf_y if young else leaf_p, out=sway, lobes=3 if young else 4, slit=.22 if young else .14,
                   holes=not young, bend=.3, cup=.1, nl=14 if young else 24, nw=6)
        # a sheath where the petiole meets the pole
        dv4.sphere("Node%d" % k, .016, loc=p2, scale=(1, 1, 1.6), seg=8, rings=5, paint=stem_p, out=sway)
    # aerial roots clinging to the pole
    root_p = dv4.paint_flat("Root", "9A7B5A", dark="5E4630", variation=.4, scale=30.0)
    for k in range(4):
        z = .5 + k * .19; a = math.radians(50 + k * 95)
        pts = [(.02 + math.cos(a) * .03, -.03 + math.sin(a) * .03, z), (.02 + math.cos(a) * .06, -.03 + math.sin(a) * .06, z - .08),
               (.02 + math.cos(a) * .045, -.03 + math.sin(a) * .045, z - .2)]
        dv4.tube("Root%d" % k, pts, radius=.005, res=5, paint=root_p, resolution=3, taper=[(0, 1.0), (1, .5)])
    return {"name": "Monstera", "tex": 1024, "budget": 10000, "floor": "F4EFE4"}
