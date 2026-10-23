"""plant-small: lush fiddle-leaf bush in a teal-glazed terracotta pot (indoor). Footprint half .28 x .28, height <= 1.3."""
import math
import dv4
from dv4 import RNG

CONFIG = {"floor": "F4EFE4", "seed": 11}


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.2, light=.34)
    pot_p = dv4.paint_terracotta("Pot", glaze_z=.19, drip=.06)
    soil_p = dv4.paint_soil("Soil")
    peb_p = dv4.paint_pebbles("Pebbles")
    bark_p = dv4.paint_wood("Bark", base="7A5A3E", dark="4A3524", light="A07C57", scale=6.0, along="Z", edge="B59A78")
    leaf_p = dv4.paint_leaf("Leaf", base="3C8F3C", dark="1E5A29", light="7CC050", vein="C6E6A0", veins=6)

    # pot: tapered terracotta with a foot ring and a rolled rim, soil sits at z .30
    prof = [(0, 0), (.12, 0), (.13, .008), (.128, .025), (.14, .03), (.19, .295), (.205, .3), (.213, .318), (.213, .352),
            (.202, .364), (.186, .364), (.18, .335), (.172, .305), (.166, .27), (0, .27)]
    dv4.lathe("Pot", prof, seg=26, paint=pot_p)
    soil = dv4.patch("Soil", .35, .35, 10, 10, loc=(0, 0, .30), paint=soil_p, disk=True)
    dv4.mod_displace(soil, strength=.022, size=.07, mid=.4)
    for i in range(5):
        a = i * 1.3 + RNG.random() * .6; r = RNG.uniform(.08, .145)
        s = RNG.uniform(.02, .03)
        dv4.sphere("Pebble%d" % i, s, loc=(math.cos(a) * r, math.sin(a) * r, .303 + s * .3),
                   scale=(RNG.uniform(.9, 1.3), RNG.uniform(.8, 1.1), .55), seg=8, rings=5, paint=peb_p, rot=(0, 0, RNG.uniform(0, 360)))
    # the plant sways from the soil: a short trunk, then stems fanning out into three tiers of big leaves (a dome)
    sway = "Anim Sway"; dv4.pivot(sway, (0, 0, .30))
    dv4.tube("Trunk", [(0, 0, .27), (.008, -.006, .45), (-.006, .01, .74)], radius=.022, res=8, paint=bark_p, out=sway,
             resolution=4, taper=[(0, 1.0), (1, .65)])
    tiers = [  # (count, z of stem start, stem length, leaf length, pitch deg, azimuth offset)
        (8, .42, .075, .18, 7, 0),
        (7, .54, .075, .195, 30, 25),
        (5, .66, .07, .18, 52, 40),
        (2, .74, .05, .13, 72, 60),
    ]
    k = 0
    for count, z0, sl, L, pitch, aoff in tiers:
        for i in range(count):
            a = math.radians(aoff + i * 360 / count + RNG.uniform(-10, 10))
            pz = math.radians(pitch + RNG.uniform(-6, 6))
            d = (math.cos(a) * math.cos(pz), math.sin(a) * math.cos(pz), math.sin(pz))
            p0 = (d[0] * .012, d[1] * .012, z0)
            p1 = (d[0] * sl, d[1] * sl, z0 + d[2] * sl + .01)
            pm = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2 - .012)
            dv4.tube("Stem%d" % k, [p0, pm, p1], radius=.006, res=6, paint=bark_p, out=sway, resolution=2, taper=[(0, 1.0), (1, .7)])
            LL = L * RNG.uniform(.92, 1.08)
            dv4.leaf("Leaf%d" % k, LL, LL * RNG.uniform(.7, .8), loc=p1, rot=(math.degrees(pz) + 6, RNG.uniform(-15, 15), math.degrees(a) - 90),
                     paint=leaf_p, out=sway, shape="fiddle", bend=.42, cup=.12, twist=RNG.uniform(-.5, .5), thickness=.005, nl=7, nw=4, wave=.5)
            k += 1
    return {"name": "PlantSmall", "tex": 1024, "budget": 6000, "floor": "F4EFE4"}
