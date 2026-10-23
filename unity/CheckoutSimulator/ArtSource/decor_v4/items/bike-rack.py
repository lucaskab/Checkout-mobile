"""bike-rack: teal powder-coated serpentine steel rack with a red step-through bicycle parked alongside (spoked wheels,
cream fenders, leather saddle, wicker basket with flowers). Footprint half .92 x .30, height <= 1.3 (Blender Z up, front +Y)."""
import math
import sys, os
import dv4
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_E as E
from dv4 import RNG

CONFIG = {"floor": "C9C3B8", "seed": 24}


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.2, light=.38)
    teal = E.paint_painted("Rack", dv4.TEAL, light="9FE6DC", dark="0E5048", variation=.15)
    red = E.paint_painted("Frame", dv4.RED, light="FFB3A8", dark="7E1F16", variation=.12)
    cream = E.paint_painted("Fender", dv4.CREAM, light="FFFFFF", dark="B9AE98", variation=.12)
    steel = dv4.paint_iron("Steel", base="9AA4AC", mid="C9D2D6", edge="FFFFFF", rust_amt=.0)
    dark = dv4.paint_iron("Dark", base="262B30", mid="3B434A", edge="8A949C", rust_amt=.0)
    rubber = E.paint_rubber("Tyre")
    leather = dv4.paint_flat("Saddle", "5A3A28", "2E1C12", variation=.2, edge="9C7050")
    wicker = E.paint_wicker("Wicker")
    leafp = dv4.paint_leaf("Leaf", base="3E8E3B", dark="1E5A2A", light="86C654", veins=4)
    pink = E.paint_petal("PetalPink", "EE8FAE", "C2567E", "FFC6D8")
    gold = E.paint_petal("PetalGold", "F2C23F", "C08A16", "FFE9A0")
    white = E.paint_petal("PetalWhite", "FBF8F1", "C9BFAE", "FFFFFF")
    stemp = dv4.paint_flat("Stem", "4E8A34", "2E5A24", variation=.3)

    # ---- the rack: one continuous serpentine tube bolted to the pavement with two flanges
    ry = -.16
    wave = [(-.83, ry, .0), (-.83, ry, .42), (-.60, ry, .80), (-.30, ry, .34), (0, ry, .80), (.30, ry, .34), (.60, ry, .80), (.83, ry, .42), (.83, ry, .0)]
    dv4.tube("Wave", wave, radius=.026, res=10, paint=teal, resolution=8)
    for x in (-.83, .83):
        dv4.lathe("Flange", [(0, 0), (.065, 0), (.07, .012), (.065, .025), (.04, .03), (.04, .05), (0, .05)], seg=16, loc=(x, ry, 0), paint=teal)
        for a in range(0, 360, 90):
            dv4.sphere("Bolt", .008, loc=(x + math.cos(math.radians(a)) * .055, ry + math.sin(math.radians(a)) * .055, .024), seg=6, rings=4, paint=dark)

    # ---- the bicycle (parked parallel in front of the rack, facing +X)
    by = .06
    R = .31
    ax_r, ax_f = (-.50, by, R + .01), (.50, by, R + .01)
    for name, (x, y, z) in (("Rear", ax_r), ("Front", ax_f)):
        dv4.torus(name + "Tyre", R - .02, .027, loc=(x, y, z), rot=(90, 0, 0), seg=36, minor=8, paint=rubber)
        dv4.torus(name + "Rim", R - .045, .011, loc=(x, y, z), rot=(90, 0, 0), seg=36, minor=6, paint=steel)
        dv4.cylinder(name + "Hub", .022, .06, loc=(x, y + .03, z), rot=(90, 0, 0), seg=10, paint=steel)
        for i in range(12):
            a = math.radians(i * 30 + 7)
            c, s = math.cos(a), math.sin(a)
            dv4.tube(name + "Spoke%d" % i, [(x + c * .02, y + (.012 if i % 2 else -.012), z + s * .02), (x + c * (R - .05), y, z + s * (R - .05))],
                     radius=.003, res=4, paint=steel, kind="POLY", resolution=1)
        # fender: arc over the top of the wheel
        arc = E.arc_pts((x, y, z), R + .005, 20, 160, 10, "XZ")
        dv4.tube(name + "Fender", arc, radius=.018, res=6, paint=cream, resolution=2)
    bb = (0, by, .33)
    seat_top = (-.16, by, .80)
    head_top, head_bot = (.36, by, .82), (.42, by, .64)
    fr = .02
    dv4.tube("DownTube", [bb, head_bot], radius=fr, res=10, paint=red, kind="POLY", resolution=1)
    dv4.tube("TopTube", [seat_top, (.1, by, .72), head_top], radius=fr * .9, res=10, paint=red, resolution=3)   # step-through curve
    dv4.tube("SeatTube", [bb, seat_top], radius=fr, res=10, paint=red, kind="POLY", resolution=1)
    dv4.tube("HeadTube", [(.43, by, .60), (.35, by, .86)], radius=fr * 1.2, res=10, paint=red, kind="POLY", resolution=1)
    for sy in (-1, 1):
        o = sy * .035
        dv4.tube("ChainStay", [(bb[0], by + o, bb[2]), (ax_r[0], ax_r[1] + o, ax_r[2])], radius=.012, res=6, paint=red, kind="POLY", resolution=1)
        dv4.tube("SeatStay", [(seat_top[0], by + o * .5, seat_top[2] - .02), (ax_r[0], ax_r[1] + o, ax_r[2])], radius=.012, res=6, paint=red, kind="POLY", resolution=1)
        dv4.tube("Fork", [(.43, by + o * .3, .60), (.47, by + o, .45), (ax_f[0], ax_f[1] + o, ax_f[2])], radius=.013, res=6, paint=red, resolution=2)
    # crank, chainring, pedals, chain
    dv4.torus("ChainRing", .085, .009, loc=(0, by + .05, .33), rot=(90, 0, 0), seg=24, minor=5, paint=steel)
    dv4.torus("Cog", .035, .008, loc=(ax_r[0], ax_r[1] + .05, ax_r[2]), rot=(90, 0, 0), seg=14, minor=5, paint=steel)
    dv4.tube("Chain", [(0, by + .05, .33 + .085), (ax_r[0], ax_r[1] + .05, ax_r[2] + .035)], radius=.006, res=4, paint=dark, kind="POLY", resolution=1)
    dv4.tube("Chain2", [(0, by + .05, .33 - .085), (ax_r[0], ax_r[1] + .05, ax_r[2] - .035)], radius=.006, res=4, paint=dark, kind="POLY", resolution=1)
    dv4.cylinder("BBShell", .028, .10, loc=(0, by - .05, .33), rot=(-90, 0, 0), seg=10, paint=red)
    for sy, a in ((1, 60), (-1, 240)):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        dv4.tube("Crank", [(0, by + sy * .065, .33), (c * .16, by + sy * .07, .33 + s * .16)], radius=.009, res=6, paint=steel, kind="POLY", resolution=1)
        dv4.cube("Pedal", (.07, .05, .02), loc=(c * .16, by + sy * .10, .33 + s * .16), paint=dark, bevel=.005, segs=1)
    # saddle, seat post, handlebar, stem, grips, kickstand, bell
    dv4.tube("SeatPost", [seat_top, (-.17, by, .90)], radius=.012, res=8, paint=steel, kind="POLY", resolution=1)
    dv4.sphere("Saddle", .1, loc=(-.19, by, .93), scale=(1.4, .75, .3), seg=14, rings=8, paint=leather)
    dv4.sphere("SaddleNose", .045, loc=(-.08, by, .925), scale=(1.4, .8, .45), seg=10, rings=6, paint=leather)
    dv4.tube("Stem", [(.35, by, .86), (.33, by, .97)], radius=.013, res=8, paint=steel, kind="POLY", resolution=1)
    bar = [(.22, by - .21, .98), (.30, by - .18, .98), (.33, by - .08, .98), (.33, by + .08, .98), (.30, by + .18, .98), (.22, by + .21, .98)]
    dv4.tube("Handlebar", bar, radius=.011, res=8, paint=steel, resolution=3)
    for sy in (-1, 1):
        dv4.tube("Grip", [(.30, by + sy * .18, .98), (.21, by + sy * .215, .98)], radius=.016, res=8, paint=leather, kind="POLY", resolution=1)
    dv4.sphere("Bell", .022, loc=(.31, by - .12, 1.0), scale=(1, 1, .7), seg=10, rings=5, paint=dv4.paint_gold("Bell"))
    dv4.tube("KickStand", [(-.12, by + .04, .30), (-.18, by + .17, .0)], radius=.008, res=6, paint=dark, kind="POLY", resolution=1)
    # wicker basket on the front with a bunch of flowers
    bx, bz = .50, .78
    basket = [(0, 0), (.11, 0), (.12, .012), (.155, .17), (.165, .185), (.15, .185), (.145, .17), (.108, .015), (0, .015)]
    dv4.lathe("Basket", [(r, z) for r, z in basket], seg=18, loc=(bx, by, bz), paint=wicker, scallop=(18, .04))
    dv4.torus("BasketRim", .158, .011, loc=(bx, by, bz + .18), seg=18, minor=6, paint=wicker)
    dv4.tube("BasketStrap", [(bx - .13, by, bz + .17), (bx - .16, by, bz + .10), (bx - .12, by, bz + .05)], radius=.008, res=6, paint=leather, resolution=2)
    pets = (pink, gold, white)
    for i in range(7):
        a = math.radians(i * 51 + 20)
        r = .02 + .07 * (i % 3) / 2
        x, y = bx + math.cos(a) * r, by + math.sin(a) * r
        h = RNG.uniform(.13, .20)
        E.stem("BS%d" % i, (x, y, bz + .05), (x * 1.0, y, bz + .05 + h), stemp, radius=.005)
        E.flower_head("BF%d" % i, RNG.uniform(.042, .052), (x, y, bz + .04 + h), pets[i % 3], rot=(RNG.uniform(-20, 20), RNG.uniform(-20, 20), 0))
    for i in range(8):
        a = math.radians(i * 45 + 10)
        dv4.leaf("BL%d" % i, .09, .05, loc=(bx + math.cos(a) * .12, by + math.sin(a) * .12, bz + .17), rot=(60, 0, math.degrees(a) - 90 + RNG.uniform(-20, 20)),
                 paint=leafp, shape="spade", bend=.3, cup=.15, thickness=.003, nl=4, nw=2)
    return {"name": "BikeRack", "tex": 1024, "budget": 10000, "floor": "C9C3B8"}
