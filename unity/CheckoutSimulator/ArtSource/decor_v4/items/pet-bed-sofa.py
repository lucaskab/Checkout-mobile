"""pet-bed-sofa: "Sofazinho retro" - mini mid-century sofa for Caramelo. Velvet upholstered base, rolled arms with cream piping
around their flat front panels, a rounded back with a diamond-tufted cushion (cream covered buttons), a loose seat cushion with
piping, a small round polka-dot pillow, and tapered splayed walnut legs with brass caps.
Fabric parts follow the colourway (navy default + teal / orange / rose bakes); wood and brass never change.
Footprint half .54 x .42, height ~.58 (Blender Z up, front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
from dv4 import MATH, MIX, SMOOTH, NOISE
import _lib_pet as P
import _lib_A as A

CONFIG = {"floor": "F4EFE4", "seed": 34}
W, D = 1.04, .80                 # upholstered base
ZB0, ZB1 = .136, .25             # base bottom / seat deck
AX, AHW, AZ1 = .485, .056, .425  # arm centre x, half width, top
AY0, AY1 = -.30, .395            # arm back / front
BACK_Y, BACK_T, BACK_Z1 = -.355, .13, .60
TILT = 8.0
PIL = (-.30, -.135, .43)         # small round pillow centre
BC_Y, BC_Z, BC_D, BC_H = -.29, .425, .29, .07          # tufted back cushion (back face y, centre z, height, thickness)
SEAT_W, SEAT_D, SEAT_H, SEAT_Y = .84, .62, .10, .085


def arm(name, sx, paint, cord):
    """Rolled arm: a rounded section (wider roll at the top) skinned along Y, flat front panel outlined with piping."""
    nsec = 20
    zc, hh = (ZB0 + AZ1) / 2, (AZ1 - ZB0) / 2

    def sec(k, scale=1.0):
        phi = -math.pi / 2 + 2 * math.pi * k / nsec
        dx, dz = P.rsec(phi, AHW, hh, 3.2)
        dx *= 1 + .22 * max(0.0, math.sin(phi)) ** 2
        return dx * scale, dz * scale

    rings = []
    for y, sc in ((AY0, .9), (AY0 + .015, 1.0), (AY1 - .03, 1.0), (AY1 - .01, .985), (AY1, .93)):
        ring = []
        for k in range(nsec):
            dx, dz = sec(k, sc)
            ring.append((sx * AX + dx, y, zc + dz))
        rings.append(ring)
    P.loft(name, rings, paint, cap0=True, cap1=True)
    pts = []
    for k in range(nsec):
        dx, dz = sec(k, .93)
        pts.append((sx * AX + dx * .97, AY1 + .004, zc + dz * .97))
    P.piping(name + "Piping", pts, r=.0065, paint=cord)


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.22, light=.34)
    cord = P.paint_cord("Piping")
    wood_x = dv4.paint_wood("Rail", base="7A4A2A", dark="3E2414", light="A86D42", scale=4.0, along="X", tint=.1, edge="C08A5A")
    wood = dv4.paint_wood("Legs", base="7A4A2A", dark="3E2414", light="A86D42", scale=6.0, along="Z", tint=.15, edge="C08A5A")
    brass = dv4.paint_gold("Brass", base="C8963A", dark="7A571A", light="F6DC8C")

    def uph(st, pal):
        return P.paint_cloth("Uph_" + st, pal, "base", kind="velvet")

    def seat(st, pal):
        return P.paint_cloth("Seat_" + st, pal, "alt", kind="velvet")

    def tufted(st, pal):
        origin = (0.0, BC_Y, BC_Z)
        return A.paint_tufted("Tufted_" + st, base=pal["alt"], dark=pal["dark"], light=pal["light"], px=.15, py=2 * BC_D / 3,
                              origin=origin, axis="XZ", tilt=TILT, dimple_r=.028, crease=.01)

    def pillow(st, pal):
        def deco(c, col):
            nt = c.nt
            # radial gathers converging on the centre button (pillow centre in world space)
            dx, dy, dz = P.SUB(nt, c.x, PIL[0]), P.SUB(nt, c.y, PIL[1]), P.SUB(nt, c.z, PIL[2])
            ang = MATH(nt, "ARCTAN2", P.ADD(nt, P.MUL(nt, dx, .9), P.MUL(nt, dy, -.45)), dz)
            g = P.ABS(nt, P.SUB(nt, P.FRACT(nt, P.MUL(nt, ang, 12 / (2 * math.pi))), .5))
            r = MATH(nt, "SQRT", P.ADD(nt, P.ADD(nt, P.MUL(nt, dx, dx), P.MUL(nt, dy, dy)), P.MUL(nt, dz, dz)))
            fold = P.MUL(nt, SMOOTH(nt, g, .3, .5), SMOOTH(nt, r, .075, .02))
            return MIX(nt, P.MUL(nt, fold, .45), col, pal["dark"])
        return P.paint_cloth("Pillow_" + st, pal, "light", kind="velvet", decorate=deco)

    up = P.fabric(uph)
    se = P.fabric(seat)
    tu = P.fabric(tufted)
    pi = P.fabric(pillow)

    # ---- legs: tapered, splayed, brass caps
    leg = [(0, 0), (.0135, 0), (.0145, .02), (.0165, .022), (.024, .128), (.026, .142), (0, .142)]
    cap = [(0, 0), (.0145, 0), (.0152, .006), (.0152, .021), (0, .021)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            i0 = P.mark()
            dv4.lathe("Leg", leg, seg=8, paint=wood)
            dv4.lathe("Cap", cap, seg=8, paint=brass)
            P.place(i0, (sx * .43, sy * .30, 0), (sy * 9, -sx * 9, 0))
    # ---- walnut plinth rail under the upholstery, then base, back, arms
    dv4.cube("Rail", (W - .05, D - .05, .024), loc=(0, 0, ZB0 - .01), paint=wood_x, bevel=.008, segs=2)
    ol = P.rrect_pts(W, D, .07, 3, 4, 3)
    P.cushion("Base", ol, ZB1 - ZB0, z0=ZB0, e=.035, bulge=.006, puff=.0, paint=up, bottom=False)
    dv4.cube("Back", (W + .02, BACK_T, BACK_Z1 - ZB0), loc=(0, BACK_Y, (ZB0 + BACK_Z1) / 2), paint=up, bevel=.055, segs=3)
    for sx in (-1, 1):
        arm("Arm", sx, up, cord)
    # ---- tufted back cushion leaning on the back
    A.tufted_cushion("BackCushion", W - 2 * AHW * 2 - .02, BC_D, BC_H, px=.15, rows=3, amp=.018, nx=22, ny=7, paint=tu,
                     loc=(0, BC_Y, BC_Z), rot=(-90 + TILT, 0, 0), bevel=.025, segs=2, button_r=.011, button_paint=cord, dimple=.012)
    # ---- loose seat cushion with piping
    ol = P.rrect_pts(SEAT_W, SEAT_D, .07, 3, 4, 3)
    P.cushion("Seat", ol, SEAT_H, z0=ZB1, e=.03, bulge=.007, puff=.022, paint=se, loc=(0, SEAT_Y, 0), bottom=False)
    for top in (True, False):
        P.piping("SeatPiping", [(x, y + SEAT_Y, z) for x, y, z in P.cushion_edge(ol, SEAT_H, ZB1, .03, top)], r=.0065, paint=cord)
    # ---- small round pillow in the left corner
    i0 = P.mark()
    prof = [(0, -.034), (.045, -.031), (.07, -.022), (.083, -.009), (.086, 0), (.083, .009), (.07, .022), (.045, .031), (0, .034)]
    dv4.lathe("Pillow", prof, seg=20, paint=pi)
    dv4.torus("PillowPiping", .085, .0055, seg=20, minor=5, paint=cord)
    for s in (-1, 1):
        dv4.sphere("PillowButton", .011, loc=(0, 0, s * .032), scale=(1, 1, .5), seg=8, rings=4, paint=cord)
    P.place(i0, PIL, (-72, 0, -28))
    return {"name": "PetBedSofa", "tex": 1024, "budget": 6000, "floor": "F4EFE4", "styles": P.STYLES}
