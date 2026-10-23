"""park-bench: classic park bench, ornate cast-iron side frames with scrolls, warm wooden slats with bolts.
Footprint half .86 x .36, height <= 1.2 (Blender: X across, front = +Y)."""
import math
import dv4
from dv4 import RNG

CONFIG = {"floor": "C9C3B8", "seed": 3}
R = .024    # cast-iron bar radius (chunky so it reads from the game camera)
RS = .019   # scroll bar radius


def side(x, iron):
    """One cast-iron side frame in the plane x = const (YZ plane)."""
    # front leg rising into the seat rail, running back and up into the backrest post that leans back
    dv4.tube("Frame%s" % x, [(x, .30, 0), (x, .31, .14), (x, .29, .30), (x, .24, .42), (x, .0, .44), (x, -.22, .44),
                              (x, -.27, .56), (x, -.30, .76), (x, -.325, .98)], radius=R, res=8, paint=iron, resolution=5)
    dv4.sphere("Finial%s" % x, .034, loc=(x, -.326, 1.0), seg=10, rings=7, paint=iron)
    dv4.lathe("FinialRing%s" % x, [(.03, 0), (.036, .012), (.03, .024)], seg=10, loc=(x, -.322, .95), rot=(-10, 0, 0), paint=iron)
    # rear leg
    dv4.tube("Rear%s" % x, [(x, -.20, 0), (x, -.21, .22), (x, -.23, .44)], radius=R, res=8, paint=iron, resolution=3)
    # armrest: leaves the post, runs forward and curls down into a scroll above the front leg
    arm = [(x, -.28, .66), (x, -.12, .705), (x, .10, .705), (x, .23, .69)]
    arm += dv4.spiral((x, .245, .615), .075, .014, 1.0, 12, a0=math.radians(80), plane="YZ", ccw=False)[1:]
    dv4.tube("Arm%s" % x, arm, radius=R, res=8, paint=iron, resolution=3)
    # arm support: an S-scroll between the arm and the seat rail
    s1 = [(x, .09, .70)] + dv4.spiral((x, .10, .60), .085, .018, .9, 11, a0=math.radians(90), plane="YZ", ccw=False)[1:]
    dv4.tube("ArmScroll%s" % x, s1, radius=RS, res=6, paint=iron, resolution=3)
    s2 = [(x, .02, .44)] + dv4.spiral((x, .0, .53), .075, .016, .9, 11, a0=math.radians(-90), plane="YZ", ccw=False)[1:]
    dv4.tube("ArmScroll2%s" % x, s2, radius=RS, res=6, paint=iron, resolution=3)
    # ornament between the legs: two facing scrolls hanging from the seat rail
    s3 = [(x, .27, .42)] + dv4.spiral((x, .13, .22), .14, .03, 1.0, 12, a0=math.radians(60), plane="YZ", ccw=False)[1:]
    dv4.tube("LegScroll%s" % x, s3, radius=RS, res=6, paint=iron, resolution=3)
    s4 = [(x, -.21, .42)] + dv4.spiral((x, -.08, .22), .13, .03, 1.0, 12, a0=math.radians(120), plane="YZ", ccw=True)[1:]
    dv4.tube("LegScroll2%s" % x, s4, radius=RS, res=6, paint=iron, resolution=3)
    # feet pads
    for y in (.30, -.20):
        dv4.cube("Foot%s%s" % (x, y), (.075, .11, .026), loc=(x, y, .013), paint=iron, bevel=.007, segs=2)
    # cast rosette where the arm meets the post
    dv4.sphere("Rosette%s" % x, .034, loc=(x, -.28, .665), scale=(1.15, 1, 1), seg=10, rings=6, paint=iron)


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.25, light=.36)
    iron = dv4.paint_iron("Iron", base="1C2430", mid="35414E", edge="9AA6B0", rust="7A4423", rust_amt=.3)
    wood = dv4.paint_wood("Slat", base="B06A37", dark="4E2C14", light="E2A95C", scale=4.0, dist=2.0, along="X", edge="E6BE86", tint=.3, k_light=.26, k_ao=.55)
    bolt = dv4.paint_iron("Bolt", base="2A313A", mid="4A5560", edge="C0CAD2", rust_amt=.0)
    X = .76
    for sx in (-X, X):
        side(sx, iron)
    # stretchers between the side frames
    dv4.tube("StretchF", [(-X, .27, .41), (X, .27, .41)], radius=.015, res=6, paint=iron, kind="POLY", resolution=1)
    dv4.tube("StretchB", [(-X, -.19, .41), (X, -.19, .41)], radius=.015, res=6, paint=iron, kind="POLY", resolution=1)
    dv4.tube("StretchTop", [(-X, -.315, .82), (X, -.315, .82)], radius=.014, res=6, paint=iron, kind="POLY", resolution=1)
    # seat slats (4) and back slats (3), leaning back 12 degrees
    W = 1.64
    seat_y = (.225, .117, .009, -.099)
    for i, y in enumerate(seat_y):
        dv4.cube("Seat%d" % i, (W, .097, .038), loc=(0, y, .468), paint=wood, bevel=.009, segs=2)
    back = ((-.238, .55), (-.264, .67), (-.29, .79))
    for i, (y, z) in enumerate(back):
        dv4.cube("Back%d" % i, (W, .038, .10), loc=(0, y, z), rot=(12, 0, 0), paint=wood, bevel=.009, segs=2)
    # bolts: domed heads on the slat ends over the frames
    for sx in (-X, X):
        for y in seat_y:
            dv4.sphere("BoltS", .013, loc=(sx, y, .487), scale=(1, 1, .5), seg=8, rings=4, paint=bolt)
        for y, z in back:
            dv4.sphere("BoltB", .013, loc=(sx, y + .019 * math.cos(math.radians(12)), z + .019 * math.sin(math.radians(12))),
                       scale=(1, .5, 1), seg=8, rings=4, paint=bolt, rot=(-78, 0, 0))
    return {"name": "ParkBench", "tex": 1024, "budget": 10000, "floor": "C9C3B8"}
