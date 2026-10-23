"""aquarium: round column aquarium on a navy cabinet with gold-trimmed door panels; open-top glass cylinder tank (G_Glass)
with a water surface, coloured gravel, rocks, a sand castle and a sunken treasure chest, three clumps of seaweed on
"Anim Sway" nodes, six big tropical fish orbiting on "Anim Spin" (pivot on the tank axis), a bubble column on "Anim Bob",
a navy/gold rim with a glowing LED ring (E_) on top so the tank stays readable from the high game camera.
Footprint half .45 x .45, height <= 1.9 (Blender Z up, front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
from dv4 import RNG
import _lib_H as H

CONFIG = {"floor": "F4EFE4", "seed": 44}
ZT0, ZT1, RT = .60, 1.66, .375     # tank bottom / top / radius
ZG = .635                           # gravel surface


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.25, light=.36)
    cab = H.paint_cabinet("Cabinet", panels=((-27, 15), (27, 15)), z=(.10, .46))
    navy = dv4.paint_flat("Navy", "1D2B4F", dark="0C1430", variation=.18, edge="5468A0")
    gold = dv4.paint_gold("Gold")
    gravel = H.paint_gravel("Gravel")
    rock = dv4.paint_stone("Rock", base="6E7F86", dark="3C4A52", light="9FB0B6", moss="3E9A7C", moss_amt=.9)
    sand = dv4.paint_stone("Castle", base="E6C98E", dark="B6914E", light="F7E6C0", moss_amt=.0)
    roof = H.paint_gloss("Roof", "D74A3C", dark="8A2418", light="FF9A8A", hl=.3, var=.15, k_ao=.6)
    dark = dv4.paint_flat("Dark", "1A1F2E", dark="05070C", variation=.2, k_ao=.4)
    chest = dv4.paint_wood("Chest", base="7A4A28", dark="3F2412", light="A8713F", scale=6.0, along="X", tint=0)
    bubble = H.paint_gloss("Bubble", "DDF4FF", dark="9CC8E0", light="FFFFFF", hl=.6, var=.0, k_ao=.1, k_light=.1)
    weed = [dv4.paint_leaf("Weed0", base="2E8F4E", dark="175A2E", light="7FD36A", vein="A8E890", veins=3),
            dv4.paint_leaf("Weed1", base="1F9A8E", dark="12605A", light="7FDCCB", vein="B0F0E8", veins=3),
            dv4.paint_leaf("Weed2", base="6DAA3A", dark="356B1E", light="B4E07A", vein="D8F2A8", veins=3)]
    fishp = [(H.paint_fish("Clown", base="F07A1F", stripe="FFFFFF", stripes=((.2, .3), (.5, .6), (.82, .9))), H.paint_gloss("ClownFin", "F59A4A", light="FFE0C0", hl=.3, var=0, k_ao=.3)),
             (H.paint_fish("Tang", base="2F6FD6", stripe="121B3A", stripe_edge="2F6FD6", stripes=((.3, .62),), belly="7FB7FF"), H.paint_gloss("TangFin", "F5D23A", light="FFF6C0", hl=.3, var=0, k_ao=.3)),
             (H.paint_fish("Yellow", base="F5C928", stripe="FFF4C0", stripes=(), belly="FFF0A0"), H.paint_gloss("YellowFin", "F0B020", light="FFF0B0", hl=.3, var=0, k_ao=.3)),
             (H.paint_fish("Pinky", base="EE6FA0", stripe="FFFFFF", stripe_edge="B03A6A", stripes=((.4, .48), (.66, .72)), belly="FFD0E0"), H.paint_gloss("PinkFin", "F59AC0", light="FFE0EE", hl=.3, var=0, k_ao=.3)),
             (H.paint_fish("Teal", base="24B5A5", stripe="FFE066", stripe_edge="137068", stripes=((.3, .36), (.55, .6)), belly="BFF2EA"), H.paint_gloss("TealFin", "6FD9CC", light="E0FFF8", hl=.3, var=0, k_ao=.3))]

    # ---- cabinet: round navy body with painted door panels, gold base ring and top rim, two gold handles
    dv4.lathe("Cabinet", [(0, 0), (.39, 0), (.41, .02), (.41, .52), (.43, .54), (.43, .575), (.40, .59), (0, .59)], seg=40, paint=cab)
    dv4.lathe("BaseRing", [(.405, .018), (.425, .025), (.425, .05), (.408, .055)], seg=40, paint=gold, cap=False)
    dv4.torus("TopRim", .432, .012, loc=(0, 0, .575), seg=40, minor=6, paint=gold)
    for a in (-7, 7):
        ar = math.radians(a)
        dv4.sphere("Handle", .016, loc=(math.sin(ar) * .415, math.cos(ar) * .415, .30), scale=(1, 1, 1.9), seg=8, rings=6, paint=gold)
    # ---- tank: glass cylinder (open), water surface disc, tank floor
    dv4.lathe("Glass", [(RT, ZT0), (RT, ZT1)], seg=48, paint=None, cap=False, mat_override="G_Glass")
    dv4.lathe("Water", [(RT - .004, 1.575), (RT - .004, 1.585), (0, 1.585)], seg=48, paint=None, cap=True, mat_override="G_Glass")
    dv4.lathe("Floor", [(0, ZT0), (RT - .002, ZT0), (RT - .002, ZT0 + .025), (0, ZT0 + .025)], seg=40, paint=navy)
    g = dv4.patch("Gravel", .74, .74, 12, 12, loc=(0, 0, ZG), paint=gravel, disk=True)
    dv4.mod_displace(g, strength=.03, size=.06, mid=.45)
    # ---- rocks, castle (back), chest (front-right)
    for i, (x, y, s) in enumerate(((-.24, -.14, .075), (.26, -.10, .06), (-.25, .14, .05))):
        r = dv4.icosphere("Rock%d" % i, s, loc=(x, y, ZG + s * .45), scale=(1.3, 1.0, .75), subdiv=2, paint=rock, rot=(0, 0, i * 40))
        dv4.mod_displace(r, strength=.03, size=.05, mid=.5)
    cx, cy = 0.02, -.19
    dv4.lathe("Keep", [(0, 0), (.095, 0), (.095, .30), (.108, .30), (.108, .335), (.09, .335), (.09, .31), (0, .31)], seg=16, loc=(cx, cy, ZG - .01),
              paint=sand)
    dv4.lathe("KeepRoof", [(0, 0), (.115, 0), (0, .17)], seg=16, loc=(cx, cy, ZG + .325), paint=roof)
    dv4.sphere("KeepBall", .018, loc=(cx, cy, ZG + .50), seg=8, rings=5, paint=gold)
    for sx in (-1, 1):
        dv4.lathe("Tower", [(0, 0), (.055, 0), (.055, .19), (.065, .19), (.065, .215), (.05, .215), (0, .215)], seg=12, loc=(cx + sx * .165, cy - .02, ZG - .01), paint=sand)
        dv4.lathe("TowerRoof", [(0, 0), (.07, 0), (0, .12)], seg=12, loc=(cx + sx * .165, cy - .02, ZG + .205), paint=roof)
    dv4.cube("Wall", (.28, .06, .14), loc=(cx, cy + .03, ZG + .06), paint=sand, bevel=.006, segs=2)
    dv4.cube("Gate", (.06, .02, .09), loc=(cx, cy + .062, ZG + .04), paint=dark, bevel=.004, segs=1)
    for sx in (-1, 1):
        dv4.cube("Window", (.025, .02, .04), loc=(cx + sx * .165, cy + .042, ZG + .12), paint=dark, bevel=.003, segs=1)
    chx, chy = -.06, .25
    dv4.cube("Chest", (.12, .085, .065), loc=(chx, chy, ZG + .028), rot=(0, 0, 20), paint=chest, bevel=.006, segs=2)
    dv4.cylinder("ChestLid", .043, .12, loc=(chx - .06 * math.cos(math.radians(20)), chy - .06 * math.sin(math.radians(20)), ZG + .06),
                 rot=(0, 90, 20), seg=10, paint=chest)
    dv4.cube("ChestBand", (.122, .018, .067), loc=(chx, chy, ZG + .029), rot=(0, 0, 20), paint=gold, bevel=.003, segs=1)
    # ---- seaweed clumps (Anim Sway, pivot at the base of each clump)
    clumps = [((-.21, .06), 0), ((.22, .0), 1), ((.14, .20), 2)]
    for i, ((x, y), pi_) in enumerate(clumps):
        node = "Anim Sway" if i == 0 else "Anim Sway.%03d" % i
        dv4.pivot(node, (x, y, ZG))
        for j in range(5):
            a = j * 72 + RNG.uniform(-15, 15)
            L = RNG.uniform(.30, .52); W = RNG.uniform(.045, .07)
            lean = RNG.uniform(0, 360)       # random lean azimuth, steep so the blades stay inside the glass
            dv4.leaf("Weed%d_%d" % (i, j), L, W, loc=(x + math.cos(math.radians(a)) * .02, y + math.sin(math.radians(a)) * .02, ZG - .01),
                     rot=(84 + RNG.uniform(-3, 3), RNG.uniform(-20, 20), lean - 90), paint=weed[(pi_ + j) % 3], out=node, shape="ellipse",
                     bend=.05, cup=.25, twist=RNG.uniform(-1, 1), thickness=.004, nl=7, nw=3, wave=RNG.uniform(.8, 1.4))
    # ---- fish orbiting the axis (Anim Spin)
    spin = "Anim Spin"; dv4.pivot(spin, (0, 0, 1.0))
    fish = [(.24, 20, .84, 1.0), (.21, 95, 1.10, .85), (.25, 160, 1.42, .8), (.19, 230, .98, .75), (.24, 300, 1.26, .95), (.17, 350, 1.50, .7)]
    for i, (rr, ang, z, sc) in enumerate(fish):
        a = math.radians(ang)
        fp, fin = fishp[i % len(fishp)]
        H.fish("Fish%d" % i, L=.22 * sc, H=.095 * sc, W=.046 * sc, loc=(math.cos(a) * rr, math.sin(a) * rr, z), rot=(0, 0, ang), paint=fp,
               fin_paint=fin, out=spin, seg=10, nl=9, rnd=i / 6)
    # ---- bubbles (Anim Bob) from an air stone
    bob = "Anim Bob"; dv4.pivot(bob, (.12, .17, 1.0))
    dv4.sphere("AirStone", .02, loc=(.12, .17, ZG), scale=(1.3, 1, .6), seg=8, rings=5, paint=rock)
    for i, z in enumerate((.72, .86, 1.01, 1.16, 1.31, 1.46)):
        dv4.sphere("Bubble%d" % i, .010 + i * .0018, loc=(.12 + math.sin(i * 1.7) * .02, .17 + math.cos(i * 1.3) * .02, z), seg=7, rings=5, paint=bubble, out=bob)
    # ---- hood: navy canopy with a gold band, lamp ring under its rim, gold finial
    dv4.lathe("Rim", [(RT - .012, ZT1 - .03), (RT - .012, ZT1 + .035), (.395, ZT1 + .05), (.42, ZT1 + .04), (.425, ZT1), (.41, ZT1 - .04), (RT - .012, ZT1 - .04)],
              seg=40, paint=navy, cap=False)
    dv4.torus("RimBand", .418, .011, loc=(0, 0, ZT1 + .02), seg=40, minor=6, paint=gold)
    dv4.torus("Lamp", RT + .006, .010, loc=(0, 0, ZT1 + .048), seg=40, minor=5, paint=None, mat_override="E_DFF6FF")
    return {"name": "Aquarium", "tex": 1024, "budget": 10000, "floor": "F4EFE4"}
