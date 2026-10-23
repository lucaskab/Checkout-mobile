"""party-tree: decorated fir tree in a red enamel tub with a gold band: seven lobed needle tiers whose branch tips droop,
glossy baubles in four colours, a gold ribbon garland spiralling up, a faceted gold star on top, four wrapped presents
underneath, and 28 fairy-light bulbs on four "Anim Blink" nodes (warm / pink, chasing).
Footprint half .50 x .50, height <= 2.3 (Blender Z up, front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
from dv4 import RNG
import _lib_H as H

CONFIG = {"floor": "F4EFE4", "seed": 33}
# (z_rim, r_rim, z_top, r_top, lobes)
TIERS = [(.44, .455, .74, .24, 9), (.70, .41, .98, .21, 8), (.95, .35, 1.22, .18, 8), (1.20, .29, 1.46, .15, 7),
         (1.44, .23, 1.68, .12, 7), (1.66, .17, 1.88, .085, 6), (1.86, .115, 2.07, .0, 5)]
LIGHT_W, LIGHT_P = "E_FFF1BE", "E_FF86BE"


def r_env(z):
    """Radius of the foliage envelope at height z (for the garland)."""
    pts = [(t[0], t[1]) for t in TIERS] + [(2.07, .02)]
    for (z0, r0), (z1, r1) in zip(pts, pts[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return .02


def build():
    dv4.FINISH.update(ao=.7, ao_dist=.3, light=.36)
    needles = H.paint_needles("Needles", tips=[(t[0], t[1]) for t in TIERS])
    bark = dv4.paint_wood("Bark", base="6E4A2E", dark="3F2A18", light="9A7250", scale=6.0, along="Z", tint=0)
    tub = H.paint_gloss("Tub", "C9372B", dark="7A1D15", light="FF9A8A", hl=.4, var=.12, k_ao=.6)
    gold = dv4.paint_gold("Gold")
    soil = dv4.paint_soil("Soil")
    baubles = [H.paint_gloss("BaubleRed", "D74A3C", dark="8A2418", light="FFC0B0", hl=.65, var=.08),
               H.paint_gloss("BaubleGold", "E0B040", dark="9A6E1A", light="FFF0B0", hl=.65, var=.08),
               H.paint_gloss("BaubleTeal", "1F9A8E", dark="0F5A52", light="B0F0E8", hl=.65, var=.08),
               H.paint_gloss("BaublePink", "EE8FAE", dark="B04A70", light="FFE0EA", hl=.65, var=.08),
               H.paint_gloss("BaubleNavy", "2A3F7A", dark="141F40", light="A0B8F0", hl=.65, var=.08)]
    ribbon = H.paint_gloss("Ribbon", "E8B84A", dark="A87820", light="FFF2C0", hl=.5, var=.1, k_ao=.5)
    cream = H.paint_gloss("Cream", "F4EFE4", dark="C9BFA8", light="FFFFFF", hl=.3, var=.08, k_ao=.55)
    gteal = H.paint_gloss("GiftTeal", "1F9A8E", dark="12605A", light="7FD9CE", hl=.25, var=.15, k_ao=.6)
    gpink = H.paint_gloss("GiftPink", "EE8FAE", dark="B05A78", light="FFD0E0", hl=.25, var=.15, k_ao=.6, dots=("FFFFFF", 45.0))
    gnavy = H.paint_gloss("GiftNavy", "1D2B4F", dark="0E1730", light="6A80C0", hl=.25, var=.15, k_ao=.6)
    gred = H.paint_gloss("GiftRed", "D74A3C", dark="8A2418", light="FFA090", hl=.25, var=.15, k_ao=.6, dots=("FFE8A0", 50.0))

    # ---- tub, soil, trunk
    dv4.lathe("Tub", [(0, 0), (.20, 0), (.215, .012), (.235, .21), (.252, .22), (.252, .25), (.236, .26), (.222, .26), (.215, .235), (0, .235)],
              seg=28, paint=tub)
    dv4.torus("TubBand", .242, .011, loc=(0, 0, .17), seg=28, minor=5, paint=gold)
    s = dv4.patch("Soil", .43, .43, 8, 8, loc=(0, 0, .232), paint=soil, disk=True)
    dv4.mod_displace(s, strength=.02, size=.08, mid=.4)
    dv4.lathe("Trunk", [(0, .22), (.06, .22), (.055, .6), (.045, 1.3), (.03, 1.9), (0, 1.9)], seg=12, paint=bark)
    # ---- needle tiers (lobed skirts with drooping tips) + an organic wobble
    for i, (zr, rr, zt, rt, lobes) in enumerate(TIERS):
        prof = [(rt * .9 + .03, zr + .09), (rr * .86, zr + .035), (rr, zr), (rr * .95, zr + .035), (rr * .78, zr + .10),
                (rr * .5, zr + (zt - zr) * .6), (rt, zt)]
        t = H.skirt("Tier%d" % i, prof, seg=40 if i < 4 else 32, lobes=lobes, amp=.10, dip=.06, paint=needles, a0=i * .4)
        dv4.mod_displace(t, strength=.022, size=.16, mid=.5)
    # ---- baubles hanging just under each rim (between the lobes), with a gold cap
    k = 0
    for i, (zr, rr, zt, rt, lobes) in enumerate(TIERS[:6]):
        n = max(3, lobes - 3)
        for j in range(n):
            a = (j + .5) * 2 * math.pi / n + i * .4 + math.pi / lobes
            rb = .048 - i * .004
            x, y, z = math.cos(a) * rr * .80, math.sin(a) * rr * .80, zr + .04 + rb * .45
            dv4.sphere("Bauble%d" % k, rb, loc=(x, y, z), seg=10, rings=7, paint=baubles[k % len(baubles)])
            dv4.lathe("Cap%d" % k, [(0, 0), (.012, 0), (.012, .016), (0, .016)], seg=8, loc=(x, y, z + rb * .92), paint=gold)
            k += 1
    # ---- gold ribbon garland spiralling up the tree
    pts = H.helix(.56, 1.95, lambda z: r_env(z) * .93 + .01, 3.6, n=96, a0=.6)
    dv4.tube("Garland", pts, radius=.017, res=6, paint=ribbon, kind="POLY", resolution=1)
    # ---- fairy lights: four Blink nodes (two warm, two pink) spread over the tiers
    nodes = ["Anim Blink", "Anim Blink.001", "Anim Blink.002", "Anim Blink.003"]
    for nd in nodes:
        dv4.pivot(nd, (0, 0, 1.2))
    k = 0
    for i, (zr, rr, zt, rt, lobes) in enumerate(TIERS):
        n = 6 if i < 3 else 4 if i < 6 else 2
        for j in range(n):
            a = j * 2 * math.pi / n + i * 1.1 + .3
            f = .55
            rl = rr * (1 - f) + rt * f + .02
            zl = zr + (zt - zr) * .42
            nd = nodes[k % 4]
            dv4.sphere("Bulb%d" % k, .022, loc=(math.cos(a) * rl, math.sin(a) * rl, zl), seg=7, rings=4, paint=None, out=nd,
                       mat_override=LIGHT_W if (k % 4) in (0, 2) else LIGHT_P)
            k += 1
    # ---- star on top
    H.star("Star", .13, .058, .07, loc=(0, 0, 2.16), paint=gold)
    dv4.lathe("StarBase", [(0, 2.03), (.02, 2.03), (.016, 2.07), (0, 2.07)], seg=8, paint=gold)
    # ---- presents around the tub
    H.gift("Gift0", (.27, .21, .17), (.33, .27, 0), gteal, cream, rot_z=18)
    H.gift("Gift1", (.22, .22, .22), (-.32, .25, 0), gpink, ribbon, rot_z=-12)
    H.gift("Gift2", (.30, .19, .13), (-.03, .39, 0), gnavy, ribbon, rot_z=4)
    H.gift("Gift3", (.24, .24, .2), (.27, -.31, 0), gred, cream, rot_z=30)
    return {"name": "PartyTree", "tex": 1024, "budget": 15000, "floor": "F4EFE4", "sharp_angle": 46}
