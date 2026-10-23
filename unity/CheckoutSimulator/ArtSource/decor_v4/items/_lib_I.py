"""_lib_I: extra paint recipes + geometry helpers for group I (picket-fence, hedge-planter, bird-bath, picnic-table, veggie-garden).
Import from an item script with:
    import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _lib_I as L
"""
import math
import bmesh
from mathutils import Vector
import dv4
from dv4 import MATH, VMATH, MIX, RAMP, COORD, NOISE, VORO, WAVE, ATTR, SMOOTH, paint, RNG


def enc(v):
    """bmesh writes byte colour layers raw (as sRGB bytes) while the Color Attribute node returns them linearised: pre-encode a
    0..1 value so the shader reads it back unchanged."""
    v = max(0.0, min(1.0, v))
    return v * 12.92 if v <= .0031308 else 1.055 * v ** (1 / 2.4) - .055


def AZ(nt, t):
    """Decodes the azimuth stored by _azimuth_attr (R = enc((a + 1) / 3)) back to a (-1..2, continuous across the seam)."""
    return MATH(nt, "SUBTRACT", MATH(nt, "MULTIPLY", t, 3.0), 1.0)


def hexmix(a, b, t):
    """Blend two sRGB hex colours (t = amount of b)."""
    ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return "".join("%02X" % int(round(x + (y - x) * t)) for x, y in zip(ca, cb))


# ================================================================================================= paint recipes
def paint_painted_wood(name="PaintedWood", base="F7F3EB", shade="DCD4C6", wood="C08A4A", wood_dark="7A5230", wear=.5,
                       grime="8C8275", grime_z=.12, along="Z", **fin):
    """Painted planks: brush strokes along `along`, chipped paint showing the wood in crevices / at random spots, grime near the ground."""
    def r(c):
        nt = c.nt
        s = {"X": (1, 7, 7), "Y": (7, 1, 7), "Z": (7, 7, 1)}[along]
        dr = {"X": "Y", "Y": "X", "Z": "X"}[along]
        strokes = WAVE(nt, COORD(nt, scale=s), scale=2.2, dist=3.0, detail=2.0, dscale=1.0, direction=dr)
        col = RAMP(nt, strokes, [(.15, shade), (.55, base), (.95, hexmix(base, "FFFFFF", .5))])
        tone = NOISE(nt, c.pos, 2.5, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", tone, .22), col, shade)
        chips = SMOOTH(nt, NOISE(nt, c.pos, 24.0, 3.0, .6), .70 - wear * .1, .74 - wear * .1)
        chips = MATH(nt, "MULTIPLY", chips, MATH(nt, "ADD", .45, c.crev), clamp=True)
        wcol = RAMP(nt, NOISE(nt, c.pos, 30.0, 2.0), [(.3, wood_dark), (.8, wood)])
        col = MIX(nt, chips, col, wcol)
        if grime_z > 0:
            g = MATH(nt, "MULTIPLY", SMOOTH(nt, c.z, grime_z, .0), MATH(nt, "ADD", .35, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 14.0, 2.0), .65)))
            col = MIX(nt, MATH(nt, "MULTIPLY", g, .4), col, grime)
        return col
    return paint(name, r, edge=wood, edge_k=.55, edge_r=.007, **fin)


def paint_gingham(name="Gingham", a="D74A3C", b="FBF7F0", cell=.055, **fin):
    """Picnic-cloth check in world XY (cell = size of one square)."""
    mid = hexmix(b, a, .5)
    def r(c):
        nt = c.nt
        u = MATH(nt, "LESS_THAN", MATH(nt, "FRACT", MATH(nt, "DIVIDE", c.x, cell)), .5)
        v = MATH(nt, "LESS_THAN", MATH(nt, "FRACT", MATH(nt, "DIVIDE", c.y, cell)), .5)
        s = MATH(nt, "DIVIDE", MATH(nt, "ADD", u, v), 2.0)
        col = RAMP(nt, s, [(0, b), (.4, mid), (.9, a)], "CONSTANT")
        # woven thread texture
        t1 = WAVE(nt, COORD(nt, scale=(1, 1, 1)), scale=160.0, dist=.3, detail=1.0, dscale=1.0, direction="X")
        t2 = WAVE(nt, COORD(nt, scale=(1, 1, 1)), scale=160.0, dist=.3, detail=1.0, dscale=1.0, direction="Y")
        th = MATH(nt, "MULTIPLY", MATH(nt, "ADD", t1, t2), .5)
        col = MIX(nt, MATH(nt, "MULTIPLY", th, .12), col, "000000")
        return col
    return paint(name, r, k_ao=.7, k_light=.3, **fin)


def paint_foliage(name="Foliage", dark="27602A", base="4A9A33", light="8FD04B", cell=70.0, top=.3, clumps=18.0, **fin):
    """Dense small-leaf foliage (boxwood / flower-bed mound): leaf clusters with dark seams, tiny leaf cells, lighter on top."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 3.0, 3.0)
        col = RAMP(nt, mot, [(.25, dark), (.5, base), (.8, light)])
        # leaf clusters: voronoi cells with dark seams between them and a lighter upper side
        seam = SMOOTH(nt, VORO(nt, c.pos, clumps, "DISTANCE_TO_EDGE", "Distance"), .035, .01)
        cl = NOISE(nt, VMATH(nt, "MULTIPLY", VORO(nt, c.pos, clumps, "F1", "Position"), (1, 1, 1)), 1.0, 1.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", cl, .5), col, light)
        col = MIX(nt, MATH(nt, "MULTIPLY", seam, .75), col, dark)
        # tiny individual leaves
        cells = VORO(nt, c.pos, cell, "F1", "Distance")
        cells2 = VORO(nt, COORD(nt, rot=(0, 0, 37)), cell * .6, "F1", "Distance")
        lm = SMOOTH(nt, cells, .45, .15)
        col = MIX(nt, MATH(nt, "MULTIPLY", lm, .55), col, light)
        gaps = MATH(nt, "MAXIMUM", SMOOTH(nt, cells, .6, .85), SMOOTH(nt, cells2, .65, .9))
        col = MIX(nt, MATH(nt, "MULTIPLY", gaps, .7), col, dark)
        tp = SMOOTH(nt, c.nz, -.3, .9)
        col = MIX(nt, MATH(nt, "MULTIPLY", tp, top), col, light)
        return col
    return paint(name, r, k_ao=.55, k_light=.42, **fin)


def paint_bloom(name="Bloom", cols=("EE8FAE", "D74A3C", "FFD97A"), centre="F5C842", calyx="4E8F2E", petals=6, **fin):
    """Flower head made by bloom(): Paint R = azimuth, G = height, B = random. Petal grooves, lighter petal middles, yellow centre."""
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        t = AZ(nt, t)
        n = len(cols)
        col = RAMP(nt, rnd, [(i / n, h) for i, h in enumerate(cols)], "CONSTANT")
        ph = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", MATH(nt, "FRACT", MATH(nt, "MULTIPLY", t, petals)), .5))   # .5 groove .. 0 mid petal
        light = MIX(nt, .45, col, "FFFFFF")
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, ph, .45, .05), .7), col, light)
        dark = MIX(nt, 1.0, col, "9A7A86", "MULTIPLY")
        groove = MATH(nt, "MULTIPLY", SMOOTH(nt, ph, .43, .5), SMOOTH(nt, s, .93, .85))
        col = MIX(nt, groove, col, dark)
        cc = RAMP(nt, NOISE(nt, c.pos, 200.0, 1.0), [(.4, hexmix(centre, "8A5A10", .6)), (.6, centre)])
        col = MIX(nt, SMOOTH(nt, s, .9, .94), col, cc)
        col = MIX(nt, SMOOTH(nt, s, .28, .2), col, calyx)
        return col
    return paint(name, r, k_ao=.4, k_light=.45, **fin)


def paint_fruit(name, base, dark, light, var=.15, **fin):
    """Round fruit / vegetable: mottled base, highlight on top, darker belly, slight per-part variation."""
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        col = RAMP(nt, NOISE(nt, c.pos, 14.0, 2.0), [(.3, dark), (.7, base)])
        col = MIX(nt, MATH(nt, "MULTIPLY", rnd, var), col, light)
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .2, 1.0), .5), col, light)
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, -.1, -1.0), .45), col, dark)
        return col
    return paint(name, r, k_light=.3, **fin)


def paint_metal(name="Metal", base="1F9A8E", dark="156F66", light="7ED3C8", scratch=.25, **fin):
    """Painted sheet metal (watering can, buckets): soft mottle, bright top highlight, fine scratches, light worn edges."""
    def r(c):
        nt = c.nt
        col = RAMP(nt, NOISE(nt, c.pos, 7.0, 2.0), [(.3, dark), (.7, base)])
        hl = SMOOTH(nt, c.nz, .15, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, .35), col, light)
        sc = SMOOTH(nt, WAVE(nt, COORD(nt, scale=(1, 1, 30)), scale=40.0, dist=6.0, detail=2.0, dscale=1.5, direction="Z"), .9, .97)
        col = MIX(nt, MATH(nt, "MULTIPLY", sc, scratch), col, light)
        return col
    return paint(name, r, edge=light, edge_k=1.0, edge_r=.006, **fin)


def paint_wicker(name="Wicker", base="C9955A", dark="8A5E30", light="EBC27E", bands=70.0, stakes=22, **fin):
    """Woven basket: horizontal weaver bands over/under vertical stakes (object is centred on its own axis: see lathe_rz)."""
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)                               # t = azimuth (encoded), s = height 0..1 (from lathe_az)
        t = AZ(nt, t)
        bz = MATH(nt, "MULTIPLY", c.z, bands)
        band = MATH(nt, "FLOOR", bz); fz = MATH(nt, "FRACT", bz)
        u = MATH(nt, "MULTIPLY", t, stakes)
        stake = MATH(nt, "FLOOR", u); fu = MATH(nt, "FRACT", u)
        par = MATH(nt, "LESS_THAN", MATH(nt, "FRACT", MATH(nt, "MULTIPLY", MATH(nt, "ADD", band, stake), .5)), .5)
        col = RAMP(nt, NOISE(nt, c.pos, 20.0, 2.0), [(.3, dark), (.7, base)])
        col = MIX(nt, MATH(nt, "MULTIPLY", par, .5), col, light)
        shade = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", fz, .5))     # 0 band middle .. .5 band edge
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, shade, .32, .5), .8), col, dark)
        shu = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", fu, .5))
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, shu, .36, .5), .45), col, dark)
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, shade, .25, .0), .25), col, light)
        return col
    return paint(name, r, edge=light, edge_k=.5, edge_r=.006, **fin)


def paint_plate(name="Plate", base="F7F2E8", rim="1F9A8E", rim2="E0B040", r0=.78, r1=.9, **fin):
    """Ceramic plate from lathe_rz(): cream glaze with a coloured band on the rim (Paint R = radius fraction)."""
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        col = RAMP(nt, NOISE(nt, c.pos, 10.0, 2.0), [(.3, hexmix(base, "C9BFAE", .4)), (.7, base)])
        band = MATH(nt, "MULTIPLY", SMOOTH(nt, t, r0 - .02, r0 + .02), SMOOTH(nt, t, r1 + .02, r1 - .02))
        col = MIX(nt, band, col, rim)
        thin = MATH(nt, "MULTIPLY", SMOOTH(nt, t, r0 - .1, r0 - .07), SMOOTH(nt, t, r0 - .04, r0 - .07))
        col = MIX(nt, thin, col, rim2)
        hl = SMOOTH(nt, c.nz, .5, 1.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, .2), col, "FFFFFF")
        return col
    return paint(name, r, edge="FFFFFF", edge_k=.5, edge_r=.004, k_light=.3, **fin)


def paint_bird(name, body, belly, wing, **fin):
    """Cute bird: body colour, lighter belly below, darker wing tint (Paint G = height from bird()), feather speckle."""
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        col = RAMP(nt, s, [(.0, belly), (.42, belly), (.5, body), (1.0, body)])
        wm = SMOOTH(nt, t, .4, .9)                                          # t = 1 on the wings (set by bird())
        col = MIX(nt, wm, col, wing)
        fe = SMOOTH(nt, NOISE(nt, c.pos, 120.0, 2.0), .6, .75)
        col = MIX(nt, MATH(nt, "MULTIPLY", fe, .18), col, hexmix(body, "FFFFFF", .5))
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .3, 1.0), .25), col, hexmix(body, "FFFFFF", .35))
        return col
    return paint(name, r, k_ao=.4, k_light=.45, **fin)


def paint_grass(name="Grass", base="4C9A2E", dark="2B6A22", light="A6D858", **fin):
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        col = RAMP(nt, t, [(.0, dark), (.45, base), (1.0, light)])
        col = MIX(nt, MATH(nt, "MULTIPLY", rnd, .3), col, light)
        return col
    return paint(name, r, k_ao=.45, k_light=.4, **fin)


# ================================================================================================= geometry helpers
def prism(name, pts, depth, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", bevel=.006, segs=2, axis="Y", **kw):
    """Extrudes a CCW 2D polygon along `axis` (centred, thickness `depth`). axis "Y": pts are (x, z); axis "X": pts are (y, z);
    axis "Z": pts are (x, y)."""
    bm = bmesh.new()
    h = depth / 2
    front, back = [], []
    for a, b in pts:
        if axis == "Y":
            front.append(bm.verts.new((a, -h, b))); back.append(bm.verts.new((a, h, b)))
        elif axis == "X":
            front.append(bm.verts.new((h, a, b))); back.append(bm.verts.new((-h, a, b)))
        else:
            front.append(bm.verts.new((a, b, h))); back.append(bm.verts.new((a, b, -h)))
    bm.faces.new(front); bm.faces.new(list(reversed(back)))
    n = len(pts)
    for i in range(n):
        bm.faces.new((front[i], back[i], back[(i + 1) % n], front[(i + 1) % n]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = dv4.from_bm(name, bm, paint, out, loc, rot, smooth=False, **kw)
    if bevel > 0:
        dv4.mod_bevel(ob, bevel, segs)
    return ob


def rounded_box_bm(size, r=.1, segs=3, cuts=1):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=bm.verts[:] + bm.edges[:], offset=min(r, min(size) * .49), segments=segs, profile=.5, affect="EDGES",
                    clamp_overlap=True)
    if cuts:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    return bm


def rounded_box(name, size, r=.1, segs=3, cuts=1, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", **kw):
    """Box with big rounded edges and a denser grid (for displaced hedges / cushions)."""
    bm = rounded_box_bm(size, r, segs, cuts)
    return dv4.from_bm(name, bm, paint, out, loc, rot, smooth=True, **kw)


def surface_samples(bm, n, min_dist=.0, top_bias=0.0):
    """n (position, normal) samples on random faces of a bmesh (local coords); top_bias > 0 favours faces with an up normal."""
    faces = list(bm.faces)
    out = []
    tries = 0
    while len(out) < n and tries < n * 40:
        tries += 1
        f = RNG.choice(faces)
        nrm = f.normal
        if top_bias > 0 and RNG.random() < top_bias and nrm.z < .6:
            continue
        vs = [v.co for v in f.verts]
        w = [RNG.random() for _ in vs]; sw = sum(w)
        p = Vector((0, 0, 0))
        for k, v in zip(w, vs):
            p += v * (k / sw)
        if min_dist > 0 and any((p - q).length < min_dist for q, _ in out):
            continue
        out.append((p.copy(), nrm.copy()))
    return out


def _write_attr(bm, fn):
    """fn(loop, face) -> (r, g, b); writes the Paint colour layer."""
    lay = bm.loops.layers.color.new("Paint")
    for f in bm.faces:
        for lo in f.loops:
            r, g, b = fn(lo, f)
            lo[lay] = (enc(r), enc(g), enc(b), 1.0)


def _azimuth_attr(bm, rnd, height_fn):
    """Paint R = azimuth fraction (unwrapped per face so the seam interpolates right), G = height_fn(co), B = rnd."""
    lay = bm.loops.layers.color.new("Paint")
    for f in bm.faces:
        cen = f.calc_center_median()
        fc = (math.atan2(cen.y, cen.x) / (2 * math.pi)) % 1.0
        for lo in f.loops:
            co = lo.vert.co
            a = (math.atan2(co.y, co.x) / (2 * math.pi)) % 1.0 if (abs(co.x) + abs(co.y)) > 1e-6 else fc
            if a - fc > .5:
                a -= 1.0
            elif a - fc < -.5:
                a += 1.0
            lo[lay] = (enc((a + 1.0) / 3.0), enc(height_fn(co)), enc(rnd), 1.0)


def bloom(name, r, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", seg=8, rings=5, flat=.8, rnd=None, **kw):
    """Flower head: a slightly flattened sphere whose Paint attribute drives paint_bloom (R azimuth, G height, B random)."""
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    b = RNG.random() if rnd is None else rnd
    _azimuth_attr(bm, b, lambda co: (co.z / r + 1) * .5)
    bmesh.ops.scale(bm, vec=Vector((1, 1, flat)), verts=bm.verts)
    return dv4.from_bm(name, bm, paint, out, loc, rot, **kw)


def lathe_rz(name, profile, seg=24, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", cap=True, scallop=None, rnd=None, **kw):
    """dv4.lathe + Paint attribute: R = r / rmax (plates), G = z fraction, B = random; azimuth in... no: R is the radius here.
    For wicker (needs azimuth) use lathe_az."""
    bm = dv4.lathe_bm(profile, seg, cap, scallop)
    rmax = max(p[0] for p in profile) or 1.0
    zs = [p[1] for p in profile]; z0, z1 = min(zs), max(zs)
    b = RNG.random() if rnd is None else rnd
    _write_attr(bm, lambda lo, f: (math.hypot(lo.vert.co.x, lo.vert.co.y) / rmax, (lo.vert.co.z - z0) / max(1e-6, z1 - z0), b))
    return dv4.from_bm(name, bm, paint, out, loc, rot, **kw)


def lathe_az(name, profile, seg=24, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", cap=True, scallop=None, rnd=None, **kw):
    """dv4.lathe + Paint attribute: R = azimuth (unwrapped), G = z fraction, B = random (for wicker / stripes)."""
    bm = dv4.lathe_bm(profile, seg, cap, scallop)
    zs = [p[1] for p in profile]; z0, z1 = min(zs), max(zs)
    b = RNG.random() if rnd is None else rnd
    _azimuth_attr(bm, b, lambda co: (co.z - z0) / max(1e-6, z1 - z0))
    return dv4.from_bm(name, bm, paint, out, loc, rot, **kw)


def rotz(p, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2])


def bird(prefix, loc, yaw, paint_body, paint_beak, paint_eye, out="Body", size=1.0, pitch=0.0):
    """A chubby little bird facing local +Y, body centre at `loc`, turned `yaw` degrees. Paint G = height (0 belly .. 1 back),
    R = 1 on the wings. ~600 tris."""
    S = size
    def P(off):
        o = rotz((off[0] * S, off[1] * S, off[2] * S), yaw)
        return (loc[0] + o[0], loc[1] + o[1], loc[2] + o[2])
    def part(name, r, off, scale, seg, rings, wing=0.0, rot=(0, 0, 0), g0=0.0):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r * S)
        bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
        zs = [v.co.z for v in bm.verts]; z0, z1 = min(zs), max(zs)
        lay = bm.loops.layers.color.new("Paint")
        for f in bm.faces:
            for lo in f.loops:
                lo[lay] = (enc(wing), enc(g0 + (1 - g0) * (lo.vert.co.z - z0) / max(1e-6, z1 - z0)), 0.0, 1.0)
        return dv4.from_bm(prefix + name, bm, paint_body, out, P(off), (rot[0] + pitch, rot[1], rot[2] + yaw))
    part("Body", .04, (0, 0, 0), (1, 1.35, 1), 14, 9)
    part("Head", .03, (0, .04, .038), (1, 1, 1), 12, 8, g0=.38)
    part("WingL", .024, (-.032, -.005, .005), (.45, 1.25, .7), 10, 6, wing=1.0, rot=(0, -20, 0))
    part("WingR", .024, (.032, -.005, .005), (.45, 1.25, .7), 10, 6, wing=1.0, rot=(0, 20, 0))
    # tail: a flat fan of feathers
    tail = prism(prefix + "Tail", [(-.012 * S, 0), (.012 * S, 0), (.02 * S, -.055 * S), (0, -.062 * S), (-.02 * S, -.055 * S)], .008 * S,
                 loc=P((0, -.045, .012)), rot=(-18 + pitch, 0, yaw), paint=paint_body, out=out, bevel=.002, axis="Z")
    ca = tail.data.color_attributes.new("Paint", "BYTE_COLOR", "CORNER")
    ca.data.foreach_set("color_srgb", [0.0, 1.0, 0.0, 1.0] * len(tail.data.loops))
    # beak: a little cone pointing forward
    dv4.lathe(prefix + "Beak", [(0, 0), (.009 * S, 0), (.0, .026 * S)], seg=8, loc=P((0, .066, .036)), rot=(-90 + pitch, 0, yaw),
              paint=paint_beak, out=out)
    for sx in (-1, 1):
        dv4.sphere(prefix + "Eye%d" % sx, .0055 * S, loc=P((sx * .02, .058, .046)), seg=8, rings=5, paint=paint_eye, out=out)


def grass_tuft(prefix, loc, paint, out="Body", n=5, L=.09, spread=25.0):
    """A few narrow blades leaning outwards."""
    for i in range(n):
        a = i * 360 / n + RNG.uniform(-20, 20)
        dv4.leaf(prefix + "%d" % i, L * RNG.uniform(.7, 1.2), L * .18, loc=loc, rot=(90 - spread + RNG.uniform(-10, 10), 0, a),
                 paint=paint, out=out, shape="pointed", bend=.25, cup=.2, thickness=.002, nl=3, nw=1)
