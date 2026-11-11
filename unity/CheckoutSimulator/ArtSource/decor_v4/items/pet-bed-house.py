"""pet-bed-house: "Casinha de madeira" - wooden dog house for Caramelo. Teal painted lap-siding walls with chipped edges and cream
corner boards, a terracotta shingle roof (overlapping courses, ridge cap, cream barge boards) with a deep front overhang, a
round-arched door with cream trim and an orange plaque with a bone pictogram above it. A cushion inside shows through the door;
a padded mat with piping and a paw applique lies in front of the door (flat area ~.8 x .5 where the dog sleeps).
Fabric parts (inner cushion, mat) follow the colourway (navy default + teal / orange / rose bakes).
Footprint half .45 x .50, height ~.84 (Blender Z up, front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
from dv4 import MATH, MIX, RAMP, SMOOTH, NOISE, COORD
import _lib_pet as P

CONFIG = {"floor": "F4EFE4", "seed": 33}
HW, Y0, Y1 = .38, -.50, -.02          # half width, back face, front face of the house
Z0, ZE, ZR, T = .04, .50, .78, .03    # floor (plinth top), eaves, ridge (wall), wall thickness
DW, ZS = .165, .245                   # door half width, arch springing height
ALPHA = math.atan((ZR - ZE) / HW)
OVER_X, OVER_F, OVER_B = .075, .095, .035
DECK, TH, NCOURSE = .018, .016, 6
MAT_W, MAT_D, MAT_H, MAT_Y = .80, .50, .07, .245


def gable(x):
    return ZE + (ZR - ZE) * (1 - abs(x) / HW)


def panel(name, x0, x1, nx, bottom, y, nz, paint):
    rows = []
    for j in range(nz + 1):
        u = j / nz
        row = []
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            b, t = bottom(x), gable(x)
            row.append((x, y, b + (t - b) * u))
        rows.append(row)
    ob = P.loft(name, rows, paint, closed=False, smooth=False)
    dv4.mod_solidify(ob, T, offset=0.0)
    return ob


def build():
    dv4.FINISH.update(ao=.64, ao_dist=.22, light=.34)
    ca, sa = math.cos(ALPHA), math.sin(ALPHA)
    L = (HW + OVER_X) / ca + .01                    # slope length ridge -> eave edge
    step = L / NCOURSE

    def siding_recipe(c):
        nt = c.nt
        v = MATH(nt, "DIVIDE", P.SUB(nt, c.z, Z0), .072)
        fr, idx = P.FRACT(nt, v), P.FLOOR(nt, v)
        strokes = NOISE(nt, COORD(nt, scale=(2.5, 2.5, 45)), 1.0, 3.0)
        col = RAMP(nt, strokes, [(.25, "17766D"), (.55, "1F9A8E"), (.85, "4FBCAE")])
        cb = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(P.MUL(nt, idx, .73), cb.inputs[0])
        tone = NOISE(nt, cb.outputs[0], 3.0, 1.0)
        col = MIX(nt, P.MUL(nt, tone, .25), col, "5CC4B6")
        col = MIX(nt, P.MUL(nt, SMOOTH(nt, fr, .22, .0), .45), col, "0E4F48")          # shadow under each lap
        col = MIX(nt, P.MUL(nt, SMOOTH(nt, fr, .9, 1.0), .25), col, "8AD8CC")           # lit lap edge
        chips = SMOOTH(nt, NOISE(nt, c.pos, 20.0, 3.0, .6), .70, .74)
        chips = P.MUL(nt, chips, P.ADD(nt, .3, c.crev))
        col = MIX(nt, P.MIN(nt, chips, 1.0), col, "B98552")
        grime = P.MUL(nt, SMOOTH(nt, c.z, Z0 + .1, Z0), .35)
        return MIX(nt, grime, col, "3E4A40")

    def shingle_recipe(c):
        nt = c.nt
        s = MATH(nt, "DIVIDE", P.ABS(nt, c.x), ca)
        w = MATH(nt, "DIVIDE", P.SUB(nt, L, s), step)
        fw, iw = P.FRACT(nt, w), P.FLOOR(nt, w)
        tab = .085
        tv = MATH(nt, "DIVIDE", P.ADD(nt, c.y, P.MUL(nt, iw, tab * .5)), tab)
        ft, it = P.FRACT(nt, tv), P.FLOOR(nt, tv)
        cb = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(P.MUL(nt, it, .61), cb.inputs[0]); nt.links.new(P.MUL(nt, iw, .37), cb.inputs[1])
        tone = NOISE(nt, cb.outputs[0], 2.0, 1.0)
        col = RAMP(nt, tone, [(.3, "B44A2E"), (.55, "C9583A"), (.8, "DD7350")])
        col = MIX(nt, P.MUL(nt, NOISE(nt, c.pos, 45.0, 2.0), .18), col, "7E2F1E")
        slit = SMOOTH(nt, P.ABS(nt, P.SUB(nt, ft, .5)), .455, .49)
        col = MIX(nt, P.MUL(nt, slit, .75), col, "5A2014")
        col = MIX(nt, P.MUL(nt, SMOOTH(nt, fw, .2, .0), .45), col, "6E2618")             # shadow just above each butt
        col = MIX(nt, P.MUL(nt, SMOOTH(nt, c.nz, .2, .9), .15), col, "F09A78")
        return col

    def plaque_recipe(c):
        nt = c.nt
        col = MIX(nt, P.MUL(nt, NOISE(nt, c.pos, 30.0, 2.0), .2), "EC862E", "B85E18")
        d = P.sd_bone(nt, c.x, c.z, 0.0, .515, .068, .019, 10.0)
        col = MIX(nt, P.MUL(nt, SMOOTH(nt, d, .006, .0), .35), col, "7A3A0E")
        col = MIX(nt, P.fill(nt, d), col, P.CREAM)
        border = SMOOTH(nt, P.ABS(nt, P.sd_rrect(nt, c.x, c.z, 0.0, .515, .061, .03, .018)), .0035, .0015)
        return MIX(nt, P.MUL(nt, border, .8), col, P.CREAM)

    siding = dv4.paint("Siding", siding_recipe, edge="8AD8CC", edge_k=.5, edge_r=.005)
    shingles = dv4.paint("Shingles", shingle_recipe, edge="F09A78", edge_k=.5, edge_r=.004)
    plaque = dv4.paint("Plaque", plaque_recipe, edge="FFC07A", edge_k=.6, edge_r=.004)
    trim = dv4.paint_flat("Trim", P.CREAM, dark=P.CREAM_D, variation=.18, edge="FFFFFF")
    wood = dv4.paint_wood("Plinth", base="A8673A", dark="5E3519", light="D69C5E", along="X", tint=.15)
    deck_w = dv4.paint_wood("Deck", base="B97A45", dark="6B4128", light="DDA55F", along="Y", tint=.2)
    nails = dv4.paint_gold("Nail")
    cord = P.paint_cord("Piping")

    def cushion_paint(st, pal):
        return P.paint_cloth("Inner_" + st, pal, "alt", kind="velvet")

    def mat_paint(st, pal):
        def deco(c, col):
            nt = c.nt
            for yy in (MAT_Y - .085, MAT_Y + .085):               # quilting channels
                d = P.ABS(nt, P.SUB(nt, c.y, yy))
                col = MIX(nt, P.MUL(nt, SMOOTH(nt, d, .02, .0), .35), col, pal["dark"])
                line = SMOOTH(nt, d, .0026, .001)
                col = MIX(nt, P.MUL(nt, line, P.dashes(nt, c, .014)), col, P.CREAM)
            d = P.sd_paw(nt, c.x, c.y, -.27, MAT_Y + .15, .11, 192.0)
            return P.applique(c, col, d, P.CREAM, pal["deco"], inset=.006)
        return P.paint_cloth("Mat_" + st, pal, "base", kind="velvet", decorate=deco)

    inner = P.fabric(cushion_paint)
    matp = P.fabric(mat_paint)

    yc = (Y0 + Y1) / 2
    # ---- plinth and walls
    dv4.cube("Plinth", (2 * HW + .02, Y1 - Y0 + .02, Z0), loc=(0, yc, Z0 / 2), paint=wood, bevel=.008, segs=2)
    yf = Y1 - T / 2
    panel("FrontL", -HW, -DW, 4, lambda x: Z0, yf, 6, siding)
    panel("FrontR", DW, HW, 4, lambda x: Z0, yf, 6, siding)
    panel("FrontArch", -DW, DW, 12, lambda x: ZS + math.sqrt(max(0.0, DW * DW - x * x)), yf, 3, siding)
    panel("Back", -HW, HW, 12, lambda x: Z0, Y0 + T / 2, 6, siding)
    for s in (-1, 1):
        dv4.cube("Side", (T, Y1 - Y0 - .002, ZE - Z0), loc=(s * (HW - T / 2), yc, (Z0 + ZE) / 2), paint=siding, bevel=.004, segs=1)
        for y in (Y1 - .014, Y0 + .014):
            dv4.cube("Corner", (.036, .036, ZE - Z0 + .01), loc=(s * (HW - .012), y, (Z0 + ZE) / 2 + .005), paint=trim, bevel=.006, segs=2)
    # ---- door: cream trim around the arch, sill, plaque with a bone
    R = DW + .016
    pts = [(-R, Y1 + .006, Z0 + .002), (-R, Y1 + .006, ZS)]
    for k in range(1, 12):
        a = math.pi * (1 - k / 12)
        pts.append((R * math.cos(a), Y1 + .006, ZS + R * math.sin(a)))
    pts += [(R, Y1 + .006, ZS), (R, Y1 + .006, Z0 + .002)]
    P.piping("DoorTrim", pts, r=.017, paint=trim, cyclic=False)
    dv4.cube("Sill", (2 * DW + .04, .05, .016), loc=(0, Y1 - .005, Z0 + .008), paint=trim, bevel=.005, segs=2)
    dv4.cube("Plaque", (.15, .016, .082), loc=(0, Y1 + .008, .515), paint=plaque, bevel=.008, segs=2)
    for x in (-.058, .058):
        dv4.sphere("Nail", .0055, loc=(x, Y1 + .016, .515), scale=(1, .6, 1), seg=8, rings=4, paint=nails)
    # ---- roof: deck boards, overlapping shingle courses, ridge cap, barge boards
    y_lo, y_hi = Y0 - OVER_B, Y1 + OVER_F
    ylen, ymid = y_hi - y_lo, (y_hi + y_lo) / 2
    for s in (-1, 1):
        d = (s * ca, -sa); nrm = (s * sa, ca)
        def at(sv, nv):
            return (d[0] * sv + nrm[0] * nv, ZR + .004 + d[1] * sv + nrm[1] * nv)
        x, z = at(L / 2, DECK / 2)
        dv4.cube("Deck", (L, ylen, DECK), loc=(x, ymid, z), rot=(0, s * math.degrees(ALPHA), 0), paint=deck_w, bevel=.004, segs=1)
        c_len = step * 1.32
        tilt = math.degrees(math.atan(TH / c_len))
        for i in range(NCOURSE):
            sb = L + .012 - i * step                 # butt of course i (from the eave)
            x, z = at(sb - c_len / 2, DECK + TH)
            dv4.cube("Course%d" % i, (c_len, ylen + .012, TH), loc=(x, ymid, z), rot=(0, s * (math.degrees(ALPHA) - tilt), 0),
                     paint=shingles, bevel=.004, segs=1)
        for yb in (y_hi - .014, y_lo + .014):
            x, z = at(L / 2 - .004, -.022)
            dv4.cube("Barge", (L - .01, .028, .05), loc=(x, yb, z), rot=(0, s * math.degrees(ALPHA), 0), paint=trim, bevel=.006, segs=2)
    dv4.cylinder("Ridge", .034, ylen + .03, loc=(0, y_hi + .015, ZR + .004 + DECK + TH * 1.6), rot=(90, 0, 0), seg=14, paint=shingles,
                 bevel=.01)
    # ---- fabric: cushion inside, mat in front of the door
    ol = P.rrect_pts(2 * HW - 2 * T - .03, Y1 - Y0 - 2 * T - .03, .06, 3, 4, 3)
    P.cushion("Inner", ol, .055, z0=Z0, e=.025, bulge=.004, puff=.02, paint=inner, loc=(0, yc, 0), bottom=False)
    ol = P.rrect_pts(MAT_W, MAT_D, .085, 4, 5, 4)
    P.cushion("Mat", ol, MAT_H, z0=0.0, e=.03, bulge=.006, puff=.02, paint=matp, loc=(0, MAT_Y, 0), bottom=False)
    P.piping("MatPiping", [(x, y + MAT_Y, z) for x, y, z in P.cushion_edge(ol, MAT_H, 0.0, .03)], r=.0065, paint=cord)
    return {"name": "PetBedHouse", "tex": 1024, "budget": 6000, "floor": "F4EFE4", "styles": P.STYLES}
