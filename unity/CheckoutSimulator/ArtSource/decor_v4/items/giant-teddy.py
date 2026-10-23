"""giant-teddy: giant honey-coloured plush teddy bear sitting on a teal gift box (cream ribbon + bow), legs forward, arms out.
Plush fur paint with stitched seams, lighter muzzle / inner ears / paw pads, black button eyes with a highlight, stitched nose
and mouth, a big red polka-dot ribbon bow at the neck. Original design (no known character).
Footprint half .45 x .40, height <= 1.4 (Blender Z up, front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
from dv4 import RNG
import _lib_H as H

CONFIG = {"floor": "F4EFE4", "seed": 12}
BY = -.05            # bear axis (y), the box is centred here too
BOX = (.70, .60, .30)
ZB = BOX[2]          # bear sits on the box top


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.22, light=.36)
    body_c = (0, BY, ZB + .30)
    paws = [(s * .32, BY + .26, .52) for s in (-1, 1)]
    feet = [(s * .20, BY + .35, .40) for s in (-1, 1)]
    patches = [((0, BY + .22, ZB + .33), (.17, .14, .21), "EFD4A0")]
    for px, py, pz in paws:
        patches.append(((px, py + .075, pz + .01), (.052, .05, .056), "EFD4A0"))
    for fx, fy, fz in feet:
        patches.append(((fx, fy + .085, fz + .01), (.07, .05, .078), "EFD4A0"))
        for k, (dx, dz) in enumerate(((-.045, .055), (0, .07), (.045, .055))):
            patches.append(((fx + dx, fy + .09, fz + dz + .01), (.02, .03, .02), "D9A86A"))
    seams = [(0.0, (ZB + .40, ZB + .56), BY + .12), (0.0, (1.17, 1.33), BY + .06)]
    fur = H.paint_plush("Fur", base="C98A45", dark="8A5628", light="E8B873", patches=patches, seams=seams)
    fur_l = H.paint_plush("FurLight", base="EBCB95", dark="B8905A", light="FBE8C4", nap=.15)
    black = H.paint_gloss("Button", "1C1A1A", dark="000000", light="8A8A8A", hl=.5, var=.0, k_ao=.3)
    nose = H.paint_gloss("Nose", "3A2418", dark="1C0F08", light="9A7A66", hl=.45, var=.1, k_ao=.3)
    white = dv4.paint_flat("White", "FFFFFF", variation=0, k_ao=.0, k_light=.0)
    thread = dv4.paint_flat("Thread", "3A2418", dark="1C0F08", variation=.2, k_ao=.3)
    ribbon = H.paint_gloss("Ribbon", "D2402F", dark="8A1E14", light="FF9A8A", hl=.45, dots=("FFD97A", 70.0), k_ao=.5)
    box = H.paint_gloss("Box", "1F9A8E", dark="12605A", light="7FD9CE", hl=.25, var=.15, k_ao=.6)
    box_rib = H.paint_gloss("BoxRibbon", "F4EFE4", dark="C9BFA8", light="FFFFFF", hl=.3, var=.08, k_ao=.55)

    # ---- gift box with ribbon bands and a standing bow on the front
    dv4.cube("Box", BOX, loc=(0, BY, ZB / 2), paint=box, bevel=.02, segs=2)
    t = .008; rw = .11
    dv4.cube("BandX", (rw, BOX[1] + 2 * t, ZB + 2 * t), loc=(0, BY, ZB / 2), paint=box_rib, bevel=.003, segs=1)
    dv4.cube("BandY", (BOX[0] + 2 * t, rw, ZB + 2 * t), loc=(0, BY, ZB / 2), paint=box_rib, bevel=.003, segs=1)
    H.bow("BoxBow", (0, BY + BOX[1] / 2 + t + .014, .175), size=.17, paint=box_rib, plane="XZ", thick=.016)

    # ---- bear: body, head, ears, muzzle, nose, mouth, eyes
    dv4.sphere("Body", 1.0, loc=body_c, scale=(.30, .27, .33), seg=22, rings=14, paint=fur)
    dv4.sphere("Head", .24, loc=(0, BY, 1.12), seg=22, rings=14, paint=fur)
    for s in (-1, 1):
        dv4.sphere("Ear", .085, loc=(s * .185, BY - .02, 1.29), seg=12, rings=8, paint=fur)
        dv4.sphere("EarIn", .055, loc=(s * .185, BY + .03, 1.29), scale=(1, .55, 1), seg=10, rings=6, paint=fur_l)
    dv4.sphere("Muzzle", 1.0, loc=(0, BY + .19, 1.06), scale=(.14, .11, .105), seg=14, rings=9, paint=fur_l)
    dv4.sphere("Nose", 1.0, loc=(0, BY + .285, 1.085), scale=(.05, .035, .036), seg=10, rings=6, paint=nose)
    dv4.tube("Mouth", [(0, BY + .29, 1.062), (0, BY + .292, 1.03)], radius=.006, res=5, paint=thread, kind="POLY", resolution=1)
    for s in (-1, 1):
        dv4.tube("Smile", [(0, BY + .292, 1.03), (s * .018, BY + .288, 1.015), (s * .04, BY + .27, 1.02)], radius=.006, res=5, paint=thread,
                 resolution=3)
        dv4.sphere("Eye", .033, loc=(s * .09, BY + .2, 1.17), scale=(1, .6, 1), seg=10, rings=7, paint=black)
        dv4.sphere("EyeHL", .010, loc=(s * .09 + .011, BY + .222, 1.182), seg=7, rings=5, paint=white)
    # ---- arms (tapered tubes) with round paws, legs forward with big feet
    for s in (-1, 1):
        dv4.tube("Arm", [(s * .24, BY + .02, .80), (s * .36, BY + .13, .67), (s * .32, BY + .24, .54)], radius=.088, res=10, paint=fur,
                 resolution=3, taper=[(0, .95), (.5, 1.0), (1, .8)])
        dv4.sphere("Paw", .088, loc=paws[0 if s < 0 else 1], scale=(1, 1, .95), seg=14, rings=9, paint=fur)
        dv4.tube("Leg", [(s * .14, BY + .10, .42), (s * .19, BY + .26, .40)], radius=.105, res=10, paint=fur, kind="POLY", resolution=1,
                 taper=[(0, 1.0), (1, .95)])
        dv4.sphere("Foot", .105, loc=feet[0 if s < 0 else 1], scale=(1, 1.08, .95), seg=14, rings=9, paint=fur)
    # ---- neck ribbon with a big bow at the front
    dv4.torus("Collar", .125, .024, loc=(0, BY + .005, .90), seg=20, minor=6, paint=ribbon, scale=(1, .95, 1.15))
    H.bow("Bow", (0, BY + .155, .865), size=.20, paint=ribbon, plane="XZ", thick=.017)
    return {"name": "GiantTeddy", "tex": 1024, "budget": 6000, "floor": "F4EFE4"}
