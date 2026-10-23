"""wine-barrel: upright oak barrel (bulged staves, riveted iron hoops) used as a wine display: three bottles, two glasses of red
wine and a bunch of grapes on the plank lid, a small wooden crate of bottles at its front-right foot.
Footprint half .45 x .45, height <= 1.4 (Blender Z up, front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
from dv4 import RNG
import _lib_H as H

CONFIG = {"floor": "F4EFE4", "seed": 21}
BC = (-.09, -.08)          # barrel axis (the crate sits front-right)
LID = .855                 # top of the lid


def bottle(name, loc, paint, out="Body", seg=14, simple=False):
    if simple:
        prof = [(0, 0), (.036, 0), (.039, .02), (.039, .17), (.03, .2), (.015, .23), (.013, .3), (.0155, .305), (.0155, .325), (0, .328)]
    else:
        prof = [(0, 0), (.034, 0), (.038, .006), (.039, .03), (.039, .17), (.034, .195), (.022, .215), (.014, .235), (.013, .3),
                (.0155, .305), (.0155, .325), (.012, .328), (0, .328)]
    dv4.lathe(name, prof, seg=seg, loc=loc, paint=paint, out=out)


def wine_glass(name, loc, wine, seg=14):
    bowl = [(.009, .09), (.03, .1), (.042, .13), (.043, .17), (.038, .2), (.034, .215)]
    dv4.lathe(name + "Bowl", bowl, seg=seg, loc=loc, paint=None, cap=False, mat_override="G_Glass")
    foot = [(0, 0), (.032, 0), (.034, .004), (.02, .012), (.008, .03), (.006, .07), (.009, .09), (0, .095)]
    dv4.lathe(name + "Foot", foot, seg=seg, loc=loc, paint=None, mat_override="G_Glass")
    dv4.lathe(name + "Wine", [(0, .1), (.024, .1), (.037, .125), (.041, .16), (.040, .172), (0, .172)], seg=seg, loc=loc, paint=wine)


def grapes(loc, grape, leafp, stem):
    """A bunch of grapes lying on the lid: layered berries narrowing toward the tip (+Y), a stalk and a vine leaf."""
    rows = [(3, 0.0, .05), (4, .036, .046), (3, .07, .04), (2, .1, .033)]
    for n, y, spread in rows:
        for i in range(n):
            a = i * 2 * math.pi / n + y * 9
            rr = spread * (1 if n > 1 else 0)
            r = RNG.uniform(.021, .025)
            dv4.sphere("Grape", r, loc=(loc[0] + math.cos(a) * rr * .85, loc[1] + y + math.sin(a) * rr * .35, loc[2] + r * .9 + math.cos(a) * rr * .3 + .004),
                       seg=8, rings=5, paint=grape)
    for dy, dz, r in ((.02, .04, .023), (-.025, .035, .022), (.055, .045, .021)):
        dv4.sphere("GrapeTop", r, loc=(loc[0] + .012, loc[1] + dy, loc[2] + dz + r * .5), seg=8, rings=5, paint=grape)
    dv4.tube("Stalk", [(loc[0], loc[1] - .045, loc[2] + .035), (loc[0] - .01, loc[1] - .075, loc[2] + .05), (loc[0] - .03, loc[1] - .105, loc[2] + .04)],
             radius=.005, res=5, paint=stem, resolution=3)
    dv4.leaf("VineLeaf", .12, .11, loc=(loc[0] - .03, loc[1] - .105, loc[2] + .04), rot=(-12, 0, 150), paint=leafp, shape="heart",
             bend=.2, cup=.12, thickness=.004, nl=5, nw=4, wave=.6)


def build():
    dv4.FINISH.update(ao=.66, ao_dist=.25, light=.34)
    cx, cy = BC
    staves = H.paint_staves("Staves", n=20, center=BC, base="B5703B", dark="5E3519", light="D99A58")
    lid = H.paint_planks("Lid", base="C98551", dark="6B4128", light="E6B06A", w=.082, along="X", off=cy + .041)
    iron = dv4.paint_iron("Hoop", base="2A2F36", mid="4A525B", edge="9AA3AC", rust="7A4423", rust_amt=.25)
    crate_w = dv4.paint_wood("Crate", base="CFA062", dark="7E5631", light="EAC890", scale=4.0, dist=2.0, along="X", tint=.35)
    bot = H.paint_bottle("Bottle", zlab=(LID + .05, LID + .135), zcap=LID + .295)
    bot2 = H.paint_bottle("BottleC", glass="2A2240", glass_d="140F22", glass_l="8A7BB0", zlab=(.08, .165), zcap=.325, cap="E0B040",
                          cap_l="FFE38A", seal="1F9A8E")
    wine = H.paint_gloss("Wine", "6E1028", dark="34091A", light="D8607A", hl=.45, k_ao=.4)
    grape = H.paint_gloss("Grape", "5B2F7C", dark="2E1442", light="CDA8EA", hl=.5, var=.25, k_ao=.55)
    leafp = dv4.paint_leaf("VineLeaf", base="4C9A3C", dark="275B28", light="8FD05E", veins=5)
    stem = dv4.paint_wood("Stem", base="7A5A3E", dark="4A3524", light="A07C57", scale=8.0, along="Y", tint=0)

    # ---- barrel: bulged stave body with a chime (recessed rim) at both ends, plank lid inset at the top
    prof = [(0, 0), (.25, 0), (.268, .012), (.285, .08), (.301, .22), (.309, .40), (.306, .55), (.293, .70), (.273, .80), (.262, .83),
            (.236, .835), (.236, .815), (0, .815)]
    dv4.lathe("Barrel", prof, seg=32, loc=(cx, cy, 0), paint=staves)
    dv4.lathe("Lid", [(0, .81), (.238, .81), (.243, .83), (.243, LID), (0, LID)], seg=32, loc=(cx, cy, 0), paint=lid)

    def rz(z):
        for (r0, z0), (r1, z1) in zip(prof[1:], prof[2:]):
            if z0 <= z <= z1 and z1 > z0:
                return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
        return .3
    for z in (.055, .235, .60, .745):
        r = rz(z + .02) + .010
        dv4.lathe("Hoop%d" % int(z * 100), [(rz(z) - .003, z), (r, z + .005), (r, z + .040), (rz(z + .045) - .003, z + .045)], seg=32,
                  loc=(cx, cy, 0), paint=iron, cap=False)
        for k in range(6):
            a = k * math.pi / 3 + .35
            dv4.sphere("Rivet", .008, loc=(cx + math.cos(a) * r, cy + math.sin(a) * r, z + .0225), seg=5, rings=3, paint=iron)
    # bung on the front belly
    dv4.lathe("Bung", [(0, 0), (.022, 0), (.024, .008), (.019, .012), (0, .012)], seg=10, loc=(cx, cy + .308, .42), rot=(-90, 0, 0), paint=stem)

    # ---- display on the lid: three bottles back-left, two glasses front-right, grapes at the front
    for i, ang in enumerate((205, 250, 160)):
        a = math.radians(ang); rr = .14 if i < 2 else .12
        bottle("Bottle%d" % i, (cx + math.cos(a) * rr, cy + math.sin(a) * rr, LID), bot, seg=10)
    for i, ang in enumerate((15, 320)):
        a = math.radians(ang)
        wine_glass("Glass%d" % i, (cx + math.cos(a) * .15, cy + math.sin(a) * .15, LID), wine, seg=10)
    grapes((cx - .01, cy + .06, LID), grape, leafp, stem)

    # ---- crate of bottles at the front-right foot
    cl = (.265, .295)
    H.crate("Crate", (.35, .25, .20), (cl[0], cl[1], 0), crate_w, rot_z=-6)
    for ix, x in enumerate((-.10, 0, .10)):
        for iy, y in enumerate((-.052, .052)):
            a = math.radians(-6); px = cl[0] + x * math.cos(a) - y * math.sin(a); py = cl[1] + x * math.sin(a) + y * math.cos(a)
            bottle("CrateBottle%d%d" % (ix, iy), (px, py, .018), bot2, seg=8, simple=True)
    return {"name": "WineBarrel", "tex": 1024, "budget": 6000, "floor": "F4EFE4"}
