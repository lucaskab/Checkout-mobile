"""pet-bed-round: "Caminha redonda" - plush round dog bed for the store dog Caramelo. Thick puffy bolster made of 8 stitched
segments (pinched seams with top-stitching and covered buttons), lower at the front to step in, cream piping around its foot;
a soft fleece cushion inside with a sewn-on paw-print applique and piping on its top edge, on a thin base.
Fabric parts follow the colourway (navy default + teal / orange / rose bakes).
Footprint half .43 x .43, height ~.19 (Blender Z up, front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
from dv4 import MATH, MIX, SMOOTH, NOISE
import _lib_pet as P

CONFIG = {"floor": "F4EFE4", "seed": 31}
RC, A, B = .315, .106, .094      # bolster: ring radius, section half width / half height (at the back)
NSEG = 8                         # puffy segments
SEG, SEC = 72, 14                # resolution around the ring / around the section
DIP = .30                        # the front (+Y) of the bolster is this much lower
SEAM0 = math.pi / 2 + math.pi / NSEG   # first seam (a segment is centred on the front)
CUSH_R, CUSH_H, CUSH_Z = .205, .08, .012


def pinch(t):
    step = 2 * math.pi / NSEG
    d = (t - SEAM0) % step
    d = min(d, step - d)
    return 1 - .2 * math.exp(-(d / .09) ** 2)


def front(t):
    return 1 - DIP * max(0.0, math.sin(t)) ** 2


def bolster_pt(t, phi):
    p, f = pinch(t), front(t)
    a, b = A * p * (1 + .05 * (1 - f)), B * p * f
    dx, dz = P.rsec(phi, a, b, 2.3)
    r = RC + dx
    return (r * math.cos(t), r * math.sin(t), b + dz)


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.2, light=.34)
    cord = P.paint_cord("Piping")

    def bolster_paint(st, pal):
        def deco(c, col):
            nt = c.nt
            ang = MATH(nt, "ARCTAN2", c.y, c.x)
            u = MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", ang, SEAM0), NSEG / (2 * math.pi))
            d = P.MUL(nt, P.ABS(nt, P.SUB(nt, P.FRACT(nt, P.ADD(nt, u, .5)), .5)), 2 * math.pi / NSEG * RC)   # metres to the seam
            col = MIX(nt, P.MUL(nt, SMOOTH(nt, d, .035, .0), .45), col, pal["dark"])
            q = P.ADD(nt, c.z, P.radial(nt, c))
            dash = P.FRACT(nt, MATH(nt, "DIVIDE", q, .016))
            dash = P.MUL(nt, SMOOTH(nt, dash, .12, .25), SMOOTH(nt, dash, .78, .65))
            for off in (-.013, .013):
                line = SMOOTH(nt, P.ABS(nt, P.SUB(nt, d, abs(off))), .0028, .0011)
                col = MIX(nt, P.MUL(nt, line, dash), col, P.CREAM)
            return col
        return P.paint_cloth("Bolster_" + st, pal, "base", kind="velvet", decorate=deco)

    def cushion_paint(st, pal):
        def deco(c, col):
            nt = c.nt
            d = P.sd_paw(nt, c.x, c.y, 0.0, .005, .15, 180.0)       # toes toward -Y: upright from the game camera
            return P.applique(c, col, d, P.CREAM, pal["deco"], inset=.0075)
        return P.paint_cloth("Cushion_" + st, pal, "alt", kind="fleece", decorate=deco, sheen=.2)

    def base_paint(st, pal):
        return P.paint_cloth("Base_" + st, pal, "dark", kind="canvas", sheen=.1)

    bol = P.fabric(bolster_paint)
    cus = P.fabric(cushion_paint)
    base = P.fabric(base_paint)

    # ---- base disc (closes the floor between the bolster and the cushion)
    P.disc("Base", .37, .014, seg=40, paint=base)
    # ---- bolster: rings around the section, wrapped into a torus
    rings = []
    for j in range(SEC):
        phi = -math.pi + 2 * math.pi * j / SEC
        rings.append([bolster_pt(2 * math.pi * k / SEG, phi) for k in range(SEG)])
    P.loft("Bolster", rings, bol, wrap=True)
    # cream piping around the foot of the bolster (follows the puffs)
    P.piping("BolsterPiping", [bolster_pt(2 * math.pi * k / SEG, -math.radians(38)) for k in range(SEG)], r=.0075, paint=cord)
    # covered buttons in the seam pinches on top
    step = 2 * math.pi / NSEG
    for i in range(NSEG):
        t = SEAM0 + i * step
        x, y, z = bolster_pt(t, math.pi / 2)
        dv4.sphere("Button", .016, loc=(x, y, z - .002), scale=(1, 1, .5), seg=10, rings=5, paint=cord)
    # ---- inner cushion with a paw applique and piping on its top edge
    ol = P.oval_pts(CUSH_R, CUSH_R, 40)
    P.cushion("Cushion", ol, CUSH_H, z0=CUSH_Z, e=.03, bulge=.006, puff=.03, paint=cus, bottom=False)
    P.piping("CushionPiping", P.cushion_edge(ol, CUSH_H, CUSH_Z, .03), r=.0062, paint=cord)
    return {"name": "PetBedRound", "tex": 1024, "budget": 6000, "floor": "F4EFE4", "styles": P.STYLES}
