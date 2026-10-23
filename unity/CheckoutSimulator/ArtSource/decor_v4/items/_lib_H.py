"""_lib_H: extra paint recipes and builders for group H (wine-barrel, neon-cart, giant-teddy, party-tree, aquarium).
Imported by the item scripts:  import _lib_H as H   (dv4_run.py puts ArtSource/decor_v4 on sys.path; this file is in items/,
so the item scripts add their own folder to sys.path before importing)."""
import math
import bpy, bmesh
from mathutils import Vector
import dv4
from dv4 import MATH, VMATH, MIX, RAMP, COORD, NOISE, VORO, WAVE, ATTR, SMOOTH, RNG, rad, paint


# ================================================================================================= node helpers
def XYZ(nt, x, y=0.0, z=0.0):
    n = nt.nodes.new("ShaderNodeCombineXYZ")
    dv4._plug(nt, n.inputs[0], x); dv4._plug(nt, n.inputs[1], y); dv4._plug(nt, n.inputs[2], z)
    return n.outputs[0]


def FLOOR(nt, x):
    return MATH(nt, "FLOOR", x)


def FRACT(nt, x):
    return MATH(nt, "FRACT", x)


def ABS(nt, x):
    return MATH(nt, "ABSOLUTE", x)


def normal_xyz(c):
    sp = c.nt.nodes.new("ShaderNodeSeparateXYZ"); c.nt.links.new(c.geo.outputs["Normal"], sp.inputs[0])
    return sp.outputs["X"], sp.outputs["Y"], sp.outputs["Z"]


def spot(c, dirv=(.3, .55, .78), power=6.0):
    """Specular-style highlight mask (0..1) from the world normal."""
    L = Vector(dirv).normalized()
    d = VMATH(c.nt, "DOT_PRODUCT", c.geo.outputs["Normal"], tuple(L))
    return MATH(c.nt, "POWER", MATH(c.nt, "MAXIMUM", d, 0.0), power)


def ellipsoid_mask(c, center, radii, soft=.15):
    """1 inside an ellipsoid (world space), fading to 0 at the surface."""
    nt = c.nt
    d = VMATH(nt, "DIVIDE", VMATH(nt, "SUBTRACT", c.pos, tuple(center)), tuple(radii))
    return SMOOTH(nt, VMATH(nt, "LENGTH", d), 1.0, 1.0 - soft)


def zband(c, lo, hi, w=.004):
    return MATH(c.nt, "MULTIPLY", SMOOTH(c.nt, c.z, lo - w, lo + w), SMOOTH(c.nt, c.z, hi + w, hi - w))


# ================================================================================================= paint recipes
def paint_gloss(name, base, dark=None, light="FFFFFF", hl=.55, var=.1, dots=None, power=5.0, **fin):
    """Shiny painted surface (baubles, ribbons, enamel, glass fruit): soft tone noise + a hot highlight spot.
    dots=(hex, scale) adds polka dots."""
    def r(c):
        nt = c.nt
        col = base
        if var > 0:
            col = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 12.0, 2.0), var), base, dark or "000000")
        if dots:
            d = VORO(nt, c.pos, dots[1], "F1", "Distance")
            col = MIX(nt, SMOOTH(nt, d, .30, .22), col, dots[0])
        col = MIX(nt, MATH(nt, "MULTIPLY", spot(c, power=power), hl), col, light)
        return col
    fin.setdefault("edge", light); fin.setdefault("edge_k", .35); fin.setdefault("edge_r", .006)
    return paint(name, r, **fin)


def paint_plush(name, base="C98A45", dark="8E5A2B", light="E6B471", patches=(), seams=(), thread="5E3A1C", nap=.2, **fin):
    """Plush fur: fine nap noise, soft tufts and faint fur strands.
    patches = [(center, radii, hex)] soft lighter regions (belly, pads) in world space.
    seams = [(x_value, (z_lo, z_hi), y_min)] dashed stitch lines on the plane x = value, front side only."""
    def r(c):
        nt = c.nt
        tuft = NOISE(nt, c.pos, 9.0, 3.0, .55)
        col = RAMP(nt, tuft, [(.3, dark), (.55, base), (.85, light)])
        fine = NOISE(nt, c.pos, 70.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", fine, nap), col, dark)
        strands = WAVE(nt, COORD(nt, scale=(1, 1, 1)), scale=55.0, dist=6.0, detail=2.0, dscale=1.0, direction="Z")
        col = MIX(nt, MATH(nt, "MULTIPLY", strands, .12), col, light)
        for center, radii, hexc in patches:
            m = ellipsoid_mask(c, center, radii, .2)
            pc = MIX(nt, MATH(nt, "MULTIPLY", fine, nap * .7), hexc, "9C7A4E")
            col = MIX(nt, m, col, pc)
        for xv, (zlo, zhi), ymin in seams:
            line = SMOOTH(nt, ABS(nt, MATH(nt, "SUBTRACT", c.x, xv)), .010, .004)
            band = MATH(nt, "MULTIPLY", zband(c, zlo, zhi, .01), SMOOTH(nt, c.y, ymin - .02, ymin + .02))
            crease = MATH(nt, "MULTIPLY", SMOOTH(nt, ABS(nt, MATH(nt, "SUBTRACT", c.x, xv)), .022, .006), band)
            col = MIX(nt, MATH(nt, "MULTIPLY", crease, .35), col, dark)
            dash = FRACT(nt, MATH(nt, "MULTIPLY", c.z, 36.0))
            dash = MATH(nt, "MULTIPLY", SMOOTH(nt, dash, .08, .2), SMOOTH(nt, dash, .62, .5))
            col = MIX(nt, MATH(nt, "MULTIPLY", MATH(nt, "MULTIPLY", line, band), dash), col, thread)
        return col
    return paint(name, r, k_ao=.6, k_light=.4, **fin)


def paint_needles(name, dark="10381C", base="22682E", light="55A43F", tips=(), tip_amt=.35, **fin):
    """Fir foliage: radial needle strokes, clumpy tone, dark undersides, lighter needle tips around each tier rim
    (tips = [(z_rim, r_rim)])."""
    def r(c):
        nt = c.nt
        ang = MATH(nt, "ARCTAN2", c.y, c.x)
        rr = MATH(nt, "SQRT", MATH(nt, "ADD", MATH(nt, "MULTIPLY", c.x, c.x), MATH(nt, "MULTIPLY", c.y, c.y)))
        v = XYZ(nt, MATH(nt, "MULTIPLY", ang, 9.0), MATH(nt, "MULTIPLY", rr, 30.0), MATH(nt, "MULTIPLY", c.z, 30.0))
        strokes = WAVE(nt, v, scale=2.6, dist=2.2, detail=2.0, dscale=1.0, direction="X")
        col = RAMP(nt, strokes, [(.1, dark), (.45, base), (.95, light)])
        v2 = XYZ(nt, MATH(nt, "MULTIPLY", ang, 4.0), MATH(nt, "MULTIPLY", rr, 14.0), MATH(nt, "MULTIPLY", c.z, 14.0))
        strokes2 = WAVE(nt, v2, scale=2.0, dist=3.0, detail=2.0, dscale=1.0, direction="X")
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, strokes2, .55, .9), .45), col, dark)
        clump = NOISE(nt, c.pos, 6.0, 3.0, .6)
        col = MIX(nt, MATH(nt, "MULTIPLY", clump, .4), col, RAMP(nt, clump, [(.3, dark), (.9, light)]))
        fine = NOISE(nt, c.pos, 70.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", fine, .22), col, dark)
        under = SMOOTH(nt, c.nz, .25, -.35)
        col = MIX(nt, MATH(nt, "MULTIPLY", under, .45), col, dark)
        for zr, rrim in tips:
            m = MATH(nt, "MULTIPLY", SMOOTH(nt, ABS(nt, MATH(nt, "SUBTRACT", c.z, zr + .005)), .06, .015),
                     SMOOTH(nt, rr, rrim - .14, rrim - .03))
            m = MATH(nt, "MULTIPLY", m, SMOOTH(nt, strokes, .35, .8))
            col = MIX(nt, MATH(nt, "MULTIPLY", m, tip_amt), col, light)
        return col
    return paint(name, r, k_ao=.72, k_light=.4, edge=light, edge_k=.25, edge_r=.01, **fin)


def paint_brick(name, brick="2B3D66", brick2="1F2E52", brick3="36497C", mortar="121A2E", bh=.065, bw=.15, gap=.008, side=None, **fin):
    """Running-bond brick wall painted in the world XZ plane (for the front/back faces of a panel); side = flat colour for the
    faces that do not look along Y."""
    def r(c):
        nt = c.nt
        col = brick_faces(c)
        if side:
            nx, ny, nz = normal_xyz(c)
            col = MIX(nt, SMOOTH(nt, ABS(nt, ny), .75, .45), col, MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 8.0, 2.0), .2), side, mortar))
        return col

    def brick_faces(c):
        nt = c.nt
        row = MATH(nt, "DIVIDE", c.z, bh)
        ri = FLOOR(nt, row)
        off = MATH(nt, "MULTIPLY", MATH(nt, "MODULO", ri, 2.0), .5)
        colx = MATH(nt, "ADD", MATH(nt, "DIVIDE", c.x, bw), off)
        ci = FLOOR(nt, colx)
        fz = FRACT(nt, row); fx = FRACT(nt, colx)
        gz = gap / bh; gx = gap / bw
        mz = MATH(nt, "MULTIPLY", SMOOTH(nt, fz, gz * .4, gz * 1.1), SMOOTH(nt, fz, 1 - gz * .4, 1 - gz * 1.1))
        mx = MATH(nt, "MULTIPLY", SMOOTH(nt, fx, gx * .4, gx * 1.1), SMOOTH(nt, fx, 1 - gx * .4, 1 - gx * 1.1))
        bm = MATH(nt, "MULTIPLY", mz, mx)
        idn = NOISE(nt, XYZ(nt, MATH(nt, "MULTIPLY", ci, .731), MATH(nt, "MULTIPLY", ri, .377), 0.3), 1.0, 1.0)
        col = RAMP(nt, idn, [(.35, brick2), (.5, brick), (.65, brick3)])
        col = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 45.0, 2.0), .22), col, mortar)
        # rounded brick faces: a little lighter in the middle of each brick
        mid = MATH(nt, "MULTIPLY", SMOOTH(nt, ABS(nt, MATH(nt, "SUBTRACT", fz, .5)), .45, .2), SMOOTH(nt, ABS(nt, MATH(nt, "SUBTRACT", fx, .5)), .47, .25))
        col = MIX(nt, MATH(nt, "MULTIPLY", mid, .18), col, brick3)
        col = MIX(nt, bm, mortar, col)
        return col
    return paint(name, r, k_ao=.55, **fin)


def paint_staves(name, n=20, center=(0, 0), base="B5703B", dark="5E3519", light="D99A58", groove="3A2010", **fin):
    """Oak barrel staves around the vertical axis through `center`: vertical grain, dark joints, each stave a little different."""
    def r(c):
        nt = c.nt
        x = MATH(nt, "SUBTRACT", c.x, center[0]); y = MATH(nt, "SUBTRACT", c.y, center[1])
        ang = MATH(nt, "ARCTAN2", y, x)
        u = MATH(nt, "MULTIPLY", ang, n / (2 * math.pi))
        idx = FLOOR(nt, u); fr = FRACT(nt, u)
        g = MATH(nt, "MULTIPLY", SMOOTH(nt, fr, .0, .07), SMOOTH(nt, fr, 1.0, .93))      # 1 inside a stave, 0 at the joint
        v = XYZ(nt, MATH(nt, "MULTIPLY", u, 2.2), MATH(nt, "MULTIPLY", c.z, 2.0), 0.0)
        grain = WAVE(nt, v, scale=2.6, dist=3.0, detail=2.0, dscale=1.1, direction="X")
        lines = WAVE(nt, v, scale=7.0, dist=2.0, detail=1.0, dscale=1.0, direction="X")
        gg = MATH(nt, "ADD", MATH(nt, "MULTIPLY", grain, .62), MATH(nt, "MULTIPLY", lines, .38))
        col = RAMP(nt, gg, [(.0, dark), (.14, base), (.34, light), (.5, base), (.6, dark), (.68, base), (.88, light), (1, base)])
        tone = NOISE(nt, XYZ(nt, MATH(nt, "MULTIPLY", idx, .53), 0.2, 0.0), 1.0, 1.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", tone, .4), col, light)
        rounded = MATH(nt, "POWER", MATH(nt, "MULTIPLY", ABS(nt, MATH(nt, "SUBTRACT", fr, .5)), 2.0), 2.5)
        col = MIX(nt, MATH(nt, "MULTIPLY", rounded, .3), col, dark)
        col = MIX(nt, MATH(nt, "SUBTRACT", 1.0, g), col, groove)
        return col
    return paint(name, r, edge="E2B57A", edge_k=.5, **fin)


def paint_bottle(name, glass="1E4A2B", glass_d="0D2616", glass_l="6FAE7C", label="F4EFE4", stripe="E0B040", seal="D74A3C",
                 zlab=(.0, .1), zcap="", cap="A3202A", cap_l="D8606A", **fin):
    """Glass bottle: dark glass with a highlight, a paper label band between zlab (gold stripes + a round seal on the front),
    a foil capsule above zcap. World z values (the bottles stand on a known surface)."""
    def r(c):
        nt = c.nt
        col = MIX(nt, MATH(nt, "MULTIPLY", spot(c, power=4.0), .55), glass, glass_l)
        col = MIX(nt, MATH(nt, "MULTIPLY", c.crev, .4), col, glass_d)
        lo, hi = zlab; h = hi - lo
        lab = zband(c, lo, hi, .003)
        lcol = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 60.0, 2.0), .08), label, "C8BFA8")
        st = MATH(nt, "ADD", zband(c, lo + h * .10, lo + h * .20, .002), zband(c, hi - h * .20, hi - h * .10, .002), clamp=True)
        lcol = MIX(nt, st, lcol, stripe)
        nx, ny, nz = normal_xyz(c)
        front = SMOOTH(nt, ny, .55, .9)
        dot = MATH(nt, "MULTIPLY", front, SMOOTH(nt, ABS(nt, MATH(nt, "SUBTRACT", c.z, lo + h * .52)), h * .2, h * .14))
        lcol = MIX(nt, dot, lcol, seal)
        col = MIX(nt, lab, col, lcol)
        if zcap != "":
            capm = SMOOTH(nt, c.z, zcap - .003, zcap + .003)
            ccol = MIX(nt, MATH(nt, "MULTIPLY", spot(c, power=4.0), .6), cap, cap_l)
            ccol = MIX(nt, zband(c, zcap + .004, zcap + .010, .002), ccol, stripe)
            col = MIX(nt, capm, col, ccol)
        return col
    return paint(name, r, k_ao=.45, k_light=.3, edge="9FD3AA", edge_k=.4, edge_r=.004, **fin)


def paint_planks(name, base="C98551", dark="6B4128", light="E6B06A", w=.085, along="X", off=0.0, joint="4A2A14", scale=3.5, dist=3.0, **fin):
    """Wood planks running along `along` (X or Y) with dark joints every `w` metres and a per-plank tone shift."""
    def r(c):
        nt = c.nt
        across = c.y if along == "X" else c.x
        u = MATH(nt, "DIVIDE", MATH(nt, "SUBTRACT", across, off), w)
        idx = FLOOR(nt, u); fr = FRACT(nt, u)
        g = MATH(nt, "MULTIPLY", SMOOTH(nt, fr, .0, .05), SMOOTH(nt, fr, 1.0, .95))
        s = (1, 9, 9) if along == "X" else (9, 1, 9)
        v = COORD(nt, scale=s)
        dr = "Y" if along == "X" else "X"
        grain = WAVE(nt, v, scale=scale, dist=dist, detail=2.0, dscale=1.2, direction=dr)
        lines = WAVE(nt, v, scale=scale * 3.1, dist=dist * .7, detail=1.0, dscale=1.0, direction=dr)
        fine = NOISE(nt, COORD(nt, scale=(40, 40, 40)), 1.0, 2.0)
        gg = MATH(nt, "ADD", MATH(nt, "MULTIPLY", grain, .62), MATH(nt, "ADD", MATH(nt, "MULTIPLY", lines, .26), MATH(nt, "MULTIPLY", fine, .12)))
        col = RAMP(nt, gg, [(.0, dark), (.12, base), (.34, light), (.5, base), (.57, dark), (.62, dark), (.7, base), (.86, light), (1.0, base)])
        tone = NOISE(nt, XYZ(nt, MATH(nt, "MULTIPLY", idx, .61), 0.4, 0.0), 1.0, 1.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", tone, .35), col, light)
        col = MIX(nt, MATH(nt, "SUBTRACT", 1.0, g), col, joint)
        return col
    return paint(name, r, edge="E2B57A", edge_k=.6, **fin)


def paint_gravel(name, cols=("7FD1C8", "F4EFE4", "EE8FAE", "4FB5A8", "E0B040", "C9D2D6", "F6C7D7"), scale=70.0, rim="3F5A66", **fin):
    """Coloured aquarium gravel: voronoi cells each in one of `cols`, darker between the grains."""
    def r(c):
        nt = c.nt
        vn = nt.nodes.new("ShaderNodeTexVoronoi"); vn.feature = "F1"; vn.inputs["Scale"].default_value = scale
        dv4._plug(nt, vn.inputs["Vector"], c.pos)
        sp = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(vn.outputs["Color"], sp.inputs[0])
        stops = [(i / (len(cols) - 1), h) for i, h in enumerate(cols)]
        col = RAMP(nt, sp.outputs[0], stops, "CONSTANT")
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, vn.outputs["Distance"], .3, .55), .55), col, rim)
        col = MIX(nt, MATH(nt, "MULTIPLY", spot(c, power=3.0), .2), col, "FFFFFF")
        return col
    return paint(name, r, k_ao=.6, k_light=.3, **fin)


def paint_fish(name, base="F07A1F", stripe="FFFFFF", stripe_edge="222222", stripes=((.22, .32), (.5, .6), (.8, .88)),
               belly="FFD9A8", belly_amt=.6, **fin):
    """Uses the Paint attribute written by fish(): R = t along the body (0 nose .. 1 tail), G = around (0 top, .5 belly)."""
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        col = base
        bel = SMOOTH(nt, ABS(nt, MATH(nt, "SUBTRACT", s, .5)), .32, .12)
        col = MIX(nt, MATH(nt, "MULTIPLY", bel, belly_amt), col, belly)
        for a, b in stripes:
            e = MATH(nt, "MULTIPLY", SMOOTH(nt, t, a - .035, a - .012), SMOOTH(nt, t, b + .035, b + .012))
            m = MATH(nt, "MULTIPLY", SMOOTH(nt, t, a - .012, a + .008), SMOOTH(nt, t, b + .012, b - .008))
            col = MIX(nt, e, col, stripe_edge); col = MIX(nt, m, col, stripe)
        col = MIX(nt, MATH(nt, "MULTIPLY", spot(c, power=5.0), .35), col, "FFFFFF")
        return col
    return paint(name, r, k_ao=.3, k_light=.3, **fin)


def paint_cabinet(name, base="1D2B4F", dark="101A33", light="34487A", trim="E0B040", panels=((-28, 16), (28, 16)), z=(.09, .47),
                  **fin):
    """Navy round cabinet: raised door panels (angle centre, half width in degrees) outlined in gold, painted around the Z axis."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 6.0, 2.0)
        col = RAMP(nt, mot, [(.3, dark), (.7, base)])
        ang = MATH(nt, "DEGREES", MATH(nt, "ARCTAN2", c.x, c.y))     # 0 at the front (+Y), +x to the right
        for a0, hw in panels:
            da = ABS(nt, MATH(nt, "SUBTRACT", ang, a0))
            inner = MATH(nt, "MULTIPLY", SMOOTH(nt, da, hw, hw - 1.2), zband(c, z[0], z[1], .004))
            outer = MATH(nt, "MULTIPLY", SMOOTH(nt, da, hw + 1.6, hw + .4), zband(c, z[0] - .012, z[1] + .012, .004))
            line = MATH(nt, "SUBTRACT", outer, inner, clamp=True)
            col = MIX(nt, MATH(nt, "MULTIPLY", inner, .7), col, light)
            col = MIX(nt, line, col, trim)
        return col
    return paint(name, r, edge="6A7BA8", edge_k=.5, **fin)


# ================================================================================================= builders
def skirt(name, profile, seg=48, lobes=8, amp=.08, dip=.05, loc=(0, 0, 0), paint=None, out="Body", a0=0.0):
    """Lathe variant for fir-tree tiers: the radius AND the height of the outer rings follow cos(lobes * theta),
    so the branch tips bulge out and droop. profile [(r, z)] from the underside to the top; dip scales with r / r_max."""
    rmax = max(r for r, z in profile)
    bm = bmesh.new(); rings = []
    for r, z in profile:
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            w = math.cos(lobes * (a + a0))
            rr = r * (1 + amp * w) if r > 1e-5 else r
            zz = z - dip * (r / rmax) ** 2 * (w * .5 + .5)
            ring.append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr, zz)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(seg):
            a_, b_ = rings[i][k], rings[i][(k + 1) % seg]
            c_, d_ = rings[i + 1][(k + 1) % seg], rings[i + 1][k]
            try:
                f = bm.faces.new((a_, b_, c_, d_)); f.smooth = True
            except ValueError:
                pass
    if profile[-1][0] > 1e-4:
        bm.faces.new(rings[-1])
    if profile[0][0] > 1e-4:
        bm.faces.new(list(reversed(rings[0])))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return dv4.from_bm(name, bm, paint, out, loc)


def star(name, R, r, depth, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", n=5, **kw):
    """Faceted n-point star in the XZ plane (faces +Y / -Y), raised ridge front and back."""
    bm = bmesh.new(); ring = []
    for i in range(2 * n):
        a = math.pi / 2 + i * math.pi / n
        rr = R if i % 2 == 0 else r
        ring.append(bm.verts.new((math.cos(a) * rr, 0, math.sin(a) * rr)))
    f = bm.verts.new((0, -depth / 2, 0)); b = bm.verts.new((0, depth / 2, 0))
    for i in range(2 * n):
        v1, v2 = ring[i], ring[(i + 1) % (2 * n)]
        bm.faces.new((v1, v2, f)); bm.faces.new((v2, v1, b))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return dv4.from_bm(name, bm, paint, out, loc, rot, smooth=False, **kw)


def helix(z0, z1, r_of_z, turns, n=90, a0=0.0, cx=0.0, cy=0.0):
    pts = []
    for i in range(n + 1):
        t = i / n; z = z0 + (z1 - z0) * t; a = a0 + turns * 2 * math.pi * t; rr = r_of_z(z)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr, z))
    return pts


def bow(name, loc, size=.1, paint=None, out="Body", plane="XZ", thick=.012, rot_z=0.0, tails=True):
    """Ribbon bow: two loops, a knot and two tails. plane 'XZ' = standing (faces +Y), 'XY' = lying flat (seen from above)."""
    cz, sz = math.cos(rad(rot_z)), math.sin(rad(rot_z))
    def P(dx, dy, dz):
        return (loc[0] + dx * cz - dy * sz, loc[1] + dx * sz + dy * cz, loc[2] + dz)
    for s in (-1, 1):
        if plane == "XZ":
            dv4.torus(name + "L%d" % s, size * .42, thick, loc=P(s * size * .5, 0, size * .05), rot=(90, 0, rot_z), seg=12, minor=5,
                      paint=paint, out=out, scale=(1.25, .85, 1))
        else:
            dv4.torus(name + "L%d" % s, size * .42, thick, loc=P(s * size * .5, 0, 0), rot=(0, 0, rot_z), seg=12, minor=5,
                      paint=paint, out=out, scale=(1.25, .8, 1))
    dv4.sphere(name + "K", size * .2, loc=P(0, 0, 0), scale=(1, 1, .85), seg=8, rings=6, paint=paint, out=out)
    if tails:
        for s in (-1, 1):
            if plane == "XZ":
                dv4.cube(name + "T%d" % s, (size * .3, thick * 1.6, size * .9), loc=P(s * size * .22, 0, -size * .42),
                         rot=(0, s * 18, rot_z), paint=paint, out=out, bevel=.004, segs=1)
            else:
                dv4.cube(name + "T%d" % s, (size * .3, size * .9, thick * 1.6), loc=P(s * size * .22, -size * .45, 0),
                         rot=(0, 0, rot_z + s * 18), paint=paint, out=out, bevel=.004, segs=1)


def gift(name, size, loc, box, ribbon, out="Body", rot_z=0.0, bow_size=None):
    """Wrapped present: bevelled box, two ribbon bands and a bow on top (loc = floor centre)."""
    w, d, h = size; t = .007; rw = w * .17
    cz, sz = math.cos(rad(rot_z)), math.sin(rad(rot_z))
    c = (loc[0], loc[1], loc[2] + h / 2)
    dv4.cube(name, size, loc=c, rot=(0, 0, rot_z), paint=box, bevel=.012, segs=2, out=out)
    dv4.cube(name + "R1", (rw, d + 2 * t, h + 2 * t), loc=c, rot=(0, 0, rot_z), paint=ribbon, bevel=.003, segs=1, out=out)
    dv4.cube(name + "R2", (w + 2 * t, rw, h + 2 * t), loc=c, rot=(0, 0, rot_z), paint=ribbon, bevel=.003, segs=1, out=out)
    bow(name + "B", (loc[0], loc[1], loc[2] + h + t * 1.5), size=bow_size or w * .36, paint=ribbon, out=out, plane="XY", rot_z=rot_z)


def fish(name, L=.12, H=.055, W=.03, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, fin_paint=None, out="Body", seg=12, nl=10, rnd=None,
         tail=1.0, dorsal=1.0):
    """Tropical fish swimming along local +Y (nose at +Y), Z up. Body writes the Paint attribute (R = nose..tail, G = around)."""
    bm = bmesh.new()
    lay = bm.loops.layers.color.new("Paint")
    b = RNG.random() if rnd is None else rnd
    rings = []
    for i in range(nl + 1):
        t = i / nl
        rv = H * .5 * max(.03, math.sin(math.pi * t) ** .8) * (1 - .35 * t)       # vertical radius: deep body, thin tail root
        rw = W * .5 * max(.03, math.sin(math.pi * t) ** 1.1)
        y = (0.5 - t) * L
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            v = bm.verts.new((math.sin(a) * rw, y, math.cos(a) * rv + H * .08 * t))
            ring.append(v)
        rings.append(ring)
    for i in range(nl):
        for k in range(seg):
            f = bm.faces.new((rings[i][k], rings[i][(k + 1) % seg], rings[i + 1][(k + 1) % seg], rings[i + 1][k])); f.smooth = True
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    for f in bm.faces:
        for lo in f.loops:
            t = 0.5 - lo.vert.co.y / L
            a = math.atan2(lo.vert.co.x, max(1e-6, lo.vert.co.z - H * .08 * t)) / (2 * math.pi)
            lo[lay] = (min(1, max(0, t)), a % 1.0, b, 1.0)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    body = dv4.from_bm(name, bm, paint, out, loc, rot)
    fp = fin_paint or paint
    # fins are leaves: tail fan (vertical, growing -Y), dorsal (growing +Z), two pectorals
    rz = rot[2]
    def local(dx, dy, dz):
        cz, sz = math.cos(rad(rz)), math.sin(rad(rz))
        return (loc[0] + dx * cz - dy * sz, loc[1] + dx * sz + dy * cz, loc[2] + dz)
    dv4.leaf(name + "Tail", L * .45 * tail, H * 1.05 * tail, loc=local(0, -L * .47, H * .05), rot=(0, 90, 180 + rz), paint=fp, out=out,
             shape="spade", bend=0.0, cup=0.0, twist=0.0, thickness=.003, nl=4, nw=4, rnd=b)
    dv4.leaf(name + "Dorsal", L * .38 * dorsal, H * .5, loc=local(0, L * .02, H * .36), rot=(90, 0, 90 + rz), paint=fp, out=out,
             shape="ellipse", bend=.25, cup=0.0, thickness=.003, nl=4, nw=3, rnd=b)
    for s in (-1, 1):
        dv4.leaf(name + "Pec%d" % s, L * .22, H * .3, loc=local(s * W * .4, L * .12, -H * .05), rot=(0, s * 35, 200 + rz), paint=fp,
                 out=out, shape="ellipse", bend=.1, cup=0.0, thickness=.003, nl=3, nw=3, rnd=b)
    return body


def crate(name, size, loc, paint, rot_z=0.0, out="Body", slats=2):
    """Open wooden crate (floor centre at loc): bottom board, corner posts, horizontal slats on all four sides."""
    w, d, h = size; p = .024; t = .012
    cz, sz = math.cos(rad(rot_z)), math.sin(rad(rot_z))
    def P(dx, dy, dz):
        return (loc[0] + dx * cz - dy * sz, loc[1] + dx * sz + dy * cz, loc[2] + dz)
    dv4.cube(name + "Floor", (w, d, .014), loc=P(0, 0, .007), rot=(0, 0, rot_z), paint=paint, bevel=0, out=out)
    for sx in (-1, 1):
        for sy in (-1, 1):
            dv4.cube(name + "Post", (p, p, h), loc=P(sx * (w / 2 - p / 2), sy * (d / 2 - p / 2), h / 2), rot=(0, 0, rot_z), paint=paint,
                     bevel=.005, segs=2, out=out)
    sh = h * .3
    for i in range(slats):
        z = h * (.28 + .5 * i / max(1, slats - 1)) if slats > 1 else h * .5
        for sy in (-1, 1):
            dv4.cube(name + "SlatY", (w - .004, t, sh), loc=P(0, sy * (d / 2 - t / 2), z), rot=(0, 0, rot_z), paint=paint, bevel=0, out=out)
        for sx in (-1, 1):
            dv4.cube(name + "SlatX", (t, d - .004, sh), loc=P(sx * (w / 2 - t / 2), 0, z), rot=(0, 0, rot_z), paint=paint, bevel=0, out=out)
