"""invite-reward-3 (3 invited friends reached the Spaeti): a navy kiosk-style street lamp. Fluted navy base and post
with thin gold bands; on top an octagonal lantern with warm glowing panes under a scalloped kiosk dome and a gold
finial; a crossbar with two curled scroll arms, each carrying a hanging flower basket on chains; a navy swallowtail
banner on a gold bracket with the friendship emblem (geometry, no text) that sways in the wind.
Footprint half .62 x .3, height ~3.1 (Blender Z up, front = +Y)."""
import os, sys, math
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _social_lib as S
import _lib_E as E

CONFIG = {"floor": "C9C3B8", "seed": 33}
GLOW = "E_FFD27A"


def basket(x, z, P, k):
    """Hanging flower basket: three chains to a hook, a navy wire bowl with a gold rim, a wicker liner, flowers + ivy."""
    hook = (x, 0, z)
    rim_z = z - .32
    for i in range(3):
        a = math.radians(90 + i * 120)
        dv4.tube("Chain%d_%d" % (k, i), [hook, (x + math.cos(a) * .17, math.sin(a) * .17, rim_z)], radius=.005, res=5, paint=P["gold"],
                 kind="POLY", resolution=1)
    bowl = [(0, rim_z - .2), (.08, rim_z - .19), (.14, rim_z - .14), (.18, rim_z - .07), (.2, rim_z), (0, rim_z)]
    dv4.lathe("Bowl%d" % k, bowl, seg=16, loc=(x, 0, 0), paint=P["wicker"])
    dv4.torus("BowlRim%d" % k, .2, .012, loc=(x, 0, rim_z), seg=16, minor=5, paint=P["gold"])
    for j in range(4):
        a = math.radians(45 + j * 90)
        dv4.tube("BowlRib%d_%d" % (k, j), [(x + math.cos(a) * .2, math.sin(a) * .2, rim_z), (x + math.cos(a) * .15, math.sin(a) * .15, rim_z - .12),
                                            (x + math.cos(a) * .04, math.sin(a) * .04, rim_z - .2)], radius=.007, res=4, paint=P["navy"], resolution=2)
    soil = dv4.patch("BasketSoil%d" % k, .36, .36, 6, 6, loc=(x, 0, rim_z - .02), paint=P["soil"], disk=True)
    S.shrub("BasketMound%d" % k, (x, 0, rim_z + .03), .17, P, squash=.55, subdiv=2)
    S.flower_ring("BasketFl%d" % k, x, 0, rim_z + .02, .17, .17, 5, P, cols=("pink", "purple", "white"), size=.06, seed=k)
    for i in range(5):
        a = math.radians(30 + i * 72)
        p0 = (x + math.cos(a) * .19, math.sin(a) * .19, rim_z)
        p1 = (x + math.cos(a) * .24, math.sin(a) * .24, rim_z - .12)
        p2 = (x + math.cos(a) * .22, math.sin(a) * .22, rim_z - .3 - .06 * (i % 2))
        dv4.tube("Ivy%d_%d" % (k, i), [p0, p1, p2], radius=.004, res=3, paint=P["stem"], resolution=3)
        for j in range(2 - i % 2):
            t = (j + 1) / 3
            q = (p0[0] + (p2[0] - p0[0]) * t, p0[1] + (p2[1] - p0[1]) * t + math.sin(a) * .03, p0[2] + (p2[2] - p0[2]) * t)
            dv4.leaf("IvyL%d_%d_%d" % (k, i, j), .07, .055, loc=q, rot=(-70, 0, math.degrees(a) - 90), paint=P["leaf"], shape="heart",
                     bend=.2, cup=.1, thickness=.003, nl=3, nw=2)


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.2, light=.38)
    P = S.paints()
    P["wicker"] = E.paint_wicker("Wicker")
    P["banner"] = E.paint_fabric("Banner", S.NAVY, "0E1730", "3D5288")
    P["glass"] = dv4.paint_flat("Pane", "FFE3A3", dark="E9A64A", variation=.25, scale=6.0)
    # ---- fluted base, plinth ring, tapered fluted post with gold bands
    base = [(0, 0), (.26, 0), (.27, .02), (.27, .07), (.23, .1), (.18, .14), (.14, .24), (.115, .38), (.095, .5), (.09, .56), (0, .56)]
    dv4.lathe("Base", base, seg=24, paint=P["navy"], scallop=(12, .04))
    dv4.torus("BaseBand", .272, .01, loc=(0, 0, .045), seg=28, minor=4, paint=P["gold"])
    dv4.torus("BaseBand2", .1, .014, loc=(0, 0, .5), seg=16, minor=4, paint=P["gold"])
    post = [(0, .55), (.07, .55), (.068, 1.2), (.062, 2.2), (.058, 2.62), (0, 2.62)]
    dv4.lathe("Post", post, seg=24, paint=P["navy"], scallop=(12, .06), cap=True)
    for z, r in ((1.12, .078), (1.95, .072), (2.42, .07)):
        dv4.torus("Band", r, .011, loc=(0, 0, z), seg=16, minor=4, paint=P["gold"])
    # ---- crossbar with two scroll arms and the baskets
    dv4.cube("CrossHub", (.16, .16, .1), loc=(0, 0, 2.18), paint=P["navy"], bevel=.03, segs=2)
    for s in (-1, 1):
        arm = [(s * .06, 0, 2.2), (s * .3, 0, 2.26), (s * .5, 0, 2.24), (s * .58, 0, 2.18)]
        dv4.tube("Arm%d" % s, arm, radius=.022, res=6, paint=P["navy"], resolution=4)
        sc = dv4.spiral((s * .27, 0, 2.08), .1, .02, .9, 12, a0=math.radians(90), plane="XZ", ccw=(s < 0))
        dv4.tube("Scroll%d" % s, [(s * .07, 0, 2.15)] + sc, radius=.014, res=5, paint=P["navy"], resolution=3)
        dv4.sphere("ArmKnob%d" % s, .03, loc=(s * .6, 0, 2.18), seg=10, rings=6, paint=P["gold"])
        dv4.torus("Hook%d" % s, .025, .006, loc=(s * .58, 0, 2.13), rot=(90, 0, 0), seg=12, minor=4, paint=P["gold"])
        basket(s * .58, 2.1, P, int(s > 0))
    # ---- kiosk lantern: collar, octagonal frame with glowing panes, scalloped dome, gold finial
    dv4.lathe("Collar", [(0, 2.6), (.07, 2.6), (.11, 2.66), (.15, 2.68), (.15, 2.71), (0, 2.71)], seg=24, paint=P["navy"])
    dv4.torus("CollarGold", .15, .008, loc=(0, 0, 2.7), seg=16, minor=4, paint=P["gold"])
    lz0, lz1, lr = 2.71, 2.98, .15
    dv4.lathe("Panes", [(0, lz0), (lr * .92, lz0), (lr * 1.02, lz1), (0, lz1)], seg=8, paint=P["glass"], rot=(0, 0, 22.5))
    for i in range(8):
        a = math.radians(i * 45)
        dv4.tube("Mullion%d" % i, [(math.cos(a) * lr * .95, math.sin(a) * lr * .95, lz0), (math.cos(a) * lr * 1.05, math.sin(a) * lr * 1.05, lz1)],
                 radius=.009, res=5, paint=P["navy"], kind="POLY", resolution=1)
    dv4.sphere("Bulb", .05, loc=(0, 0, 2.84), scale=(1, 1, 1.3), seg=10, rings=6, paint=None, mat_override=GLOW)
    dome = [(0, lz1), (.2, lz1), (.21, lz1 + .02), (.19, lz1 + .05), (.15, lz1 + .1), (.1, lz1 + .15), (.05, lz1 + .19), (0, lz1 + .2)]
    dv4.lathe("Dome", dome, seg=24, paint=P["navy"], scallop=(8, .06))
    dv4.torus("DomeGold", .205, .009, loc=(0, 0, lz1 + .012), seg=24, minor=4, paint=P["gold"])
    dv4.lathe("Finial", [(0, lz1 + .19), (.03, lz1 + .19), (.035, lz1 + .22), (.022, lz1 + .26), (.03, lz1 + .29), (.012, lz1 + .33),
                         (0, lz1 + .35)], seg=12, paint=P["gold"])
    # ---- banner on a gold bracket on the front of the post (sways)
    bz = 1.92
    dv4.tube("BannerArm", [(0, .06, bz), (0, .3, bz), (0, .36, bz - .02)], radius=.012, res=6, paint=P["gold"], resolution=2)
    dv4.tube("BannerBrace", [(0, .06, bz - .2), (0, .2, bz - .05)], radius=.008, res=5, paint=P["gold"], kind="POLY", resolution=1)
    sway = "Anim Sway"
    dv4.pivot(sway, (.0, .3, bz))
    dv4.tube("BannerRod", [(-.22, .3, bz - .03), (.22, .3, bz - .03)], radius=.012, res=6, paint=P["gold"], kind="POLY", resolution=1, out=sway)
    for s in (-1, 1):
        dv4.sphere("RodEnd%d" % s, .02, loc=(s * .23, .3, bz - .03), seg=8, rings=5, paint=P["gold"], out=sway)
    W, Hb, notch = .4, .62, .14
    pts = [(-W / 2, 0), (W / 2, 0), (W / 2, -Hb), (0, -Hb + notch), (-W / 2, -Hb)]
    ban = E.flat_shape("Banner", pts, depth=.014, loc=(0, .3, bz - .05), rot=(90, 0, 0), paint=P["banner"], out=sway)
    dv4.mod_bevel(ban, .004, 1)
    # gold piping along the edges and the emblem on the front face
    edge = [(-W / 2 + .02, .309, bz - .07), (-W / 2 + .02, .309, bz - .05 - Hb + .04), (0, .309, bz - .05 - Hb + notch + .02),
            (W / 2 - .02, .309, bz - .05 - Hb + .04), (W / 2 - .02, .309, bz - .07)]
    dv4.tube("BannerPiping", edge, radius=.005, res=4, paint=P["gold"], kind="POLY", resolution=1, out=sway)
    S.emblem("Emb", 0, .31, bz - .3, .13, P)
    for ob in dv4.PARTS:
        if ob.name.startswith("Emb"):
            ob["dv4_out"] = sway
    return {"name": "InviteReward3", "tex": 1024, "budget": 10000, "floor": "C9C3B8"}
