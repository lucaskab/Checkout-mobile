"""swing-set: wooden A-frame playground swing with two rope-hung seats (each on its own "Anim Sway", pivot at the top beam).
Footprint half 1.20 x .60, height <= 2.2 (Blender: X across, front = +Y)."""
import math, os, sys
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_J as J

CONFIG = {"floor": "C9C3B8", "seed": 21}

X = 1.00          # x of the A-frames
Y0 = .47          # leg spread at the ground
ZT = 2.00         # top beam centre height
LEG = .095        # leg timber size


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.25, light=.36)
    wood = dv4.paint_wood("Timber", base="C28A4C", dark="6E4322", light="E8BE7C", scale=2.6, dist=3.0, along="Z", tint=.25, edge="F0CF95")
    beam = dv4.paint_wood("Beam", base="B97C42", dark="63391C", light="E2B373", scale=2.6, dist=3.0, along="X", tint=.15, edge="EFC78C")
    seat = J.paint_painted_wood("Seat", base="D74A3C", dark="9E2E24", light="F07A6B", along="X", wear="E9B38B", wear_amt=.35)
    seat2 = J.paint_painted_wood("Seat2", base="1F9A8E", dark="146A61", light="5CC7BA", along="X", wear="CDE9E0", wear_amt=.35)
    iron = dv4.paint_iron("Iron", base="1E2630", mid="3A4653", edge="9AA6B0", rust_amt=.25)
    rope = J.paint_rope("Rope", axis="Z")

    tilt = math.degrees(math.atan2(Y0, ZT))
    L = math.hypot(Y0, ZT) + .08
    # A-frames: two splayed legs each side, a cross brace, a foot block and an iron collar at the apex
    for sx in (-X, X):
        for sy in (-1, 1):
            dv4.cube("Leg%s%s" % (sx, sy), (LEG, LEG, L), loc=(sx, sy * Y0 * .5, ZT * .5 - .02), rot=(sy * tilt, 0, 0), paint=wood, bevel=.012, segs=2)
            dv4.cube("Foot%s%s" % (sx, sy), (LEG + .06, LEG + .06, .05), loc=(sx, sy * (Y0 + .02), .025), paint=iron, bevel=.012, segs=2)
        zb = .78
        yb = Y0 * (1 - zb / ZT)
        dv4.cube("Brace%s" % sx, (LEG * .8, yb * 2 + .02, LEG * .8), loc=(sx, 0, zb), paint=wood, bevel=.01, segs=2)
        for sy in (-1, 1):
            dv4.sphere("BraceBolt%s%s" % (sx, sy), .014, loc=(sx + LEG * .4, sy * yb * .95, zb), scale=(.5, 1, 1), seg=8, rings=4, paint=iron)
        # iron apex collar wrapping the beam and the two leg tops
        dv4.cube("Collar%s" % sx, (.07, .30, .19), loc=(sx, 0, ZT - .02), paint=iron, bevel=.014, segs=2)
        for sy in (-1, 1):
            dv4.sphere("CollarBolt%s%s" % (sx, sy), .017, loc=(sx + .036, sy * .09, ZT - .02), scale=(.5, 1, 1), seg=8, rings=4, paint=iron)
    # top beam with rounded ends and a cap strip
    dv4.cube("Beam", (2 * X + .30, .115, .115), loc=(0, 0, ZT), paint=beam, bevel=.02, segs=3)
    # swings: rope eyes under the beam, ropes, seat with iron edge brackets
    for i, (sx, sp) in enumerate(((-.55, seat), (.55, seat2))):
        out = "Anim Sway" + (".001" if i else "")
        dv4.pivot(out, (sx, 0, ZT))
        for dx in (-.21, .21):
            dv4.torus("Eye%d%s" % (i, dx), .022, .007, loc=(sx + dx, 0, ZT - .07), rot=(0, 90, 0), seg=12, minor=5, paint=iron)
            dv4.tube("Rope%d%s" % (i, dx), [(sx + dx, 0, ZT - .09), (sx + dx, 0, .50)], radius=.015, res=7, paint=rope, kind="POLY", resolution=1, out=out)
            dv4.sphere("Knot%d%s" % (i, dx), .024, loc=(sx + dx, 0, .512), scale=(1, 1, .7), seg=8, rings=5, paint=rope, out=out)
        dv4.cube("Seat%d" % i, (.50, .20, .035), loc=(sx, 0, .55), paint=sp, bevel=.012, segs=2, out=out)
        for dx in (-.22, .22):
            dv4.cube("Bracket%d%s" % (i, dx), (.035, .22, .05), loc=(sx + dx, 0, .553), paint=iron, bevel=.008, segs=2, out=out)
    # a little bird perched on the beam (bobs)
    bird = J.paint_gloss("Bird", "EC862E", dark="B55A14", light="FFC27A", variation=.1)
    bird_d = J.paint_gloss("BirdDark", "1D2B4F", dark="0E1730", light="4A5C8C", variation=.1)
    beak = J.paint_gloss("Beak", "E0B040", dark="A8781F", light="FFE38A", variation=.05)
    bob = "Anim Bob"; bx, bz = -X + .22, ZT + .058
    dv4.pivot(bob, (bx, 0, bz))
    dv4.sphere("BirdBody", .056, loc=(bx, 0, bz + .05), scale=(1.3, 1, .9), seg=12, rings=8, paint=bird, out=bob, rot=(0, 0, 10))
    dv4.sphere("BirdHead", .04, loc=(bx + .056, .01, bz + .106), seg=12, rings=8, paint=bird, out=bob)
    dv4.lathe("Beak", [(0, 0), (.014, 0), (0, .037)], seg=8, loc=(bx + .091, .015, bz + .102), rot=(0, 80, 10), paint=beak, out=bob)
    dv4.sphere("BirdWing", .037, loc=(bx - .006, -.037, bz + .056), scale=(1.5, .45, .8), seg=10, rings=6, paint=bird_d, out=bob, rot=(0, 0, 10))
    dv4.sphere("BirdWing2", .037, loc=(bx - .006, .037, bz + .056), scale=(1.5, .45, .8), seg=10, rings=6, paint=bird_d, out=bob, rot=(0, 0, 10))
    dv4.cube("BirdTail", (.075, .044, .012), loc=(bx - .087, -.012, bz + .062), rot=(0, -25, 10), paint=bird_d, bevel=.004, segs=1, out=bob)
    for sy in (-.012, .012):
        dv4.sphere("BirdEye%s" % sy, .0075, loc=(bx + .081, sy * 2.75, bz + .119), seg=6, rings=4, paint=bird_d, out=bob)
    return {"name": "SwingSet", "tex": 1024, "budget": 6000, "floor": "C9C3B8", "sharp_angle": 50}
