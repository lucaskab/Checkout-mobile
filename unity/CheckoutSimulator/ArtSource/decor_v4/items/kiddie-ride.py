"""kiddie-ride (diamond): coin-operated cartoon car on a chrome coil spring over a navy & gold platform with gold stars; red
car with a gold star on the hood, chrome bumpers and grille, glowing headlights, windshield, cream seat and steering wheel.
The car (with its wheels) rocks on "Anim Bob"; the coin box on its post has a blinking LED ("Anim Blink") and a pennant ("Anim Sway").
Footprint half .46 x .62, height <= 1.5 (Blender: car front = +Y, Z up)."""
import math
import dv4
from dv4 import RNG
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib_F as F

CONFIG = {"floor": "C9C3B8", "seed": 24}
NAVY, GOLD, CREAM, RED = "1D2B4F", "E0B040", "F4EFE4", "D74A3C"


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.2, light=.36)
    stars = [(-.30, .42), (.30, .42), (-.33, -.1), (.33, -.1), (-.22, -.47), (.22, -.47), (0, .55)]
    navy = F.paint_navy_stars("Navy", stars=stars, star_r=.045)
    gold = F.paint_brass("Gold")
    chrome = F.paint_chrome("Chrome")
    red = F.paint_enamel_star("Red", RED, "8F2A20", "FF9A8C", star_at=(0, .30, .74), star_r=.09)
    cream = F.paint_enamel("Cream", CREAM, dark="C9BFA8", light="FFFFFF", variation=.1, scratch=.03)
    rubber = F.paint_rubber("Rubber")
    dark = F.paint_enamel("Dark", "2F3A40", dark="161C20", light="7A8A94", variation=.12)
    teal = F.paint_enamel("Teal", "1F9A8E", dark="0E5A53", light="8ADFD3", variation=.14)
    plate = F.paint_checker("Plate", "C9D2D6", "AEB8BD", size=.06, axis="XY", k_light=.3)
    taillight = F.paint_enamel("Tail", "FF5A4A", dark="C0263B", light="FFC0B0", variation=.1, scratch=0.0, hl=.4, k_ao=.2, k_light=.1)
    led = F.paint_enamel("Led", "4CFF8A", dark="1FB85A", light="DFFFEA", variation=.05, scratch=0.0, hl=.4, k_ao=.1, k_light=.05)

    # ---------------------------------------------------------------- platform
    dv4.cube("Base", (.88, 1.20, .12), loc=(0, 0, .06), paint=navy, bevel=.03, segs=2)
    for sy in (-.595, .595):
        dv4.cube("TrimY%s" % sy, (.90, .035, .03), loc=(0, sy, .115), paint=gold, bevel=.008, segs=1)
    for sx in (-.435, .435):
        dv4.cube("TrimX%s" % sx, (.035, 1.22, .03), loc=(sx, 0, .115), paint=gold, bevel=.008, segs=1)
    dv4.cube("Step", (.70, .20, .02), loc=(0, .49, .135), paint=plate, bevel=.006, segs=2)
    for sx in (-.41, .41):
        for sy in (-.56, .56):
            dv4.cylinder("Bumper%s%s" % (sx, sy), .035, .10, loc=(sx, sy, .0), seg=8, paint=rubber, bevel=.01)
    # ---------------------------------------------------------------- coil spring (chrome) + top plate
    dv4.lathe("SpringFoot", [(0, 0), (.14, 0), (.15, .01), (.15, .025), (.12, .035), (0, .035)], seg=16, loc=(0, 0, .12), paint=chrome)
    pts = F.helix((0, 0), .10, .17, .50, 4.0, n_per_turn=12)
    dv4.tube("Spring", pts, radius=.018, res=6, paint=chrome, kind="NURBS", resolution=1)
    dv4.sphere("SpringEnd0", .016, loc=pts[0], seg=8, rings=5, paint=chrome)
    dv4.sphere("SpringEnd1", .016, loc=pts[-1], seg=8, rings=5, paint=chrome)

    # ---------------------------------------------------------------- the car on Anim Bob
    bob = "Anim Bob"; dv4.pivot(bob, (0, 0, .52))
    dv4.lathe("SpringTop", [(0, 0), (.12, 0), (.13, .01), (.13, .02), (.10, .03), (0, .03)], seg=16, loc=(0, 0, .50), paint=chrome, out=bob)
    BZ = .70
    body = dv4.cube("CarBody", (.60, 1.0, .26), loc=(0, .02, BZ), paint=red, bevel=.07, segs=3, out=bob)
    dv4.cube("Hood", (.50, .36, .06), loc=(0, .30, BZ + .15), paint=red, bevel=.028, segs=2, out=bob)
    dv4.cube("Trunk", (.50, .20, .05), loc=(0, -.40, BZ + .14), paint=red, bevel=.024, segs=2, out=bob)
    # wheel arches / running boards and the four wheels with chrome hubcaps
    for sx in (-1, 1):
        dv4.cube("Board%d" % sx, (.06, .62, .04), loc=(sx * .32, -.02, BZ - .10), paint=dark, bevel=.012, segs=2, out=bob)
        for sy in (.30, -.30):
            wx = sx * .30
            dv4.cylinder("Tyre%d%s" % (sx, sy), .12, .09, loc=(wx - .045, sy, .60), rot=(0, 90, 0), seg=14, paint=rubber, bevel=.025, out=bob)
            dv4.lathe("Hub%d%s" % (sx, sy), [(0, 0), (.07, 0), (.075, .008), (.065, .02), (.03, .028), (0, .03)], seg=12,
                      loc=(wx + sx * .046, sy, .60), rot=(0, sx * 90, 0), paint=chrome, out=bob)
    # cockpit: dark well, cream seat, dashboard, steering wheel, windshield
    dv4.cube("Cockpit", (.42, .44, .05), loc=(0, -.13, BZ + .14), paint=dark, bevel=.02, segs=2, out=bob)
    dv4.cube("SeatCushion", (.36, .22, .07), loc=(0, -.20, BZ + .17), paint=cream, bevel=.025, segs=2, out=bob)
    dv4.cube("SeatBack", (.36, .07, .22), loc=(0, -.335, BZ + .24), rot=(8, 0, 0), paint=cream, bevel=.025, segs=2, out=bob)
    dv4.cube("Dash", (.42, .08, .08), loc=(0, .08, BZ + .18), paint=dark, bevel=.02, segs=2, out=bob)
    dv4.tube("SteerCol", [(0, .06, BZ + .18), (0, -.02, BZ + .30)], radius=.012, res=8, paint=chrome, kind="POLY", resolution=1, out=bob)
    dv4.torus("Steer", .075, .014, loc=(0, -.02, BZ + .30), rot=(-35, 0, 0), seg=14, minor=6, paint=cream, out=bob)
    dv4.sphere("SteerHub", .022, loc=(0, -.02, BZ + .30), seg=8, rings=5, paint=chrome, out=bob)
    dv4.tube("ShieldFrame", [(-.21, .11, BZ + .20), (-.21, .07, BZ + .40), (0, .06, BZ + .42), (.21, .07, BZ + .40), (.21, .11, BZ + .20)],
             radius=.011, res=6, paint=chrome, resolution=3, out=bob)
    dv4.cube("Shield", (.40, .006, .20), loc=(0, .09, BZ + .30), rot=(-12, 0, 0), paint=None, mat_override="G_Glass", bevel=0, out=bob)
    # face: chrome grille + bumpers, headlights (glow), tail lights, little exhaust pipe
    dv4.cube("Grille", (.26, .03, .09), loc=(0, .515, BZ - .02), paint=dark, bevel=.012, segs=2, out=bob)
    for i in range(4):
        dv4.cube("GrilleBar%d" % i, (.24, .012, .008), loc=(0, .53, BZ - .055 + i * .024), paint=chrome, bevel=0, out=bob)
    dv4.tube("BumperF", [(-.28, .48, BZ - .10), (-.22, .54, BZ - .10), (.22, .54, BZ - .10), (.28, .48, BZ - .10)], radius=.018, res=6, paint=chrome, resolution=2, out=bob)
    dv4.tube("BumperB", [(-.28, -.44, BZ - .10), (-.22, -.50, BZ - .10), (.22, -.50, BZ - .10), (.28, -.44, BZ - .10)], radius=.018, res=6, paint=chrome, resolution=2, out=bob)
    for sx in (-.19, .19):
        dv4.lathe("LampRing%s" % sx, [(0, 0), (.06, 0), (.065, .01), (.062, .03), (.055, .035), (0, .035)], seg=10, loc=(sx, .50, BZ + .04), rot=(-90, 0, 0), paint=chrome, out=bob)
        dv4.sphere("Lamp%s" % sx, .048, loc=(sx, .515, BZ + .04), seg=10, rings=6, paint=None, mat_override="E_FFF1C4", out=bob, scale=(1, .6, 1))
        dv4.sphere("Tail%s" % sx, .025, loc=(sx, -.49, BZ + .05), seg=8, rings=5, paint=taillight, out=bob, scale=(1, .5, 1))
    dv4.tube("Exhaust", [(.22, -.45, BZ - .15), (.22, -.56, BZ - .15)], radius=.014, res=8, paint=chrome, kind="POLY", resolution=1, out=bob)
    dv4.sphere("ExhaustCap", .014, loc=(.22, -.56, BZ - .15), seg=8, rings=5, paint=dark, out=bob)
    # tiny antenna + ball on the trunk
    dv4.tube("Antenna", [(-.18, -.42, BZ + .16), (-.18, -.44, BZ + .40)], radius=.004, res=5, paint=chrome, kind="POLY", resolution=1, out=bob)
    dv4.sphere("AntennaBall", .018, loc=(-.18, -.44, BZ + .40), seg=10, rings=6, paint=teal, out=bob)

    # ---------------------------------------------------------------- coin box on a chrome post (back-right corner)
    px, py = .36, -.50
    dv4.tube("Post", [(px, py, .12), (px, py, .78)], radius=.02, res=10, paint=chrome, kind="POLY", resolution=1)
    dv4.lathe("PostFoot", [(0, 0), (.05, 0), (.055, .01), (.04, .03), (.025, .04), (0, .04)], seg=14, loc=(px, py, .125), paint=chrome)
    dv4.cube("CoinBox", (.16, .12, .18), loc=(px, py, .86), paint=teal, bevel=.015, segs=2)
    dv4.cube("CoinFace", (.13, .012, .14), loc=(px, py + .06, .86), paint=cream, bevel=.006, segs=2)
    dv4.cube("CoinSlot", (.012, .01, .05), loc=(px, py + .068, .89), paint=dark, bevel=.002, segs=1)
    dv4.cube("CoinReturn", (.06, .01, .025), loc=(px, py + .068, .815), paint=dark, bevel=.004, segs=1)
    dv4.sphere("CoinKnob", .014, loc=(px + .045, py + .07, .89), seg=8, rings=5, paint=gold)
    blink = "Anim Blink"; dv4.pivot(blink, (px - .04, py + .07, .89))
    dv4.sphere("LED", .012, loc=(px - .04, py + .07, .89), seg=8, rings=5, paint=led, out=blink)
    dv4.sphere("LEDRing", .015, loc=(px - .04, py + .062, .89), seg=8, rings=5, paint=chrome, scale=(1, .5, 1))
    # pennant on the post top
    dv4.tube("Flagpole", [(px, py, .95), (px, py, 1.26)], radius=.007, res=6, paint=chrome, kind="POLY", resolution=1)
    dv4.sphere("FlagBall", .016, loc=(px, py, 1.26), seg=8, rings=5, paint=gold)
    sway = "Anim Sway"; dv4.pivot(sway, (px, py, 1.25))
    F.pennant("Pennant", (px, py, 1.25), .08, .20, red, out=sway, rot_z=200)
    return {"name": "KiddieRide", "tex": 1024, "budget": 6000, "floor": "C9C3B8"}
