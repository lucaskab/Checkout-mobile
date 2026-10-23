"""floor-lamp: elegant floor lamp - weighted brass base on a felt ring, turned brass stem with baluster knobs, a pleated cream
fabric shade (real pleats + stitched seams, lit warm inside) with a teal ribbon trim, brass finial and pull chain; the bulb and
the glowing top opening use the E_ slot. Footprint half .24 x .24, height <= 1.9 (Blender Z up, front +Y)."""
import os, sys, math
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_A as lib

CONFIG = {"floor": "F4EFE4", "seed": 5}
GLOW = "E_FFD27A"


def build():
    dv4.FINISH.update(ao=.55, ao_dist=.2, light=.34)
    brass = lib.paint_brass("Brass", base="BA8530", dark="5E3E0E", light="F2CB64")
    felt = dv4.paint_flat("Felt", "2F3A40", dark="161C20", variation=.3, scale=12.0)
    shade = lib.paint_fabric("Shade", base="F6EFDF", dark="D8CAAE", light="FFFDF6", weave=22.0, pleats=26,
                             glow=("FFCD8C", 1.57, .17), seam="C8B898", inner="FFDC9E")
    teal = dv4.paint_flat("Ribbon", "1F9A8E", dark="12605A", variation=.25, scale=16.0, edge="6FD0C4", edge_r=.004)

    # ---- base: felt ring, heavy brass dome stepping into the stem
    dv4.lathe("Felt", [(0, 0), (.185, 0), (.185, .008), (0, .008)], seg=28, paint=felt)
    base = [(0, .006), (.19, .006), (.198, .016), (.198, .034), (.188, .05), (.16, .06), (.12, .068), (.075, .078), (.048, .092),
            (.036, .11), (.03, .13), (.022, .15)]
    dv4.lathe("Base", base, seg=28, paint=brass)
    dv4.torus("BaseRing", .17, .007, loc=(0, 0, .058), seg=28, minor=6, paint=brass)
    # ---- turned stem: slender rod with two balusters and a collar, socket cup on top
    stem = [(0, .15), (.022, .15), (.017, .18), (.016, .42), (.028, .44), (.046, .47), (.048, .50), (.038, .53), (.024, .555),
            (.016, .58), (.016, .96), (.03, .975), (.04, 1.0), (.034, 1.03), (.022, 1.05), (.016, 1.07), (.016, 1.38), (.028, 1.395),
            (.034, 1.42), (.03, 1.44), (.02, 1.455), (.02, 1.49), (.034, 1.50), (.04, 1.53), (.04, 1.55), (0, 1.55)]
    dv4.lathe("Stem", stem, seg=20, paint=brass)
    # pull chain with a tiny ball
    dv4.tube("Chain", [(.04, .012, 1.53), (.052, .02, 1.47), (.055, .022, 1.41)], radius=.0025, res=4, paint=brass, resolution=3)
    dv4.sphere("ChainBall", .007, loc=(.055, .022, 1.405), seg=8, rings=5, paint=brass)
    # ---- shade: pleated cone (scalloped lathe, solidified so the inside is visible from above), trims and finial
    z0, z1, r0, r1 = 1.47, 1.80, .224, .145
    prof = [(r0, z0), (r0 - .002, z0 + .02), (r0 + (r1 - r0) * .5, z0 + (z1 - z0) * .5), (r1 + .002, z1 - .02), (r1, z1)]
    sh = dv4.lathe("Shade", prof, seg=78, paint=shade, cap=False, scallop=(26, .022))
    dv4.mod_solidify(sh, .004, offset=-1.0)
    dv4.lathe("TrimBottom", [(r0 + .004, z0 - .006), (r0 + .012, z0 - .002), (r0 + .012, z0 + .016), (r0 + .004, z0 + .02)], seg=52,
              paint=teal, cap=False, scallop=(26, .02))
    dv4.torus("TrimTop", r1 + .002, .006, loc=(0, 0, z1), seg=36, minor=6, paint=brass)
    # spider: three brass arms from the top ring to the finial hub
    for i in range(3):
        a = math.radians(90 + i * 120)
        dv4.tube("Spider%d" % i, [(math.cos(a) * r1, math.sin(a) * r1, z1), (math.cos(a) * .02, math.sin(a) * .02, z1 + .01)],
                 radius=.004, res=5, paint=brass, kind="POLY", resolution=1)
    dv4.lathe("Finial", [(0, z1 - .01), (.022, z1 - .01), (.022, z1 + .012), (.014, z1 + .02), (.02, z1 + .035), (.026, z1 + .055),
                         (.018, z1 + .075), (.006, z1 + .088), (0, z1 + .09)], seg=16, paint=brass)
    # ---- light: bulb inside, glowing disc in the top opening (what the game camera sees)
    dv4.sphere("Bulb", .036, loc=(0, 0, 1.615), scale=(1, 1, 1.25), seg=12, rings=8, paint=None, mat_override=GLOW)
    dv4.lathe("GlowTop", [(0, z1 - .012), (r1 - .01, z1 - .012), (r1 - .01, z1 - .008), (0, z1 - .008)], seg=36, paint=None, mat_override=GLOW)
    return {"name": "FloorLamp", "tex": 1024, "budget": 6000, "floor": "F4EFE4"}
