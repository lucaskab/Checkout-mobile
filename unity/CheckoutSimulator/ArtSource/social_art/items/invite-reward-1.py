"""invite-reward-1 (1 invited friend reached the Spaeti): a small navy-and-gold bench planter. Two navy painted planter
boxes (raised panel frames, thin gold rim and base lines) hold round boxwood shrubs ringed with flowers; between them a
warm-wood slatted seat and a low backrest on navy posts, crowned by the friendship emblem (two shopping bags leaning
together under a heart) on a cream medallion with a gold rim. No text anywhere.
Footprint half .92 x .32, height ~1.15 (Blender Z up, front = +Y)."""
import os, sys, math
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _social_lib as S

CONFIG = {"floor": "C9C3B8", "seed": 31}


def planter(x, P):
    W, Dp, H = .46, .56, .56
    # body with a plinth and a cap rail
    dv4.cube("PlBody", (W - .04, Dp - .04, H - .1), loc=(x, 0, .06 + (H - .1) / 2), paint=P["navy"], bevel=.015, segs=2)
    dv4.cube("PlPlinth", (W, Dp, .07), loc=(x, 0, .035), paint=P["navy"], bevel=.012, segs=2)
    dv4.cube("PlCap", (W + .02, Dp + .02, .05), loc=(x, 0, H - .015), paint=P["navy"], bevel=.014, segs=2)
    # raised panel frames on the front/back and sides, thin gold lines at the rim and above the plinth
    for sy in (-1, 1):
        dv4.cube("PlPanel", (W - .14, .02, H - .24), loc=(x, sy * (Dp / 2 - .015), .06 + (H - .1) / 2), paint=P["navy_wood"], bevel=.006, segs=1)
    for sx in (-1, 1):
        dv4.cube("PlPanelS", (.02, Dp - .14, H - .24), loc=(x + sx * (W / 2 - .015), 0, .06 + (H - .1) / 2), paint=P["navy_wood"], bevel=.006,
                 segs=1)
    for z in (H - .045, .078):
        for sy in (-1, 1):
            dv4.cube("PlGold", (W + .005, .008, .012), loc=(x, sy * (Dp / 2 + .004), z), paint=P["gold"], bevel=.003, segs=1)
        for sx in (-1, 1):
            dv4.cube("PlGoldS", (.008, Dp + .005, .012), loc=(x + sx * (W / 2 + .004), 0, z), paint=P["gold"], bevel=.003, segs=1)
    # brass ball feet
    for sx in (-1, 1):
        for sy in (-1, 1):
            dv4.sphere("PlFoot", .028, loc=(x + sx * (W / 2 - .05), sy * (Dp / 2 - .05), .0), scale=(1, 1, .6), seg=10, rings=6, paint=P["gold"])
    # soil, a round boxwood and a ring of flowers
    soil = dv4.patch("PlSoil", W - .06, Dp - .06, 8, 8, loc=(x, 0, H - .03), paint=P["soil"])
    dv4.mod_displace(soil, strength=.015, size=.08, mid=.45)
    S.shrub("PlShrub", (x, -.01, H + .17), .2, P, squash=.95)
    S.flower_ring("PlFl%d" % (1 if x > 0 else 0), x, 0, H - .02, .19, .22, 6, P, size=.065, seed=int(x > 0))


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.22, light=.36)
    P = S.paints()
    for x in (-.69, .69):
        planter(x, P)
    # seat: four warm wood slats on navy rails between the planters
    L = .92
    for sy in (-1, 1):
        dv4.cube("SeatRail", (L + .04, .05, .07), loc=(0, sy * .2, .38), paint=P["navy"], bevel=.012, segs=2)
    for i in range(4):
        y = -.18 + i * .12
        dv4.cube("Slat", (L + .02, .1, .04), loc=(0, y, .44), paint=P["wood"], bevel=.012, segs=2)
    # low backrest: two slats on navy posts at the back, gold cap line, the emblem on top
    for sx in (-1, 1):
        dv4.cube("BackPost", (.05, .05, .5), loc=(sx * .43, -.25, .66), rot=(-6, 0, 0), paint=P["navy"], bevel=.012, segs=2)
        dv4.sphere("PostKnob", .03, loc=(sx * .43, -.276, .92), seg=10, rings=6, paint=P["gold"])
    for i, z in enumerate((.6, .74)):
        dv4.cube("BackSlat", (L - .02, .04, .1), loc=(0, -.245 - (z - .41) * .105, z), rot=(-6, 0, 0), paint=P["wood"], bevel=.012, segs=2)
    dv4.cube("BackTop", (L, .05, .045), loc=(0, -.262, .835), rot=(-6, 0, 0), paint=P["navy"], bevel=.012, segs=2)
    dv4.cube("BackGold", (L - .04, .008, .01), loc=(0, -.234, .835), rot=(-6, 0, 0), paint=P["gold"], bevel=.003, segs=1)
    # crest: the friendship emblem standing on the top rail
    dv4.cube("CrestFoot", (.18, .05, .06), loc=(0, -.262, .88), paint=P["navy"], bevel=.012, segs=2)
    S.emblem("Emb", 0, -.29, 1.08, .19, P)
    return {"name": "InviteReward1", "tex": 1024, "budget": 9000, "floor": "C9C3B8"}
