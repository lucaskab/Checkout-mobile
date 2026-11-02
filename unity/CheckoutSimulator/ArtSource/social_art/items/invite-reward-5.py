"""invite-reward-5 (5 invited friends reached the Spaeti): the friends statue. A painted, full-colour statue of a chunky
shopkeeper (teal cap and apron over a red shirt, navy trousers, moustache) waving and holding hands with a little friend
(yellow shirt, denim trousers, red sneakers), in the style and palette of the game's own characters, standing on a
round marble pedestal with a thin gold rim, on a stepped navy plinth with thin gold bands and a gold-rimmed friendship
emblem plaque on the front (geometry, no text). Two round boxwoods in navy pots on the lower step.
Footprint half .62 x .62, height ~2.0 (Blender Z up, front = +Y)."""
import os, sys, math
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _social_lib as S
import _lib_D as LD
import _lib_E as E

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
    dv4.torus("StatueRim", .401, .008, loc=(0, 0, .852), seg=40, minor=5, paint=P["gold"], scale=(1.05, 1, 1))
    z0 = .88
    # the friend stands on the shopkeeper's right (viewer's left); their inner hands meet in front, between them
    hold = (-.11, .12, z0 + .29)
    face = {
        "eyes": E.paint_painted("Eyes", "2A1E1A", light="5A4A40", dark="0E0A08", variation=.05, sheen=.4),
        "glint": dv4.paint_flat("Glint", "FFFFFF", "EDEDED", variation=.02),
        "mouth": E.paint_painted("Mouth", "8E3A2C", light="B85A48", dark="5A2018", variation=.08),
        "cheek": E.paint_painted("Blush", "EE9A86", light="FFC2B0", dark="D97A66", variation=.06),
    }
    teal = E.paint_fabric("ApronTeal", "188F86", "0E5F59", "54C1AB")
    keeper = dict(face,
                  skin=E.paint_painted("Skin", "F0BE96", light="FFE0C8", dark="C98E68", variation=.08, sheen=.15),
                  shirt=E.paint_fabric("ShirtRed", "D9473A", "9E2C22", "F07A63"),
                  apron=teal, cap=teal,
                  brim=E.paint_painted("BrimTeal", "12726B", light="3FA89A", dark="0A4A45", variation=.1, sheen=.2),
                  pocket=P["cream"],
                  belt=E.paint_painted("Belt", "6B4128", light="9A6A44", dark="3A2214", variation=.12, sheen=.25),
                  pants=E.paint_fabric("PantsNavy", "2E3F6B", "1A2546", "4F659E"),
                  shoes=E.paint_painted("Shoes", "4A2E1E", light="8A5A3A", dark="23150D", variation=.1, sheen=.3),
                  hair=E.paint_painted("HairKeeper", "5A3A26", light="8A5E3E", dark="2E1C12", variation=.15))
    friend = dict(face,
                  skin=E.paint_painted("Skin2", "DDA67C", light="F5CDA8", dark="B07650", variation=.08, sheen=.15),
                  shirt=E.paint_fabric("ShirtYellow", "F2C23F", "C98F1C", "FFE07A"),
                  pants=E.paint_fabric("Denim", "4A6FA5", "2C4A78", "7FA0CF"),
                  shoes=E.paint_painted("Sneakers", "D9473A", light="F07A63", dark="8E2A20", variation=.1, sheen=.3),
                  hair=E.paint_painted("Hair", "6B4128", light="9A6A44", dark="3A2214", variation=.18))
    S.person("Keeper", .15, -.03, z0, 1.0, keeper, wave="right", cap=True, apron=True, mustache=True, hold=hold, hair_cap=True)
    S.person("Friend", -.3, .04, z0, .6, friend, wave="left", cap=False, apron=False, mustache=False, hold=hold, hair_cap=True)
    # ---- two round boxwoods in small navy pots on the lower step (front corners)
    for sx in (-1, 1):
        x, y = sx * .54, .54
        dv4.lathe("Pot", [(0, .12), (.07, .12), (.09, .14), (.1, .24), (.11, .26), (.095, .26), (0, .25)], seg=18, loc=(x, y, 0), paint=P["navy"])
        dv4.torus("PotGold", .105, .006, loc=(x, y, .255), seg=18, minor=5, paint=P["gold"])
        S.shrub("Ball", (x, y, .36), .11, P, squash=1.0, subdiv=2)
    return {"name": "InviteReward5", "tex": 1024, "budget": 15000, "floor": "C9C3B8"}
