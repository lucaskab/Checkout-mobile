"""neon-cart: freestanding sign - a navy brick panel in a gold frame on a stepped plinth, carrying a blinking neon shopping-cart
pictogram (pink tubes) and four gold neon stars. The neon tubes are E_ slots on six "Anim Blink" nodes (cart body, wheels,
basket bars, star, star, two stars) so they chase; unlit dark glass tubes stay in Body underneath.
Footprint half .50 x .15, height <= 1.9 (Blender Z up, front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
from dv4 import RNG
import _lib_H as H

CONFIG = {"floor": "F4EFE4", "seed": 7}
PINK, GOLDN = "E_FF5FA8", "E_FFD64A"
PW, PH, PT = .90, 1.52, .07      # panel width / height / thickness
Z0 = .11                         # panel bottom (top of the plinth)
ZC = Z0 + PH / 2                 # panel centre height
YN = PT / 2 + .045               # neon tube axis in front of the panel
YO = PT / 2 + .038               # unlit tube axis
RN, RO = .017, .011
RS, RSO = .013, .009             # thinner tubes for the stars


def neon(name, pts, out, colour, off_paint, cyclic=False, kind="POLY", resolution=1, rn=RN, ro=RO):
    """A neon tube (glow slot on a Blink node) plus its unlit twin in Body. pts = [(x, z)] panel coordinates."""
    on = [(x, YN, ZC + z) for x, z in pts]
    off = [(x, YO, ZC + z) for x, z in pts]
    dv4.tube(name, on, radius=rn, res=8, paint=None, out=out, cyclic=cyclic, kind=kind, resolution=resolution, mat_override=colour)
    dv4.tube(name + "Off", off, radius=ro, res=6, paint=off_paint, cyclic=cyclic, kind=kind, resolution=resolution)


def ring(name, cx, cz, r, out, colour, off_paint):
    dv4.torus(name, r, RN, loc=(cx, YN, ZC + cz), rot=(90, 0, 0), seg=20, minor=8, paint=None, out=out, mat_override=colour)
    dv4.torus(name + "Off", r, RO, loc=(cx, YO, ZC + cz), rot=(90, 0, 0), seg=20, minor=6, paint=off_paint)


def star_pts(cx, cz, R, r, n=5):
    pts = []
    for i in range(2 * n):
        a = math.pi / 2 + i * math.pi / n
        rr = R if i % 2 == 0 else r
        pts.append((cx + math.cos(a) * rr, cz + math.sin(a) * rr))
    return pts


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.2, light=.34)
    brick = H.paint_brick("Brick", side="1D2B4F")
    gold = dv4.paint_gold("Frame")
    navy = dv4.paint_flat("Navy", "1D2B4F", dark="0C1430", variation=.18, edge="5468A0")
    offp = dv4.paint_flat("TubeOff", "3B2340", dark="150A1A", variation=.25)
    offg = dv4.paint_flat("TubeOffG", "4A3A16", dark="1C1406", variation=.25)
    steel = dv4.paint_iron("Steel", base="3A4249", mid="5A646C", edge="C9D2D6", rust_amt=0)

    # ---- plinth: two navy steps with a gold line between, steel glides underneath
    dv4.cube("Base", (1.0, .30, .055), loc=(0, 0, .0275), paint=navy, bevel=.012, segs=3)
    dv4.cube("Trim", (.98, .28, .012), loc=(0, 0, .058), paint=gold, bevel=.004, segs=1)
    dv4.cube("Base2", (.96, .26, .05), loc=(0, 0, .085), paint=navy, bevel=.01, segs=2)
    for x in (-.44, .44):
        dv4.cube("Glide", (.08, .25, .012), loc=(x, 0, .006), paint=steel, bevel=.004, segs=1)
    # ---- panel + gold frame with corner rosettes and a top ornament bar
    dv4.cube("Panel", (PW, PT, PH), loc=(0, 0, ZC), paint=brick, bevel=.006, segs=2)
    fx, fz0, fz1 = PW / 2 + .012, Z0 - .004, Z0 + PH + .004
    dv4.tube("Frame", [(-fx, 0, fz0), (fx, 0, fz0), (fx, 0, fz1), (-fx, 0, fz1)], radius=.024, res=10, paint=gold, kind="POLY", cyclic=True)
    for x in (-fx, fx):
        for z in (fz0, fz1):
            dv4.sphere("Rosette", .036, loc=(x, 0, z), seg=12, rings=8, paint=gold)
    dv4.lathe("Finial", [(0, 0), (.03, 0), (.035, .01), (.02, .03), (.012, .05), (.03, .075), (.02, .095), (0, .105)], seg=12,
              loc=(0, 0, fz1 + .03), paint=gold)
    dv4.cube("TopBar", (PW * .6, .03, .02), loc=(0, 0, fz1 + .02), paint=gold, bevel=.006, segs=2)
    # ---- cart pictogram (panel coords, origin at the panel centre)
    cart = "Anim Blink"; dv4.pivot(cart, (0, YN, ZC))
    neon("Basket", [(-.26, .22), (.30, .22), (.23, -.10), (-.17, -.10)], cart, PINK, offp, cyclic=True)
    neon("Handle", [(-.26, .22), (-.33, .38), (-.43, .38)], cart, PINK, offp)
    neon("Axle", [(-.17, -.10), (-.12, -.15)], cart, PINK, offp)
    neon("Axle2", [(.23, -.10), (.17, -.15)], cart, PINK, offp)
    wheels = "Anim Blink.001"; dv4.pivot(wheels, (0, YN, ZC - .21))
    ring("WheelL", -.12, -.21, .05, wheels, PINK, offp)
    ring("WheelR", .17, -.21, .05, wheels, PINK, offp)
    bars = "Anim Blink.002"; dv4.pivot(bars, (0, YN, ZC + .06))
    for i, x in enumerate((-.08, .03, .14)):
        neon("Bar%d" % i, [(x + .012, .21), (x - .010, -.09)], bars, PINK, offp)
    neon("BarH", [(-.215, .06), (.265, .06)], bars, PINK, offp)
    # ---- stars (gold), three Blink nodes so they twinkle independently
    stars = [("Anim Blink.003", [(-.32, .56, .10)]), ("Anim Blink.004", [(.33, .52, .085)]),
             ("Anim Blink.005", [(.32, -.50, .075), (-.34, -.44, .07)])]
    for node, lst in stars:
        dv4.pivot(node, (lst[0][0], YN, ZC + lst[0][1]))
        for k, (sx, sz, R) in enumerate(lst):
            neon("Star%s%d" % (node[-1], k), star_pts(sx, sz, R, R * .5), node, GOLDN, offg, cyclic=True, rn=RS, ro=RSO)
    # ---- small mounting clips holding the tubes (steel)
    for x, z in ((-.26, .22), (.30, .22), (.23, -.10), (-.17, -.10), (-.43, .38), (-.08, .06), (.14, .06)):
        dv4.cube("Clip", (.016, .03, .024), loc=(x, PT / 2 + .016, ZC + z), paint=steel, bevel=.003, segs=1)
    return {"name": "NeonCart", "tex": 1024, "budget": 6000, "floor": "F4EFE4"}
