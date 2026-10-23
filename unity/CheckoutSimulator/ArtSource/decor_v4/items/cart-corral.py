"""cart-corral: cart return bay (inside). Chrome rails on round base plates, a row of 5 nested chrome shopping carts (wire
baskets, red plastic handles / child-seat flaps / corner bumpers, black casters), navy+gold gantry sign with a cart pictogram,
gold floor stop. Footprint half .46 x 1.04, height <= 1.6 (Blender: X across, front = +Y, the carts' handles face +Y)."""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
import _lib_D as L
from dv4 import RNG

CONFIG = {"floor": "F4EFE4", "seed": 7}


def cart(i, yh, chrome, red, redl, black, grey, wirep):
    """One cart with its handle bar at y = yh, the basket running toward -Y. Nested carts (i > 0) use fewer wires."""
    n = "C%d" % i
    lite = i > 0
    # basket frame (trapezoid in plan + slight upward tilt toward the nose)
    wb, wn = .255, .20            # half widths at the back (handle end) / nose
    yb, yn = yh - .10, yh - .72    # basket back / nose y
    zt_b, zt_n = .97, .93          # top rim z
    zb_b, zb_n = .63, .67          # bottom rim z
    R = .0085
    top = [(-wb, yb, zt_b), (-wn, yn, zt_n), (wn, yn, zt_n), (wb, yb, zt_b)]
    bot = [(-wb + .01, yb, zb_b), (-wn + .01, yn, zb_n), (wn - .01, yn, zb_n), (wb - .01, yb, zb_b)]
    L.bar(n + "Top", top, r=R, paint=chrome, res=6)
    L.bar(n + "Bot", bot, r=R, paint=chrome, res=6)
    for k in range(4):
        L.bar(n + "V%d" % k, [bot[k], top[k]], r=R, paint=chrome, res=6)
    # wires: sides (vertical + 2 horizontal), nose, bottom
    nv = 7 if lite else 9
    for k in range(1, nv):
        t = k / nv
        y = yb + (yn - yb) * t
        for sx in (-1, 1):
            w = wb + (wn - wb) * t
            L.wire(n + "SW%d%d" % (k, sx), (sx * (w - .006), y, zb_b + (zb_n - zb_b) * t), (sx * (w - .003), y, zt_b + (zt_n - zt_b) * t), r=.0058, paint=wirep)
    for j, f in enumerate((.5,) if lite else (.33, .66)):
        for sx in (-1, 1):
            L.wire(n + "SH%d%d" % (j, sx), (sx * (wb - .004), yb, zb_b + (zt_b - zb_b) * f), (sx * (wn - .004), yn, zb_n + (zt_n - zb_n) * f), r=.0058, paint=wirep)
    nn = 5 if lite else 6
    for k in range(1, nn):
        x = -wn + 2 * wn * k / nn
        L.wire(n + "NW%d" % k, (x, yn + .002, zb_n), (x, yn + .002, zt_n), r=.0058, paint=wirep)
    for j, f in enumerate((.5,) if lite else (.33, .66)):
        L.wire(n + "NH%d" % j, (-wn, yn + .002, zb_n + (zt_n - zb_n) * f), (wn, yn + .002, zb_n + (zt_n - zb_n) * f), r=.0058, paint=wirep)
    nb = 5 if lite else 7
    for k in range(1, nb):
        t = k / nb
        L.wire(n + "BL%d" % k, (-wb + 2 * wb * t, yb, zb_b + .002), (-wn + 2 * wn * t, yn, zb_n + .002), r=.0058, paint=wirep)
    for k in range(1, 3 if lite else 5):
        t = k / (3 if lite else 5)
        w = wb + (wn - wb) * t
        L.wire(n + "BC%d" % k, (-w, yb + (yn - yb) * t, zb_b + (zb_n - zb_b) * t + .002), (w, yb + (yn - yb) * t, zb_b + (zb_n - zb_b) * t + .002), r=.0058, paint=wirep)
    # child-seat flap at the handle end: red plastic panel leaning into the basket + its wire frame, two leg holes read as dark slots
    dv4.cube(n + "Flap", (.44, .018, .2), loc=(0, yb - .005, zb_b + .2), rot=(8, 0, 0), paint=red, bevel=.006, segs=1)
    for sx in (-1, 1):
        dv4.cube(n + "Slot%d" % sx, (.08, .006, .05), loc=(sx * .1, yb - .018, zb_b + .21), rot=(8, 0, 0), paint=black, bevel=0)
    dv4.cube(n + "Seat", (.40, .13, .016), loc=(0, yb - .075, zb_b + .105), rot=(-6, 0, 0), paint=redl, bevel=.006, segs=1)
    # red bumper corners at the nose and at the back
    for sx in (-1, 1):
        dv4.cube(n + "BumpN%d" % sx, (.05, .05, .035), loc=(sx * (wn - .005), yn - .01, zt_n), paint=red, bevel=.012, segs=1)
        dv4.cube(n + "BumpB%d" % sx, (.045, .045, .035), loc=(sx * (wb - .005), yb + .005, zt_b), paint=red, bevel=.012, segs=1)
    # handle: two chrome uprights from the back top corners curling back into the grip bar at z 1.0
    for sx in (-1, 1):
        dv4.tube(n + "HU%d" % sx, [(sx * wb, yb, zt_b - .02), (sx * wb, yb + .035, zt_b + .02), (sx * wb, yb + .09, 1.0)], radius=R, res=8, paint=chrome, resolution=2)
    L.bar(n + "HB", [(-wb, yb + .09, 1.0), (wb, yb + .09, 1.0)], r=R, paint=chrome, res=8)
    dv4.cylinder(n + "Grip", .017, .34, loc=(-.17, yb + .09, 1.0), rot=(0, 90, 0), seg=8, paint=red)
    for sx in (-1, 1):
        dv4.sphere(n + "GripEnd%d" % sx, .019, loc=(sx * .185, yb + .09, 1.0), seg=6, rings=4, paint=red)
    # chassis: rear legs down from the back corners to the rear casters, a tapered lower frame forward, front struts up to the basket
    for sx in (-1, 1):
        dv4.tube(n + "Leg%d" % sx, [(sx * wb, yb, zb_b), (sx * .24, yb - .02, .35), (sx * .235, yb - .04, .1)], radius=R, res=6, paint=chrome, resolution=2)
        L.bar(n + "Rail%d" % sx, [(sx * .235, yb - .04, .1), (sx * .17, yn + .02, .1)], r=R, paint=chrome, res=6)
        L.bar(n + "Strut%d" % sx, [(sx * .17, yn + .02, .1), (sx * (wn - .005), yn + .02, zb_n)], r=R, paint=chrome, res=6)
    L.bar(n + "Cross", [(-.235, yb - .04, .1), (.235, yb - .04, .1)], r=R * .9, paint=chrome, res=6)
    L.bar(n + "CrossF", [(-.17, yn + .02, .1), (.17, yn + .02, .1)], r=R * .9, paint=chrome, res=6)
    # lower tray wires (visible under the first cart)
    for k in range(1, 1 if lite else 4):
        t = k / 4
        L.wire(n + "TW%d" % k, (-.235 + .47 * t, yb - .04, .102), (-.17 + .34 * t, yn + .02, .102), r=.003, paint=wirep)
    # casters: fork + black wheel (axle along X) + chrome hub
    for sx in (-1, 1):
        for y, x in ((yb - .04, .235), (yn + .02, .17)):
            dv4.cube(n + "Fork%d%s" % (sx, y), (.03, .05, .06), loc=(sx * x, y, .065), paint=grey, bevel=0)
            dv4.cylinder(n + "Wheel%d%s" % (sx, y), .04, .028, loc=(sx * x - .014, y, .04), rot=(0, 90, 0), seg=8 if lite else 12, paint=black)
            if not lite:
                dv4.cylinder(n + "Hub%d%s" % (sx, y), .016, .032, loc=(sx * x - .016, y, .04), rot=(0, 90, 0), seg=6, paint=grey)


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.2, light=.34)
    chrome = L.paint_chrome("Chrome")
    wirep = L.paint_chrome("Wire", light="EEF2F4", mid="8A969E", dark="3E4A52", k_ao=.35, k_light=.2)
    rail = L.paint_chrome("Rail", light="EEF2F4", mid="9DA9B1", dark="36414A")
    red = L.paint_plastic("Red", "CF3A2C", light="E86656", dark="7E1F16", gloss=.2)
    redl = L.paint_plastic("RedL", "D8463A", light="EC7566", dark="8A2A1E", gloss=.2)
    black = L.paint_plastic("Black", "2A2E33", light="5C636B", dark="121416", gloss=.25)
    grey = L.paint_plastic("Grey", "8E979D", light="C9D0D4", dark="4C545A", gloss=.3)
    navy = L.paint_plastic("Navy", "1D2B4F", light="3A4E7F", dark="101A33", gloss=.2)
    gold = dv4.paint_gold("Gold")
    goldp = L.paint_plastic("GoldP", "E6B23A", light="FFE07A", dark="9E6E14", gloss=.35)
    cream = L.paint_plastic("Cream", "F4EFE4", light="FFFFFF", dark="C9C0AE", gloss=.2)

    # ---- corral: two chrome side rails (top + knee rail) on 3 posts each, round base plates, back cross-rail
    X, YF, YB = .39, .97, -.97
    RR = .02
    for sx in (-1, 1):
        for y in (YF, 0.0, YB):
            dv4.cylinder("Post%d%s" % (sx, y), RR, .86, loc=(sx * X, y, .02), seg=12, paint=rail)
            dv4.lathe("Plate%d%s" % (sx, y), [(0, 0), (.065, 0), (.07, .008), (.06, .02), (0, .024)], seg=12, loc=(sx * X, y, 0), paint=grey)
            dv4.sphere("Cap%d%s" % (sx, y), RR, loc=(sx * X, y, .88), seg=8, rings=4, paint=rail)
        L.bar("RailT%d" % sx, [(sx * X, YF, .86), (sx * X, YB, .86)], r=RR, paint=rail, res=10)
        L.bar("RailK%d" % sx, [(sx * X, YF, .42), (sx * X, YB, .42)], r=RR * .8, paint=rail, res=8)
    L.bar("RailBack", [(-X, YB, .86), (X, YB, .86)], r=RR, paint=rail, res=10)
    L.bar("RailBackK", [(-X, YB, .42), (X, YB, .42)], r=RR * .8, paint=rail, res=8)
    # gold floor stop at the front edge (rounded bar on two feet)
    dv4.cube("Stop", (.78, .07, .05), loc=(0, YF - .02, .025), paint=goldp, bevel=.02, segs=3)
    # ---- sign gantry: two chrome posts on the back rail carrying a navy rounded panel with a gold frame + gold cart pictogram
    for sx in (-1, 1):
        dv4.cylinder("SignPost%d" % sx, .016, .62, loc=(sx * .24, YB, .88), seg=10, paint=rail)
    dv4.cube("SignFrame", (.66, .03, .5), loc=(0, YB, 1.34), paint=gold, bevel=.012, segs=3)
    dv4.cube("SignFace", (.6, .012, .44), loc=(0, YB + .014, 1.34), paint=navy, bevel=.01, segs=3)
    dv4.cube("SignBack", (.6, .012, .44), loc=(0, YB - .014, 1.34), paint=navy, bevel=.01, segs=3)
    L.picto_cart("Picto", (-.03, YB + .028, 1.27), .56, goldp, r=.015)
    L.picto_star("Star", (.22, YB + .028, 1.45), .11, goldp, r=.008)
    # ---- five nested carts, handles toward the front
    for i in range(5):
        cart(i, .94 - i * .255, chrome, red, redl, black, grey, wirep)
    return {"name": "CartCorral", "tex": 1024, "budget": 10000, "floor": "F4EFE4"}
