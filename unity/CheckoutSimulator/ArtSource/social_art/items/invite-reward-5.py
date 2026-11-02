"""invite-reward-5 (5 invited friends reached the Spaeti): the friends statue. A cream marble statue of a chunky
shopkeeper (cap, apron, moustache) waving, holding hands with a little friend who carries a shopping bag, in the style of
the game's own characters, on a stepped navy plinth with thin gold bands and a gold-rimmed friendship emblem plaque on
the front (geometry, no text). Two round boxwoods in navy pots on the lower step.
Footprint half .62 x .62, height ~2.0 (Blender Z up, front = +Y)."""
import os, sys, math
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _social_lib as S
import _lib_D as LD

CONFIG = {"floor": "C9C3B8", "seed": 35}


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.2, light=.36)
    P = S.paints()
    P["marble"] = LD.paint_marble("Marble", base="F2ECE1", vein="B8AD9C", vein2="DCD3C5")
    # ---- stepped plinth: low base step, the body with recessed panels, cornice and top slab
    dv4.cube("Step", (1.24, 1.24, .12), loc=(0, 0, .06), paint=P["navy"], bevel=.02, segs=2)
    dv4.cube("Step2", (1.0, 1.0, .08), loc=(0, 0, .16), paint=P["navy"], bevel=.018, segs=2)
    dv4.cube("Plinth", (.78, .78, .5), loc=(0, 0, .45), paint=P["navy_wood"], bevel=.02, segs=2)
    for sx, sy, w, d in ((0, 1, .6, .02), (0, -1, .6, .02), (1, 0, .02, .6), (-1, 0, .02, .6)):
        dv4.cube("Panel", (w, d, .36), loc=(sx * .395, sy * .395, .45), paint=P["navy"], bevel=.006, segs=1)
    dv4.cube("Cornice", (.9, .9, .07), loc=(0, 0, .735), paint=P["navy"], bevel=.02, segs=2)
    dv4.cube("Top", (.84, .84, .05), loc=(0, 0, .795), paint=P["navy"], bevel=.015, segs=2)
    # thin gold bands: on the base step, under the cornice and at the top edge
    for z, half in ((.118, .505), (.7, .395), (.772, .455)):
        for sy in (-1, 1):
            dv4.cube("GoldF", (2 * half + .01, .008, .012), loc=(0, sy * (half + .004), z), paint=P["gold"], bevel=.003, segs=1)
        for sx in (-1, 1):
            dv4.cube("GoldS", (.008, 2 * half + .01, .012), loc=(sx * (half + .004), 0, z), paint=P["gold"], bevel=.003, segs=1)
    # emblem plaque on the front panel
    S.emblem("Emb", 0, .405, .46, .16, P)
    # ---- the statue: marble base slab, the shopkeeper waving and the little friend holding his hand
    dv4.cylinder("StatueBase", .4, .06, loc=(0, 0, .82), seg=32, paint=P["marble"], bevel=.015, scale=(1.05, 1, 1))
    z0 = .88
    # the friend stands on the shopkeeper's right (viewer's left); their inner hands meet in front, between them
    hold = (-.11, .12, z0 + .29)
    S.person("Keeper", .15, -.03, z0, 1.0, P["marble"], wave="right", cap=True, apron=True, mustache=True, hold=hold)
    S.person("Friend", -.3, .04, z0, .6, P["marble"], wave="left", cap=False, apron=False, mustache=False, hold=hold)
    # ---- two round boxwoods in small navy pots on the lower step (front corners)
    for sx in (-1, 1):
        x, y = sx * .54, .54
        dv4.lathe("Pot", [(0, .12), (.07, .12), (.09, .14), (.1, .24), (.11, .26), (.095, .26), (0, .25)], seg=18, loc=(x, y, 0), paint=P["navy"])
        dv4.torus("PotGold", .105, .006, loc=(x, y, .255), seg=18, minor=5, paint=P["gold"])
        S.shrub("Ball", (x, y, .36), .11, P, squash=1.0, subdiv=2)
    return {"name": "InviteReward5", "tex": 1024, "budget": 15000, "floor": "C9C3B8"}
