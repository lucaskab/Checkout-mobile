"""fountain: two-tier carved stone fountain with gold bands, running water (crown of jets on "Anim Spin").
Footprint half 1.12 x 1.12, height <= 1.9 (Blender Z up, front +Y; the model is radially symmetric)."""
import math
import dv4
from dv4 import RNG

CONFIG = {"floor": "C9C3B8", "seed": 5}


def build():
    dv4.FINISH.update(ao=.7, ao_dist=.35, light=.38)
    stone = dv4.paint_stone("Stone", base="DCCBA9", dark="A48B62", light="F2E8D2", moss_amt=.8, moss_z=.6, blocks=(16, [.29], .13, .44))
    stone_hi = dv4.paint_stone("StoneHi", base="E0D0AF", dark="AC9469", light="F4EAD6", moss_amt=.0)
    gold = dv4.paint_gold("Gold")
    pool = dv4.paint_water("Pool", deep="1F7FAE", shallow="5FC2DE", scale=9.0, caustic=.5)
    bowl_w = dv4.paint_water("BowlWater", deep="3AA3C9", shallow="8ADCEC", scale=14.0, caustic=.45)
    stream = dv4.paint_stream("Stream")

    # lower basin: plinth step, masonry wall, rolled carved lip, inner floor at z .18
    basin = [(0, 0), (1.08, 0), (1.115, .03), (1.115, .085), (1.07, .105), (1.0, .13), (.985, .30), (1.0, .44), (1.03, .46),
             (1.075, .49), (1.085, .53), (1.06, .57), (1.0, .585), (.93, .57), (.905, .53), (.9, .40), (.9, .18), (0, .18)]
    dv4.lathe("Basin", basin, seg=56, paint=stone)
    dv4.lathe("GoldBand", [(.995, .385), (1.02, .395), (1.02, .435), (1.0, .445)], seg=56, paint=gold, cap=False)
    dv4.lathe("GoldLip", [(1.075, .485), (1.098, .495), (1.098, .53), (1.08, .545)], seg=56, paint=gold, cap=False)
    dv4.torus("Rope", 1.078, .024, loc=(0, 0, .115), seg=56, minor=6, paint=stone_hi)
    dv4.lathe("PoolWater", [(0, .50), (.5, .50), (.9, .50)], seg=48, paint=pool)
    # pedestal: base, fluted shaft with a ring, capital
    dv4.lathe("ColBase", [(0, .18), (.36, .18), (.36, .25), (.31, .28), (.23, .31), (.21, .34)], seg=32, paint=stone_hi)
    dv4.lathe("Shaft", [(.2, .34), (.175, .45), (.16, .62), (.17, .78), (.2, .86)], seg=56, paint=stone_hi, scallop=(14, .05), cap=False)
    dv4.torus("ShaftRing", .19, .02, loc=(0, 0, .6), seg=32, minor=6, paint=gold)
    dv4.lathe("Capital", [(.19, .86), (.27, .9), (.34, .935), (.35, .965), (.31, .975), (0, .975)], seg=32, paint=stone_hi)
    # upper bowl: scalloped lip, inner floor at 1.01, water at 1.12
    bowl = [(0, .965), (.14, .965), (.32, .99), (.5, 1.03), (.6, 1.085), (.64, 1.13), (.615, 1.18), (.55, 1.18), (.52, 1.12),
            (.45, 1.05), (.3, 1.015), (0, 1.005)]
    dv4.lathe("Bowl", bowl, seg=64, paint=stone_hi, scallop=(8, .075))
    dv4.lathe("BowlWater", [(0, 1.12), (.25, 1.12), (.47, 1.12)], seg=40, paint=bowl_w)
    # finial baluster with the spout on top
    dv4.lathe("Finial", [(0, 1.005), (.14, 1.005), (.12, 1.05), (.08, 1.2), (.09, 1.3), (.145, 1.36), (.165, 1.4), (.125, 1.44), (0, 1.455)],
              seg=24, paint=stone_hi)
    dv4.torus("FinialRing", .105, .016, loc=(0, 0, 1.24), seg=24, minor=5, paint=gold)
    # ---- moving water: the crown of jets spins slowly (readable "running water")
    spin = "Anim Spin"; dv4.pivot(spin, (0, 0, 1.44))
    dv4.lathe("Jet", [(0, 1.43), (.035, 1.43), (.045, 1.58), (.075, 1.7), (.06, 1.77), (0, 1.8)], seg=14, paint=stream, out=spin)
    for i in range(8):
        a = math.radians(i * 45 + 22.5)
        c, s = math.cos(a), math.sin(a)
        pts = [(0, 0, 1.72), (.16 * c, .16 * s, 1.77), (.33 * c, .33 * s, 1.56), (.42 * c, .42 * s, 1.2)]
        dv4.tube("Arc%d" % i, pts, radius=.021, res=6, paint=stream, out=spin, resolution=3, taper=[(0, .6), (.3, 1.0), (1, .85)])
        dv4.torus("Splash%d" % i, .065, .012, loc=(.42 * c, .42 * s, 1.125), seg=12, minor=5, paint=stream, out=spin)
    # ---- overflow: water pours from the bowl's eight lobes into the pool
    for i in range(8):
        a = math.radians(i * 45)
        c, s = math.cos(a), math.sin(a)
        pts = [(.6 * c, .6 * s, 1.17), (.69 * c, .69 * s, 1.1), (.72 * c, .72 * s, .85), (.70 * c, .70 * s, .52)]
        dv4.tube("Fall%d" % i, pts, radius=.03, res=6, paint=stream, resolution=3, taper=[(0, .7), (.25, 1.0), (1, 1.35)])
        dv4.torus("Ring%d" % i, .1, .016, loc=(.70 * c, .70 * s, .505), seg=14, minor=5, paint=stream)
        dv4.torus("Ring2_%d" % i, .17, .011, loc=(.70 * c, .70 * s, .503), seg=16, minor=5, paint=stream)
    return {"name": "Fountain", "tex": 1024, "budget": 15000, "floor": "C9C3B8"}
