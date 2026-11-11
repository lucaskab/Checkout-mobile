"""pet-bed-basket: "Cesta de vime" - oval wicker dog basket for Caramelo. Woven body (over-under strands on stakes), a rolled
twisted rim that dips low at the front to step in, two wrapped side handles; a plump oval cushion with cream piping, a plaid
blanket folded over the front-left rim, and a red rubber chew bone.
Fabric parts (cushion, blanket) follow the colourway (navy default + teal / orange / rose bakes); wicker and toy never change.
Footprint half .49 x .37, height ~.33 (Blender Z up, front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
from dv4 import MATH, MIX, RAMP, SMOOTH, NOISE, COORD, ATTR
import _lib_pet as P

CONFIG = {"floor": "F4EFE4", "seed": 32}
RXT, RYT = .45, .35          # rim radii
RXB, RYB = .385, .295        # foot radii
HB, HF = .30, .165           # rim height at the back / at the front dip
WALL = .024
SEG = 64
CRX, CRY, CZ0, CH, CPUFF = .35, .26, .03, .085, .022     # cushion
RIM_R = .021
BLANKET_T, BLANKET_HALF = math.radians(122), math.radians(17)


def top(t):
    return HB - (HB - HF) * max(0.0, math.cos(t - math.pi / 2)) ** 3


def wall_ring(f, inset=0.0, zf=None):
    pts = []
    for k in range(SEG):
        t = 2 * math.pi * k / SEG
        rx = RXB + (RXT - RXB) * f - inset; ry = RYB + (RYT - RYB) * f - inset
        pts.append((rx * math.cos(t), ry * math.sin(t), zf(t) if zf else f * top(t)))
    return pts


def cushion_top(f):
    return CZ0 + CH + CPUFF * (1 - min(1.0, f) ** 2)


def ell_r(psi, a, b):
    return a * b / math.sqrt((b * math.cos(psi)) ** 2 + (a * math.sin(psi)) ** 2)


def blanket(paint):
    nj = 8
    cols = []
    for j in range(nj + 1):
        g = j / nj
        t = BLANKET_T + BLANKET_HALF * (2 * g - 1)
        rx, ry = (RXT - WALL * .5) * math.cos(t), (RYT - WALL * .5) * math.sin(t)
        psi = math.atan2(ry, rx); dx, dy = math.cos(psi), math.sin(psi)
        rc = math.hypot(rx, ry); zr = top(t) + .004
        rk = ell_r(psi, CRX, CRY)
        fold = .006 * math.sin(g * math.pi * 2.5 + .6)
        R = RIM_R + .007
        path = [(.2 * rk, cushion_top(.2) + .009 + fold * .3), (.5 * rk, cushion_top(.5) + .009 + fold * .6),
                (.78 * rk, cushion_top(.8) + .01 + fold), (.96 * rk, CZ0 + CH + .006 + fold)]
        path.append(((rk + rc - R) * .5, (path[-1][1] + zr + R) * .5 + .006))
        for a in (125, 95, 62, 30, 0):
            path.append((rc + R * math.cos(math.radians(a)), zr + R * math.sin(math.radians(a))))
        hem = .012 * math.sin(g * math.pi * 3.0)
        for dz, dr in ((-.045, .004), (-.085, .009 + hem * .5), (-.12, .013 + hem)):
            path.append((rc + R + dr, zr + dz))
        cols.append([(dx * r, dy * r, z) for r, z in path])
    # rings = rows along the path (each row runs across the width)
    rows = [[cols[j][i] for j in range(nj + 1)] for i in range(len(cols[0]))]
    L = [0.0]
    for i in range(1, len(rows)):
        a, b = rows[i - 1][nj // 2], rows[i][nj // 2]
        L.append(L[-1] + math.dist(a, b))
    ob = P.loft("Blanket", rows, paint, closed=False, attr=lambda i, k: (L[i] / L[-1], k / nj))
    dv4.mod_solidify(ob, .010, offset=0.0)
    return ob


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.2, light=.34)
    cord = P.paint_cord("Piping")
    toy = P.paint_rubber_toy("Bone")

    def wicker_recipe(c):
        nt = c.nt
        ang = P.ADD(nt, MATH(nt, "ARCTAN2", MATH(nt, "DIVIDE", c.y, RYT), MATH(nt, "DIVIDE", c.x, RXT)), math.pi)
        u = P.MUL(nt, ang, 46 / (2 * math.pi)); v = MATH(nt, "DIVIDE", c.z, .026)
        fu, fv = P.FRACT(nt, u), P.FRACT(nt, v)
        par = MATH(nt, "MODULO", P.ADD(nt, P.FLOOR(nt, u), P.FLOOR(nt, v)), 2.0)
        strand = MATH(nt, "POWER", MATH(nt, "SINE", P.MUL(nt, fv, math.pi)), .55)
        stake = MATH(nt, "POWER", MATH(nt, "SINE", P.MUL(nt, fu, math.pi)), .55)
        pv = P.ADD(nt, stake, P.MUL(nt, par, P.SUB(nt, strand, stake)))
        tone = NOISE(nt, COORD(nt, scale=(3, 3, 40)), 1.0, 2.0)
        col = RAMP(nt, pv, [(.0, "4F3216"), (.35, "9A6630"), (.7, "C9954F"), (1.0, "EBC27E")])
        col = MIX(nt, P.MUL(nt, tone, .3), col, "8A5A28")
        fib = NOISE(nt, COORD(nt, scale=(10, 10, 160)), 1.0, 2.0)
        col = MIX(nt, P.MUL(nt, fib, .18), col, "6B4220")
        return col

    def rim_recipe(c):
        nt = c.nt
        ang = MATH(nt, "ARCTAN2", MATH(nt, "DIVIDE", c.y, RYT), MATH(nt, "DIVIDE", c.x, RXT))
        q = P.ADD(nt, P.ADD(nt, P.MUL(nt, ang, .40), P.MUL(nt, c.z, 1.3)), P.MUL(nt, P.radial(nt, c), 1.3))
        f = P.FRACT(nt, MATH(nt, "DIVIDE", q, .024))
        prof = MATH(nt, "SINE", P.MUL(nt, f, math.pi))
        col = RAMP(nt, prof, [(.0, "7A5226"), (.45, "B07A3E"), (.85, "D3A262"), (1.0, "E6C27F")])
        return MIX(nt, P.MUL(nt, NOISE(nt, COORD(nt, scale=(30, 30, 30)), 1.0, 2.0), .15), col, "6B4220")

    def wrap_recipe(c):
        nt = c.nt
        f = P.FRACT(nt, MATH(nt, "DIVIDE", P.ADD(nt, c.y, P.MUL(nt, c.z, .45)), .011))
        prof = MATH(nt, "SINE", P.MUL(nt, f, math.pi))
        return RAMP(nt, prof, [(.0, "5E3C1A"), (.45, "B07A3E"), (1.0, "E8C07E")])

    wicker = dv4.paint("Wicker", wicker_recipe, edge="EBC27E", edge_k=.4, edge_r=.006)
    rim = dv4.paint("Rim", rim_recipe, k_ao=.5)
    wrap = dv4.paint("Handle", wrap_recipe, k_ao=.5)

    def cushion_paint(st, pal):
        return P.paint_cloth("Cushion_" + st, pal, "base", kind="velvet")

    def blanket_paint(st, pal):
        def r(c):
            nt = c.nt
            R, G, _ = ATTR(nt)
            col = MIX(nt, P.MUL(nt, NOISE(nt, c.pos, 70.0, 2.0), .12), P.CREAM, P.CREAM_D)
            def band(x, lo, hi, s=.012):
                return P.MUL(nt, SMOOTH(nt, x, lo - s, lo + s), SMOOTH(nt, x, hi + s, hi - s))
            bg = P.MAX(nt, band(G, .1, .26), band(G, .74, .9))
            br = P.MAX(nt, band(R, .06, .14, .006), band(R, .78, .86, .006))
            col = MIX(nt, P.MUL(nt, bg, .9), col, pal["base"])
            col = MIX(nt, P.MUL(nt, br, .75), col, pal["base"])
            col = MIX(nt, P.MUL(nt, P.MUL(nt, bg, br), .6), col, pal["dark"])
            thin = P.MAX(nt, band(G, .49, .51, .006), band(R, .46, .475, .004))
            col = MIX(nt, P.MUL(nt, thin, .8), col, pal["light"])
            fringe = P.MUL(nt, SMOOTH(nt, R, .955, .97), SMOOTH(nt, P.ABS(nt, P.SUB(nt, P.FRACT(nt, P.MUL(nt, G, 40.0)), .5)), .32, .18))
            col = MIX(nt, P.MUL(nt, fringe, .5), col, P.CREAM_D)
            col = MIX(nt, P.MUL(nt, c.crev, .4), col, pal["dark"])
            return col
        return dv4.paint("Blanket_" + st, r, k_ao=.55, k_light=.32)

    cus = P.fabric(cushion_paint)
    bla = P.fabric(blanket_paint)

    # ---- woven body: outer wall up to the rim, inner wall back down to the floor of the basket
    rings = [wall_ring(0, .012, lambda t: 0.0), wall_ring(0, 0, lambda t: .012)]
    for f in (.33, .66, 1.0):
        rings.append(wall_ring(f))
    rings.append(wall_ring(1.0, WALL))
    rings.append(wall_ring(.5, WALL))
    rings.append(wall_ring(.05, WALL, lambda t: CZ0))
    rings.append([(0.0, 0.0, CZ0)])
    P.loft("Basket", rings, wicker, cap0=True)
    # rolled rim following the front dip
    n = 48
    pts = []
    for k in range(n):
        t = 2 * math.pi * k / n
        pts.append(((RXT - WALL * .5) * math.cos(t), (RYT - WALL * .5) * math.sin(t), top(t) + .004))
    P.piping("RimRoll", pts, r=RIM_R, paint=rim, sides=6)
    # wrapped side handles
    for s in (-1, 1):
        hp = [(s * .433, -.10, .262), (s * .462, -.072, .332), (s * .472, 0, .354), (s * .462, .072, .332), (s * .433, .10, .262)]
        dv4.tube("Handle", hp, radius=.013, res=6, paint=wrap, resolution=5)
    # ---- cushion, piping, blanket, toy
    ol = P.oval_pts(CRX, CRY, 40)
    P.cushion("Cushion", ol, CH, z0=CZ0, e=.03, bulge=.006, puff=CPUFF, paint=cus, bottom=False)
    P.piping("CushionPiping", P.cushion_edge(ol, CH, CZ0, .03), r=.0062, paint=cord)
    blanket(bla)
    f = math.hypot(.13 / CRX, .09 / CRY)
    P.bone_toy("Bone", (.13, .09, cushion_top(f) - .006), rot_z=28, paint=toy)
    return {"name": "PetBedBasket", "tex": 1024, "budget": 6000, "floor": "F4EFE4", "styles": P.STYLES}
