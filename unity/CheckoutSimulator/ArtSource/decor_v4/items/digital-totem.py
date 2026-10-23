"""digital-totem: sleek digital signage totem - brushed aluminium rounded housing on a heavy base plate, navy bezel with a
cyan LED edge, gold trim bands, the screen is a quad with material T_IK_Screen (0..1 UVs) on "Anim Scroll",
a blinking power LED on "Anim Blink". Footprint half .34 x .20, height <= 2.2 (front +Y)."""
import os, sys, math
import dv4
from dv4 import RNG, MATH, MIX, RAMP, NOISE, SMOOTH, WAVE, COORD
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_B as lib

lib.install_fixes()
CONFIG = {"floor": "F4EFE4", "seed": 2}
LED = "E_6FE3FF"


def paint_grille(name="Grille"):
    def r(c):
        nt = c.nt
        lines = WAVE(nt, COORD(nt, scale=(1, 1, 1)), 90.0, 0.0, 0.0, 1.0, "Z")
        return RAMP(nt, lines, [(.35, "2A3238"), (.6, "4C565E")])
    return dv4.paint(name, r, k_ao=.5)


def build():
    dv4.FINISH.update(ao=.55, ao_dist=.2, light=.4)
    alu = lib.paint_brushed("Alu", axis="Z")
    alu_h = lib.paint_brushed("AluH", axis="X", base="A9B3B9", dark="737E86")
    navy = dv4.paint_flat("Navy", "1D2B4F", dark="0E1730", variation=.18, scale=5.0, edge="4A5C8C", edge_k=.6, edge_r=.004)
    gold = dv4.paint_gold("Gold")
    dark = dv4.paint_flat("Dark", "22282E", variation=.1)
    grille = paint_grille("Grille")

    # ---- base: heavy plate with a chamfer, rubber pad underneath, a neck into the housing
    dv4.cube("Pad", (.62, .37, .012), loc=(0, 0, .006), paint=dark, bevel=.004, segs=2)
    dv4.cube("Plate", (.66, .40, .034), loc=(0, 0, .029), paint=alu_h, bevel=.012, segs=4)
    for x in (-.322, .322):
        dv4.cube("TrimX%s" % x, (.014, .40, .008), loc=(x, 0, .05), paint=gold, bevel=.003, segs=2)
    for y in (-.192, .192):
        dv4.cube("TrimY%s" % y, (.66, .014, .008), loc=(0, y, .05), paint=gold, bevel=.003, segs=2)
    dv4.cube("Neck", (.32, .17, .07), loc=(0, 0, .085), paint=alu, bevel=.015, segs=4)
    # ---- housing: rounded aluminium slab, gold bands top & bottom, navy front bezel
    H0, H1 = .11, 2.1
    dv4.cube("Housing", (.60, .13, H1 - H0), loc=(0, 0, (H0 + H1) / 2), paint=alu, bevel=.038, segs=6)
    dv4.cube("BandLo", (.612, .142, .016), loc=(0, 0, H0 + .07), paint=gold, bevel=.006, segs=3)
    dv4.cube("BandHi", (.612, .142, .016), loc=(0, 0, H1 - .07), paint=gold, bevel=.006, segs=3)
    dv4.cube("Bezel", (.56, .024, 1.84), loc=(0, .062, 1.13), paint=navy, bevel=.009, segs=3)
    # LED edge strip around the bezel (glow slot, same colour as the power LED)
    fy = .0745
    for z, h in ((1.13 - .91, .008), (1.13 + .91, .008)):
        dv4.cube("LedH%s" % z, (.576, .006, .012), loc=(0, fy, z), paint=None, mat_override=LED, bevel=0)
    for x in (-.282, .282):
        dv4.cube("LedV%s" % x, (.012, .006, 1.83), loc=(x, fy, 1.13), paint=None, mat_override=LED, bevel=0)
    # ---- screen: single quad, 0..1 UVs (fixed after the bake), scrolled in thirds by CheckoutInteriorLife
    scroll = "Anim Scroll"; dv4.pivot(scroll, (0, .0755, 1.19))
    lib.plane("Screen", .50, 1.50, loc=(0, .0755, 1.19), paint=None, out=scroll, mat_override="T_IK_Screen")
    # chin: gold emblem (starburst disc) and a blinking power LED
    dv4.lathe("Emblem", [(0, 0), (.022, 0), (.024, .004), (.02, .007), (0, .008)], seg=24, loc=(0, .074, .33), rot=(-90, 0, 0), paint=gold, scallop=(10, .12))
    dv4.sphere("EmblemDot", .007, loc=(0, .08, .33), seg=10, rings=6, paint=navy)
    blink = "Anim Blink"; dv4.pivot(blink, (.2, .076, .33))
    dv4.sphere("PowerLed", .007, loc=(.2, .076, .33), seg=10, rings=6, paint=None, out=blink, mat_override=LED)
    dv4.torus("LedRing", .011, .003, loc=(.2, .075, .33), rot=(90, 0, 0), seg=16, minor=5, paint=gold)
    # top: camera eye + ambient sensor strip; back: vent grille and a cable port
    dv4.sphere("Cam", .009, loc=(0, .058, H1 - .09), seg=12, rings=8, paint=dark)
    dv4.torus("CamRing", .012, .003, loc=(0, .06, H1 - .09), rot=(90, 0, 0), seg=16, minor=5, paint=gold)
    dv4.cube("Vent", (.34, .012, .30), loc=(0, -.066, .45), paint=grille, bevel=.004, segs=2)
    dv4.cube("Vent2", (.34, .012, .30), loc=(0, -.066, 1.75), paint=grille, bevel=.004, segs=2)
    dv4.cube("Port", (.07, .012, .035), loc=(0, -.066, .17), paint=dark, bevel=.003, segs=2)
    return {"name": "DigitalTotem", "tex": 1024, "budget": 6000, "floor": "F4EFE4"}
