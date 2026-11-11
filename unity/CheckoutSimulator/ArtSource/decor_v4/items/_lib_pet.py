"""_lib_pet: shared helpers for the store dog's beds (items/pet-bed-*.py): fabric colourways, cloth paints, cushion geometry,
pictogram masks (paw, bone).
Fabric colourways: every fabric paint is made through fabric(maker) -> dv4.styled(): build() gets the navy paint and returns
cfg["styles"] = STYLES; the runner then re-bakes the atlas with maker(style, palette) for each style (same mesh, same UVs), so
Unity only swaps the albedo:  IK_D4_<Name>_albedo.png (navy), IK_D4_<Name>_albedo_<teal|orange|rose>.png.
Wood, wicker, gold, roof, toys and the cream piping are NOT styled (identical in every colourway)."""
import math
import bpy, bmesh
from mathutils import Vector, Matrix, Euler
import dv4
from dv4 import MATH, VMATH, MIX, RAMP, COORD, NOISE, VORO, WAVE, ATTR, SMOOTH, RNG, paint, rad

DEFAULT = "navy"
STYLES = ["teal", "orange", "rose"]
CREAM, CREAM_D, CREAM_L = "F4EFE4", "CDBFA4", "FFFDF7"
# base = main fabric, dark / light = shading, alt = second fabric (inner cushions), deco = thread / print colour on cream
FAB = {
    "navy":   {"base": "22335C", "dark": "0E1630", "light": "4A6299", "alt": "2D4170", "deco": "22335C"},
    "teal":   {"base": "1F9A8E", "dark": "0E5953", "light": "6CCDBF", "alt": "2DAC9E", "deco": "17786E"},
    "orange": {"base": "DA7B2D", "dark": "8F4517", "light": "F8BB72", "alt": "E69043", "deco": "C2661F"},
    "rose":   {"base": "CD8794", "dark": "8C4C59", "light": "F2C3CB", "alt": "DA9DA8", "deco": "B86F7D"},
}


def hexmix(a, b, t):
    ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]; cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return "".join("%02X" % int(round(x + (y - x) * t)) for x, y in zip(ca, cb))


def fabric(maker):
    """maker(style, pal) -> paint material. Returns the default-style paint, registered for the colourway bakes."""
    return dv4.styled(lambda st: maker(st, FAB[st]), DEFAULT)


def E(x):
    """bmesh byte colour layers are stored as sRGB and read back linear: pre-encode attribute values."""
    x = min(1.0, max(0.0, x))
    return x * 12.92 if x <= .0031308 else 1.055 * x ** (1 / 2.4) - .055


# ================================================================================================= node shorthands
def ADD(nt, a, b): return MATH(nt, "ADD", a, b)
def SUB(nt, a, b): return MATH(nt, "SUBTRACT", a, b)
def MUL(nt, a, b): return MATH(nt, "MULTIPLY", a, b)
def ABS(nt, a): return MATH(nt, "ABSOLUTE", a)
def FRACT(nt, a): return MATH(nt, "FRACT", a)
def FLOOR(nt, a): return MATH(nt, "FLOOR", a)
def MIN(nt, a, b): return MATH(nt, "MINIMUM", a, b)
def MAX(nt, a, b): return MATH(nt, "MAXIMUM", a, b)


def radial(nt, c, cx=0.0, cy=0.0):
    dx, dy = SUB(nt, c.x, cx), SUB(nt, c.y, cy)
    return MATH(nt, "SQRT", ADD(nt, MUL(nt, dx, dx), MUL(nt, dy, dy)))


def uv_rot(nt, a, b, ca, cb, ang):
    """(a, b) relative to (ca, cb), rotated by -ang degrees -> (u, v) sockets."""
    da, db = SUB(nt, a, ca), SUB(nt, b, cb)
    co, si = math.cos(rad(ang)), math.sin(rad(ang))
    return ADD(nt, MUL(nt, da, co), MUL(nt, db, si)), SUB(nt, MUL(nt, db, co), MUL(nt, da, si))


# signed distance fields (metres, < 0 inside) in a 2D (u, v) frame
def sd_circle(nt, u, v, cu, cv, r):
    du, dv = SUB(nt, u, cu), SUB(nt, v, cv)
    return SUB(nt, MATH(nt, "SQRT", ADD(nt, MUL(nt, du, du), MUL(nt, dv, dv))), r)


def sd_ellipse(nt, u, v, cu, cv, ru, rv, ang=0.0):
    a, b = uv_rot(nt, u, v, cu, cv, ang)
    a, b = MATH(nt, "DIVIDE", a, ru), MATH(nt, "DIVIDE", b, rv)
    d = MATH(nt, "SQRT", ADD(nt, MUL(nt, a, a), MUL(nt, b, b)))
    return MUL(nt, SUB(nt, d, 1.0), min(ru, rv))


def sd_rrect(nt, u, v, cu, cv, hw, hh, r, ang=0.0):
    a, b = uv_rot(nt, u, v, cu, cv, ang)
    qa = MAX(nt, SUB(nt, ABS(nt, a), hw - r), 0.0); qb = MAX(nt, SUB(nt, ABS(nt, b), hh - r), 0.0)
    return SUB(nt, MATH(nt, "SQRT", ADD(nt, MUL(nt, qa, qa), MUL(nt, qb, qb))), r)


def sd_union(nt, *ds):
    d = ds[0]
    for x in ds[1:]:
        d = MIN(nt, d, x)
    return d


def sd_paw(nt, u, v, cu, cv, s, ang=0.0):
    """Paw print of overall width ~s; toes point toward +v (after rotating by ang degrees)."""
    a, b = uv_rot(nt, u, v, cu, cv, ang)
    pad = sd_union(nt, sd_ellipse(nt, a, b, 0.0, -.16 * s, .40 * s, .30 * s),
                   sd_ellipse(nt, a, b, -.17 * s, -.30 * s, .20 * s, .17 * s), sd_ellipse(nt, a, b, .17 * s, -.30 * s, .20 * s, .17 * s))
    toes = [sd_ellipse(nt, a, b, x * s, y * s, .135 * s, .175 * s, g) for x, y, g in
            ((-.47, .17, 28), (-.18, .40, 8), (.18, .40, -8), (.47, .17, -28))]
    return sd_union(nt, pad, *toes)


def sd_bone(nt, u, v, cu, cv, L, w, ang=0.0):
    """Cartoon bone: shaft of length L and width w along u (rotated by ang), two round knobs at each end."""
    a, b = uv_rot(nt, u, v, cu, cv, ang)
    k = .62 * w
    return sd_union(nt, sd_rrect(nt, a, b, 0.0, 0.0, L * .5, w * .5, w * .25),
                    *[sd_circle(nt, a, b, sx * L * .5, sy * w * .52, k) for sx in (-1, 1) for sy in (-1, 1)])


def fill(nt, d, soft=.0016):
    return SMOOTH(nt, d, soft, -soft)


def dashes(nt, c, period=.016, duty=.55):
    """0/1 dash pattern that alternates along any direction (rotated checker of sines)."""
    k = 2 * math.pi / period
    s1 = MATH(nt, "SINE", MUL(nt, ADD(nt, MUL(nt, c.x, .8), MUL(nt, c.y, .6)), k))
    s2 = MATH(nt, "SINE", MUL(nt, ADD(nt, MUL(nt, c.y, .8), SUB(nt, c.z, MUL(nt, c.x, .6))), k))
    return SMOOTH(nt, MUL(nt, s1, s2), -.15 + (1 - duty) * .3, .15 + (1 - duty) * .3)


def applique(c, col, d, fill_hex, thread, edge_hex=None, inset=.008, shadow=.35):
    """Sewn-on fabric patch over col: fill inside the sdf d, soft shadow around it, darker hem, dashed stitch line inset."""
    nt = c.nt
    m = fill(nt, d)
    fcol = MIX(nt, MUL(nt, NOISE(nt, c.pos, 60.0, 2.0), .12), fill_hex, edge_hex or hexmix(fill_hex, "000000", .25))
    sh = MUL(nt, MUL(nt, SMOOTH(nt, d, .009, .0), SUB(nt, 1.0, m)), shadow)
    col = MIX(nt, sh, col, "000000")
    col = MIX(nt, m, col, fcol)
    hem = MUL(nt, SMOOTH(nt, d, -.0045, -.0005), m)
    col = MIX(nt, MUL(nt, hem, .3), col, edge_hex or hexmix(fill_hex, "000000", .3))
    line = SMOOTH(nt, ABS(nt, ADD(nt, d, inset)), .0022, .0008)
    col = MIX(nt, MUL(nt, line, dashes(nt, c, .013)), col, thread)
    return col


# ================================================================================================= paints
def paint_cloth(name, pal, tone="base", kind="velvet", decorate=None, sheen=.26, crev=.35, **fin):
    """Upholstery fabric in one palette tone. kind: velvet (nap + sheen), canvas (woven threads), fleece (nubby plush).
    decorate(c, col) -> col adds seams / appliques / prints."""
    base = pal.get(tone, tone)
    dark, light = pal["dark"], pal["light"]

    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 4.5, 3.0, .55)
        col = RAMP(nt, mot, [(.2, hexmix(base, dark, .35)), (.55, base), (.9, hexmix(base, light, .3))])
        if kind == "velvet":
            nap = NOISE(nt, c.pos, 85.0, 2.0)
            col = MIX(nt, MUL(nt, nap, .14), col, dark)
            crush = SMOOTH(nt, NOISE(nt, c.pos, 9.0, 2.0, .5, 1.2), .5, .7)
            col = MIX(nt, MUL(nt, crush, .12), col, light)
        elif kind == "canvas":
            k = 2 * math.pi / .007
            w1 = MATH(nt, "SINE", MUL(nt, ADD(nt, c.x, c.z), k)); w2 = MATH(nt, "SINE", MUL(nt, ADD(nt, c.y, c.z), k))
            col = MIX(nt, MUL(nt, SMOOTH(nt, MUL(nt, w1, w2), -.4, .6), .1), col, dark)
            col = MIX(nt, MUL(nt, NOISE(nt, c.pos, 140.0, 1.0), .1), col, dark)
        else:   # fleece
            nub = VORO(nt, c.pos, 130.0, "F1", "Distance")
            col = MIX(nt, MUL(nt, SMOOTH(nt, nub, .15, .6), .22), col, hexmix(base, light, .5))
            col = MIX(nt, MUL(nt, NOISE(nt, c.pos, 40.0, 3.0), .12), col, dark)
        hl = MUL(nt, SMOOTH(nt, c.nz, .3, .97), sheen)
        col = MIX(nt, hl, col, light)
        col = MIX(nt, MUL(nt, c.crev, crev), col, dark)
        if decorate:
            col = decorate(c, col)
        return col
    return paint(name, r, k_ao=.55, k_light=.32, **fin)


def paint_cord(name="Piping", base=CREAM, dark=CREAM_D, light=CREAM_L, pitch=.009, **fin):
    """Twisted piping cord: diagonal twist lines, light on top."""
    def r(c):
        nt = c.nt
        tw = FRACT(nt, MATH(nt, "DIVIDE", ADD(nt, ADD(nt, c.x, c.y), MUL(nt, c.z, 1.7)), pitch))
        col = MIX(nt, MUL(nt, SMOOTH(nt, ABS(nt, SUB(nt, tw, .5)), .32, .5), .45), base, dark)
        col = MIX(nt, MUL(nt, SMOOTH(nt, c.nz, .2, .95), .4), col, light)
        return col
    return paint(name, r, k_ao=.5, k_light=.3, **fin)


def paint_gilt(name="Gilt", base="E2B13F", dark="B8842A", light="FFE89A", **fin):
    """Gold-leaf paint for carved furniture: soft even tone (no blotches), warm darker crevices, bright tops and edges."""
    def r(c):
        nt = c.nt
        col = MIX(nt, MUL(nt, NOISE(nt, c.pos, 18.0, 2.0), .14), base, dark)
        col = MIX(nt, MUL(nt, NOISE(nt, c.pos, 90.0, 1.0), .06), col, light)
        col = MIX(nt, MUL(nt, c.crev, .55), col, "8A5E14")
        L = Vector((.3, .5, .8)).normalized()
        spot = MATH(nt, "POWER", MAX(nt, VMATH(nt, "DOT_PRODUCT", c.geo.outputs["Normal"], tuple(L)), 0.0), 4.0)
        return MIX(nt, MUL(nt, spot, .45), col, light)
    fin.setdefault("edge", light); fin.setdefault("edge_k", .9); fin.setdefault("edge_r", .005)
    return paint(name, r, k_ao=.45, k_light=.3, **fin)


def paint_rubber_toy(name="Toy", base="D74A3C", dark="8E2A20", light="FF9C8A", **fin):
    """Glossy chew toy: tone noise, tiny bite dents, a hot highlight."""
    def r(c):
        nt = c.nt
        col = MIX(nt, MUL(nt, NOISE(nt, c.pos, 14.0, 2.0), .25), base, dark)
        dent = SMOOTH(nt, VORO(nt, c.pos, 45.0, "F1", "Distance"), .12, .02)
        col = MIX(nt, MUL(nt, dent, .25), col, dark)
        L = Vector((.3, .55, .78)).normalized()
        spot = MATH(nt, "POWER", MAX(nt, VMATH(nt, "DOT_PRODUCT", c.geo.outputs["Normal"], tuple(L)), 0.0), 6.0)
        return MIX(nt, MUL(nt, spot, .6), col, light)
    return paint(name, r, k_ao=.45, k_light=.3, edge=light, edge_k=.4, edge_r=.004, **fin)


# ================================================================================================= geometry
def loft(name, rings, paint=None, out="Body", cap0=False, cap1=False, wrap=False, closed=True, smooth=True, attr=None, loc=(0, 0, 0),
         rot=(0, 0, 0), **kw):
    """Skin through rings (lists of (x, y, z) of equal length, closed loops unless closed=False; a ring of length 1 is a pole).
    wrap = connect the last ring back to the first (torus). attr(i, k) -> (R, G) writes the Paint attribute (B = random);
    k runs 0..n (k == n is the closing seam of a closed loop)."""
    bm = bmesh.new()
    lay = bm.loops.layers.color.new("Paint") if attr else None
    b = RNG.random()
    vs = [[bm.verts.new(p) for p in ring] for ring in rings]
    pairs = [(i, i + 1) for i in range(len(vs) - 1)] + ([(len(vs) - 1, 0)] if wrap else [])
    for i, j in pairs:
        A, B = vs[i], vs[j]
        n = max(len(A), len(B))
        for k in range(n if closed else n - 1):
            k2 = (k + 1) % n
            if len(B) == 1:
                quad = (A[k], A[k2], B[0]); idx = ((i, k), (i, k + 1), (j, 0))
            elif len(A) == 1:
                quad = (A[0], B[k2], B[k]); idx = ((i, 0), (j, k + 1), (j, k))
            else:
                quad = (A[k], A[k2], B[k2], B[k]); idx = ((i, k), (i, k + 1), (j, k + 1), (j, k))
            try:
                f = bm.faces.new(quad)
            except ValueError:
                continue
            f.smooth = smooth
            if lay:
                for lo, (ii, kk) in zip(f.loops, idx):
                    R, G = attr(ii, kk)
                    lo[lay] = (E(R), E(G), b, 1.0)
    if cap0 and len(vs[0]) > 2:
        f = bm.faces.new(list(reversed(vs[0]))); f.smooth = False
    if cap1 and len(vs[-1]) > 2:
        f = bm.faces.new(vs[-1]); f.smooth = False
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return dv4.from_bm(name, bm, paint, out, loc, rot, **kw)


def oval_pts(rx, ry, seg=48, a0=0.0):
    """Ellipse outline [(x, y, nx, ny)] CCW from +X (a0 degrees), with outward normals."""
    pts = []
    for k in range(seg):
        a = rad(a0) + 2 * math.pi * k / seg
        n = Vector((math.cos(a) / rx, math.sin(a) / ry)).normalized()
        pts.append((rx * math.cos(a), ry * math.sin(a), n.x, n.y))
    return pts


def rrect_pts(w, d, r, cseg=4, nx=4, ny=3):
    """Rounded rectangle outline [(x, y, nx, ny)] CCW, straight sides cut into nx (along X) / ny (along Y) segments."""
    hw, hd = w / 2 - r, d / 2 - r
    cs = ((hw, hd, 0), (-hw, hd, 90), (-hw, -hd, 180), (hw, -hd, 270))
    pts = []
    for ci, (cx, cy, a0) in enumerate(cs):
        for k in range(cseg + 1):
            a = rad(a0 + 90.0 * k / cseg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a), math.cos(a), math.sin(a)))
        ncx, ncy, na0 = cs[(ci + 1) % 4]
        a = rad(a0 + 90.0)
        p0 = (cx + r * math.cos(a), cy + r * math.sin(a)); p1 = (ncx + r * math.cos(a), ncy + r * math.sin(a))
        n = nx if ci in (0, 2) else ny
        for j in range(1, n):
            t = j / n
            pts.append((p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t, math.cos(a), math.sin(a)))
    return pts


def ring_at(outline, off, z, k=1.0):
    """3D loop: the outline pushed out by `off` along its normals (and scaled by k) at height z."""
    return [((x + nx * off) * k, (y + ny * off) * k, z) for x, y, nx, ny in outline]


def cushion_profile(h, e, bulge):
    return [(-e * .8, 0.0), (-e * .35, e * .1), (-e * .07, e * .42), (bulge, h * .5), (-e * .07, h - e * .42), (-e * .35, h - e * .1),
            (-e * .8, h)]


def cushion(name, outline, h, z0=0.0, e=.03, bulge=.008, puff=.02, inner=(.84, .62, .36), paint=None, out="Body", loc=(0, 0, 0),
            rot=(0, 0, 0), dome=None, bottom=True, **kw):
    """Plump cushion on an outline centred at the local origin: bulging sides, rounded edges, a domed top (puff).
    dome(x, y) -> extra height (optional dents / tufts). bottom=False leaves the (hidden) bottom open: no atlas space."""
    rings = [ring_at(outline, o, z0 + z) for o, z in cushion_profile(h, e, bulge)]
    top = rings[-1]
    for f in inner:
        ring = []
        for x, y, z in top:
            px, py = x * f, y * f
            ring.append((px, py, z0 + h + puff * (1 - f * f) + (dome(px, py) if dome else 0.0)))
        rings.append(ring)
    rings.append([(0.0, 0.0, z0 + h + puff + (dome(0.0, 0.0) if dome else 0.0))])
    return loft(name, rings, paint, out, cap0=bottom, loc=loc, rot=rot, **kw)


def disc(name, r, h, z0=0.0, seg=40, e=.006, paint=None, out="Body", loc=(0, 0, 0), **kw):
    """Thin base disc without a bottom face (sits on the floor)."""
    rings = []
    for rr, z in ((r, 0.0), (r, h - e), (r - e * .7, h)):
        rings.append([(rr * math.cos(2 * math.pi * k / seg), rr * math.sin(2 * math.pi * k / seg), z0 + z) for k in range(seg)])
    rings.append([(0.0, 0.0, z0 + h)])
    return loft(name, rings, paint, out, loc=loc, **kw)


def cushion_edge(outline, h, z0=0.0, e=.03, top=True):
    """Points of the piping seam around a cushion() (top or bottom rounded edge)."""
    z = z0 + (h - e * .2 if top else e * .2)
    return ring_at(outline, -e * .2, z)


def piping(name, pts, r=.0065, paint=None, sides=6, out="Body", cyclic=True):
    return dv4.tube(name, pts, radius=r, res=sides, paint=paint, out=out, cyclic=cyclic, kind="POLY", resolution=1)


def mark():
    return len(dv4.PARTS)


def place(i0, loc=(0, 0, 0), rot=(0, 0, 0)):
    """Moves every part created since mark() == i0 by the transform (loc, rot degrees XYZ), about the world origin."""
    bpy.context.view_layer.update()
    M = Matrix.Translation(Vector(loc)) @ Euler([rad(a) for a in rot], "XYZ").to_matrix().to_4x4()
    for ob in dv4.PARTS[i0:]:
        ob.matrix_world = M @ ob.matrix_world
    bpy.context.view_layer.update()


def rsec(phi, a, b, n=2.4):
    """Rounded-square cross-section point (superellipse) for angle phi: (horizontal, vertical) offsets."""
    c, s = math.cos(phi), math.sin(phi)
    return a * math.copysign(abs(c) ** (2 / n), c), b * math.copysign(abs(s) ** (2 / n), s)


def bone_toy(name, loc, L=.14, r=.017, knob=.024, rot_z=0.0, paint=None, out="Body"):
    """Rubber chew bone lying flat: a shaft and two knobs at each end (loc = floor point under its centre)."""
    i0 = mark()
    dv4.tube(name + "Shaft", [(-L / 2, 0, 0), (L / 2, 0, 0)], radius=r, res=8, paint=paint, out=out, kind="POLY", resolution=1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            dv4.sphere(name + "Knob", knob, loc=(sx * L / 2, sy * knob * .62, 0), seg=10, rings=7, paint=paint, out=out)
    place(i0, (loc[0], loc[1], loc[2] + knob * .92), (0, 0, rot_z))
