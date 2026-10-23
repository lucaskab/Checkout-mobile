"""_lib_C: shared helpers for group C items (claw-machine, atm, vending-machine, photo-booth).
Paint recipes baked into the atlas: enamel, brushed steel, chrome, fur, velvet, sparkle, bright (lit screens / signs).
2D pictogram masks (rect, circle, ring, star, heart, band) addressed in a face plane through plane_uv() so painted
icons sit exactly where the geometry is.  Geometry: rounded panels, star prisms, bulbs, plush toys, cans/bottles/coils,
pleated curtain, Frame (local placement).  install_glass_fix(): faces with the G_Glass override are temporarily split
off and hidden from the bake rays so the glass does not darken the interior AO (wrapper around dv4.bake)."""
import math
import bpy, bmesh
from mathutils import Vector, Matrix, Euler
import dv4
from dv4 import MATH, VMATH, MIX, RAMP, COORD, NOISE, VORO, WAVE, ATTR, SMOOTH, paint, RNG, rad


# ================================================================================================= colours
def shade(h, k):
    return "".join("%02X" % max(0, min(255, int(round(int(h[i:i + 2], 16) * k)))) for i in (0, 2, 4))


def mixhex(a, b, t):
    return "".join("%02X" % int(round(int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t)) for i in (0, 2, 4))


# ================================================================================================= 2D masks
def plane_uv(c, center, right=(1, 0, 0), up=(0, 0, 1)):
    """(u, v) sockets: position in the plane through `center` spanned by right / up (metres)."""
    nt = c.nt
    p = VMATH(nt, "SUBTRACT", c.pos, tuple(center))
    return VMATH(nt, "DOT_PRODUCT", p, tuple(right)), VMATH(nt, "DOT_PRODUCT", p, tuple(up))


def facing(c, d, lo=.6, hi=.9):
    """1 where the surface normal points along d."""
    return SMOOTH(c.nt, VMATH(c.nt, "DOT_PRODUCT", c.geo.outputs["Normal"], tuple(d)), lo, hi)


def shift(nt, u, v, du, dv_):
    return MATH(nt, "SUBTRACT", u, du), MATH(nt, "SUBTRACT", v, dv_)


def band(nt, x, lo, hi, soft=.003):
    return MATH(nt, "MULTIPLY", SMOOTH(nt, x, lo - soft, lo + soft), SMOOTH(nt, x, hi + soft, hi - soft))


def dist(nt, u, v):
    return MATH(nt, "SQRT", MATH(nt, "ADD", MATH(nt, "MULTIPLY", u, u), MATH(nt, "MULTIPLY", v, v)))


def rect(nt, u, v, w, h, r=0.0, soft=.003, cx=0.0, cy=0.0):
    """Rectangle (half sizes w, h) with rounded corners r, centred at (cx, cy)."""
    if cx or cy:
        u, v = shift(nt, u, v, cx, cy)
    if r <= 0:
        return MATH(nt, "MULTIPLY", band(nt, u, -w, w, soft), band(nt, v, -h, h, soft))
    qx = MATH(nt, "SUBTRACT", MATH(nt, "ABSOLUTE", u), w - r); qy = MATH(nt, "SUBTRACT", MATH(nt, "ABSOLUTE", v), h - r)
    px = MATH(nt, "MAXIMUM", qx, 0.0); py = MATH(nt, "MAXIMUM", qy, 0.0)
    d = MATH(nt, "SQRT", MATH(nt, "ADD", MATH(nt, "MULTIPLY", px, px), MATH(nt, "MULTIPLY", py, py)))
    d = MATH(nt, "ADD", d, MATH(nt, "MINIMUM", MATH(nt, "MAXIMUM", qx, qy), 0.0))
    return SMOOTH(nt, d, r + soft, r - soft)


def circle(nt, u, v, r, soft=.003, cx=0.0, cy=0.0):
    if cx or cy:
        u, v = shift(nt, u, v, cx, cy)
    return SMOOTH(nt, dist(nt, u, v), r + soft, r - soft)


def ring(nt, u, v, r0, r1, soft=.003, cx=0.0, cy=0.0):
    if cx or cy:
        u, v = shift(nt, u, v, cx, cy)
    return band(nt, dist(nt, u, v), r0, r1, soft)


def star(nt, u, v, R, k=.5, n=5, soft=.003, cx=0.0, cy=0.0):
    """n-pointed star, outer radius R, inner k*R, one point up."""
    if cx or cy:
        u, v = shift(nt, u, v, cx, cy)
    d = dist(nt, u, v)
    a = MATH(nt, "SUBTRACT", MATH(nt, "ARCTAN2", v, u), math.pi / 2)
    step = 2 * math.pi / n
    m = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", MATH(nt, "MODULO", MATH(nt, "ADD", a, 20 * math.pi + step / 2), step), step / 2))
    rb = MATH(nt, "SUBTRACT", R, MATH(nt, "MULTIPLY", m, (R - k * R) / (step / 2)))
    return SMOOTH(nt, MATH(nt, "SUBTRACT", d, rb), soft, -soft)


def heart(nt, u, v, s, soft=.08, cx=0.0, cy=0.0):
    """Heart of about 2.4*s wide, lobes up."""
    if cx or cy:
        u, v = shift(nt, u, v, cx, cy)
    x = MATH(nt, "DIVIDE", u, s); y = MATH(nt, "DIVIDE", v, s)
    x2 = MATH(nt, "MULTIPLY", x, x); y2 = MATH(nt, "MULTIPLY", y, y)
    g = MATH(nt, "SUBTRACT", MATH(nt, "ADD", x2, y2), 1.0)
    g3 = MATH(nt, "MULTIPLY", g, MATH(nt, "MULTIPLY", g, g))
    f = MATH(nt, "SUBTRACT", g3, MATH(nt, "MULTIPLY", x2, MATH(nt, "MULTIPLY", y2, y)))
    return SMOOTH(nt, f, soft, -soft)


def smile(nt, u, v, r, w=.006, cx=0.0, cy=0.0, soft=.003):
    """Lower half of a ring: a smile."""
    if cx or cy:
        u, v = shift(nt, u, v, cx, cy)
    return MATH(nt, "MULTIPLY", ring(nt, u, v, r - w, r + w, soft), SMOOTH(nt, v, .004, -.004))


def tri_up(nt, u, v, w, h, cx=0.0, cy=0.0, soft=.003):
    """Isosceles triangle, base 2w at v=-h/2, apex at v=+h/2."""
    if cx or cy:
        u, v = shift(nt, u, v, cx, cy)
    t = MATH(nt, "DIVIDE", MATH(nt, "SUBTRACT", h / 2, v), h)       # 1 at base .. 0 at apex
    half = MATH(nt, "MULTIPLY", t, w)
    inside = SMOOTH(nt, MATH(nt, "SUBTRACT", MATH(nt, "ABSOLUTE", u), half), soft, -soft)
    return MATH(nt, "MULTIPLY", inside, band(nt, v, -h / 2, h / 2, soft))


def uni(nt, *masks):
    m = masks[0]
    for k in masks[1:]:
        m = MATH(nt, "MAXIMUM", m, k)
    return m


def cut(nt, a, b):
    return MATH(nt, "MULTIPLY", a, MATH(nt, "SUBTRACT", 1.0, b))


def over(nt, col, mask, hex_):
    return MIX(nt, mask, col, hex_)


def pick(nt, rnd, cols):
    """Per-part random colour from a palette (rnd = Paint attribute B)."""
    n = len(cols)
    return RAMP(nt, rnd, [(i / n, h) for i, h in enumerate(cols)], "CONSTANT")


# ================================================================================================= paints
def paint_enamel(name, base, dark=None, light=None, sheen=.2, speck=.05, edge=None, edge_k=.7, **fin):
    """Glossy painted metal / plastic: soft tone variation, fine speckle, lighter top sheen, light worn edges."""
    dark = dark or shade(base, .72); light = light or mixhex(base, "FFFFFF", .28)
    def r(c):
        nt = c.nt
        col = RAMP(nt, NOISE(nt, c.pos, 2.5, 2.0), [(.3, dark), (.5, base), (.8, light)])
        col = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 140.0, 1.0), speck), col, light)
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .2, 1.0), sheen), col, light)
        return col
    return paint(name, r, edge=edge or light, edge_k=edge_k, edge_r=.008, **fin)


def paint_brushed(name, base="C6CED3", dark="98A2A8", light="EDF2F4", axis="Z", **fin):
    def r(c):
        nt = c.nt
        sc = {"Z": (70, 70, 1.5), "X": (1.5, 70, 70), "Y": (70, 1.5, 70)}[axis]
        streak = NOISE(nt, COORD(nt, scale=sc), 1.0, 2.0, .6)
        col = RAMP(nt, streak, [(.25, dark), (.5, base), (.8, light)])
        col = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 4.0, 2.0), .18), col, dark)
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .1, 1.0), .25), col, light)
        return col
    return paint(name, r, edge="FFFFFF", edge_k=.8, edge_r=.006, **fin)


def paint_chrome(name="Chrome", **fin):
    """Fake chrome: sky-to-ground reflection gradient driven by the normal, dark horizon band, bright edges."""
    def r(c):
        nt = c.nt
        stops = [(0.0, "3C4449"), (.3, "262D32"), (.46, "F4F7F9"), (.58, "AEB9C0"), (.8, "D9E0E4"), (1.0, "F7F9FA")]
        nz01 = MATH(nt, "ADD", MATH(nt, "MULTIPLY", c.nz, .5), .5)
        wob = MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", NOISE(nt, c.pos, 5.0, 2.0), .5), .12)
        return RAMP(nt, MATH(nt, "ADD", nz01, wob), stops)
    return uv_weight(paint(name, r, k_ao=.4, k_light=.25, edge="FFFFFF", edge_k=.6, edge_r=.005, **fin), .7)


def paint_rubber(name="Rubber", base="2F3A40", **fin):
    return uv_weight(dv4.paint_flat(name, base, dark=shade(base, .55), variation=.2, scale=12.0, edge=mixhex(base, "FFFFFF", .3), **fin), .5)


def paint_fur(name, col, dark=None, light=None, **fin):
    dark = dark or shade(col, .7); light = light or mixhex(col, "FFFFFF", .3)
    def r(c):
        nt = c.nt
        base = RAMP(nt, NOISE(nt, c.pos, 7.0, 2.0), [(.3, dark), (.55, col), (.85, light)])
        fuzz = NOISE(nt, c.pos, 110.0, 3.0, .7)
        base = MIX(nt, MATH(nt, "MULTIPLY", fuzz, .3), base, dark)
        rim = MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, -.3, .9), .16)
        return MIX(nt, rim, base, light)
    return uv_weight(cyl_uv(paint(name, r, k_ao=.4, k_light=.3, **fin)), .6)


def paint_velvet(name, base="D74A3C", dark="7E2418", light="F07A66", x0=0.0, width=.56, waves=7, **fin):
    """Pleated curtain: lighter on the bulges, dark in the folds (matches curtain()), fine nap."""
    def r(c):
        nt = c.nt
        ph = MATH(nt, "SINE", MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", c.x, x0), 2 * math.pi * waves / width))
        sh = MATH(nt, "ADD", MATH(nt, "MULTIPLY", ph, .5), .5)
        col = RAMP(nt, sh, [(0.0, dark), (.55, base), (1.0, light)])
        nap = NOISE(nt, c.pos, 60.0, 2.0)
        return MIX(nt, MATH(nt, "MULTIPLY", nap, .18), col, dark)
    return paint(name, r, k_ao=.4, k_light=.35, **fin)


def paint_sparkle(name, base, dot="F4EFE4", scale=30.0, size=.25, amt=.6, keep=.5, **fin):
    """Enamel with scattered little dots (confetti / star dust)."""
    def r(c):
        nt = c.nt
        col = RAMP(nt, NOISE(nt, c.pos, 3.0, 2.0), [(.3, shade(base, .8)), (.55, base), (.85, mixhex(base, "FFFFFF", .15))])
        d = VORO(nt, c.pos, scale, "F1", "Distance")
        kp = SMOOTH(nt, NOISE(nt, c.pos, scale * .5, 1.0), .5 - keep * .2, .5 + (1 - keep) * .2)
        dots = MATH(nt, "MULTIPLY", SMOOTH(nt, d, size, size * .8), kp)
        col = MIX(nt, MATH(nt, "MULTIPLY", dots, amt), col, dot)
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .2, 1.0), .15), col, mixhex(base, "FFFFFF", .3))
        return col
    return paint(name, r, edge=mixhex(base, "FFFFFF", .35), edge_k=.6, edge_r=.008, **fin)


def paint_bright(name, draw, **fin):
    """Lit surfaces (screens, light boxes): no AO, no light, draw(c) -> colour socket."""
    return uv_weight(paint(name, draw, k_ao=0.0, k_light=0.0, **fin), 1.5)


# ================================================================================================= geometry
class Frame:
    """Local placement: p(local) -> world, r(local rot) -> world rot (degrees)."""
    def __init__(self, loc, rot=(0, 0, 0), s=1.0):
        self.m = Euler([rad(a) for a in rot], "XYZ").to_matrix(); self.loc = Vector(loc); self.s = s
    def p(self, q):
        return tuple(self.loc + self.m @ (Vector(q) * self.s))
    def r(self, rot=(0, 0, 0)):
        return tuple(math.degrees(a) for a in (self.m @ Euler([rad(a) for a in rot], "XYZ").to_matrix()).to_euler("XYZ"))


def panel(name, w, h, t=.02, r=.03, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", bevel=.004, n=3, **kw):
    """Rounded-rectangle plate: w along local X, h along local Z, thickness t along local Y (front face = +Y)."""
    bm = bmesh.new()
    r = max(.002, min(r, w * .49, h * .49))
    pts = []
    for i, (sx, sz) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        for k in range(n + 1):
            a = math.radians(i * 90 + 90 * k / n)
            pts.append((sx * (w / 2 - r) + r * math.cos(a), sz * (h / 2 - r) + r * math.sin(a)))
    verts = [bm.verts.new((x, -t / 2, z)) for x, z in pts]
    f = bm.faces.new(verts)
    res = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=(0, t, 0), verts=[g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = dv4.from_bm(name, bm, paint, out, loc, rot, smooth=False, **kw)
    if bevel > 0:
        dv4.mod_bevel(ob, min(bevel, t * .45), 1)
    return ob


def star_prism(name, R, k=.45, t=.015, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", n=5, bevel=.003, **kw):
    """Star plate in the local XZ plane, thickness along Y, one point up."""
    bm = bmesh.new(); pts = []
    for i in range(2 * n):
        a = math.pi / 2 + i * math.pi / n
        rr = R if i % 2 == 0 else R * k
        pts.append(bm.verts.new((math.cos(a) * rr, -t / 2, math.sin(a) * rr)))
    f = bm.faces.new(pts)
    res = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=(0, t, 0), verts=[g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = dv4.from_bm(name, bm, paint, out, loc, rot, smooth=False, **kw)
    if bevel > 0:
        dv4.mod_bevel(ob, min(bevel, t * .45), 1)
    return ob


def bulb(name, loc, r=.018, out="Anim Blink", glow="E_FFE9B0", seg=6, rings=3):
    return dv4.sphere(name, r, loc=loc, seg=seg, rings=rings, paint=None, out=out, mat_override=glow)


def can(name, loc, paint, out="Body", h=.112, r=.03, seg=8, rot=(0, 0, 0)):
    prof = [(0, 0), (r * .8, 0), (r, .008), (r, h - .012), (r * .85, h - .004), (r * .65, h), (0, h)]
    return dv4.lathe(name, prof, seg=seg, loc=loc, rot=rot, paint=paint, out=out)


def bottle(name, loc, paint, out="Body", h=.15, r=.026, seg=8, rot=(0, 0, 0)):
    prof = [(0, 0), (r * .9, 0), (r, .012), (r, h * .52), (r * .5, h * .76), (r * .46, h * .98), (0, h * .98)]
    return dv4.lathe(name, prof, seg=seg, loc=loc, rot=rot, paint=paint, out=out)


def coil(name, center, r=.03, length=.07, turns=1.0, n=7, radius=.0045, paint=None, out="Body"):
    """Vending coil: helix around the +Y axis (toward the customer), starting at center."""
    pts = []
    for i in range(n):
        t = i / (n - 1); a = 2 * math.pi * turns * t
        pts.append((center[0] + r * math.cos(a), center[1] + length * t, center[2] + r * math.sin(a)))
    return dv4.tube(name, pts, radius=radius, res=4, paint=paint, out=out, resolution=2)


def curtain(name, width, height, waves=7, amp=.034, thick=.012, cols=42, rows=5, loc=(0, 0, 0), paint=None, out="Anim Curtain"):
    """Pleated fabric: top edge along +X from the origin (the pivot), hanging down -Z, pleats bulging along Y."""
    bm = bmesh.new(); grid = []
    for i in range(cols + 1):
        t = i / cols; x = width * t
        cf, cb = [], []
        for j in range(rows + 1):
            u = j / rows; z = -height * u
            y = amp * (.55 + .45 * u) * math.sin(2 * math.pi * waves * t) - .01 * u
            cf.append(bm.verts.new((x, y + thick / 2, z))); cb.append(bm.verts.new((x, y - thick / 2, z)))
        grid.append((cf, cb))
    for i in range(cols):
        (f0, b0), (f1, b1) = grid[i], grid[i + 1]
        for j in range(rows):
            bm.faces.new((f0[j], f1[j], f1[j + 1], f0[j + 1])); bm.faces.new((b0[j + 1], b1[j + 1], b1[j], b0[j]))
        bm.faces.new((f0[0], b0[0], b1[0], f1[0])); bm.faces.new((f0[rows], f1[rows], b1[rows], b0[rows]))
    for (f, b) in (grid[0], grid[-1]):
        for j in range(rows):
            bm.faces.new((f[j], f[j + 1], b[j + 1], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return dv4.from_bm(name, bm, paint, out, loc, smooth=True)


# ------------------------------------------------------------------------------------------------- plush toys
def plush(kind, F, fur, P, out="Body", full=True, tag=""):
    """Cute low-poly plush. F = Frame (local: Z up, face toward +Y, ~27 cm tall at s=1).
    P = dict of paints: ink, cream, pink, orange, white, black. full=False builds only body/head/ears/eyes (buried toys)."""
    sp = lambda n, r, q, sc=(1, 1, 1), p=None, seg=8, rings=5, rot=(0, 0, 0): dv4.sphere(
        n + tag, r * F.s, loc=F.p(q), scale=sc, seg=seg, rings=rings, paint=p or fur, out=out, rot=F.r(rot))
    sp("Body", .08, (0, 0, .08), (1, .92, 1.0))
    sp("Head", .07, (0, .01, .195), (1.05, .95, .95))
    for sx in (-1, 1):
        sp("Eye", .011, (sx * .028, .072, .205), seg=5, rings=3, p=P["ink"])
    if kind in ("bear", "panda"):
        for sx in (-1, 1):
            sp("Ear", .028, (sx * .052, -.005, .255), (1, .7, 1), seg=6, rings=3, p=P["black"] if kind == "panda" else fur)
        sp("Muzzle", .028, (0, .066, .178), (1.25, .8, .85), seg=6, rings=4, p=P["cream"])
        sp("Nose", .011, (0, .09, .186), (1.2, .8, .8), seg=5, rings=3, p=P["ink"])
        if kind == "panda":
            for sx in (-1, 1):
                sp("Patch", .022, (sx * .03, .063, .207), (1.0, .5, 1.25), seg=6, rings=3, p=P["black"], rot=(0, sx * 25, 0))
    elif kind == "bunny":
        for sx in (-1, 1):
            sp("Ear", .02, (sx * .03, -.005, .3), (1, .6, 2.8), seg=6, rings=3, rot=(0, sx * 12, 0))
            sp("EarIn", .011, (sx * .03, .008, .3), (1, .4, 2.2), seg=5, rings=3, p=P["pink"], rot=(0, sx * 12, 0))
        sp("Muzzle", .026, (0, .066, .178), (1.3, .8, .8), seg=6, rings=4, p=P["cream"])
        sp("Nose", .009, (0, .088, .19), seg=5, rings=3, p=P["pink"])
    elif kind == "cat":
        for sx in (-1, 1):
            dv4.lathe("Ear" + tag, [(0, 0), (.03 * F.s, 0), (.004 * F.s, .05 * F.s)], seg=6, loc=F.p((sx * .045, 0, .24)),
                      rot=F.r((-12, sx * 22, 0)), paint=fur, out=out)
        sp("Muzzle", .024, (0, .066, .18), (1.4, .8, .7), seg=6, rings=4, p=P["cream"])
        sp("Nose", .009, (0, .088, .19), seg=5, rings=3, p=P["pink"])
    elif kind == "duck":
        sp("Beak", .03, (0, .085, .183), (1.1, 1.0, .45), seg=6, rings=4, p=P["orange"])
        sp("Tuft", .018, (0, -.01, .262), (1, 1, .8), seg=5, rings=3)
    elif kind == "pig":
        for sx in (-1, 1):
            dv4.lathe("Ear" + tag, [(0, 0), (.026 * F.s, 0), (.004 * F.s, .045 * F.s)], seg=6, loc=F.p((sx * .045, 0, .24)),
                      rot=F.r((-20, sx * 30, 0)), paint=fur, out=out)
        dv4.cylinder("Snout" + tag, .022 * F.s, .02 * F.s, loc=F.p((0, .07, .183)), rot=F.r((-90, 0, 0)), seg=8, paint=P["pink"], out=out, bevel=.004)
    elif kind == "frog":
        for sx in (-1, 1):
            sp("Bump", .022, (sx * .036, .028, .252), seg=6, rings=4)
            sp("Eye2", .011, (sx * .036, .045, .256), seg=5, rings=3, p=P["ink"])
        sp("Mouth", .03, (0, .066, .172), (1.5, .6, .5), seg=6, rings=3, p=P["pink"])
    if not full:
        return
    sp("Belly", .05, (0, .045, .075), (1, .6, 1.1), seg=6, rings=4, p=P["cream"] if kind != "panda" else P["white"])
    for sx in (-1, 1):
        sp("Arm", .03, (sx * .085, .02, .11), (1.1, 1, 1.5), seg=6, rings=3, rot=(0, sx * 28, 0), p=P["black"] if kind == "panda" else fur)
        sp("Foot", .035, (sx * .045, .055, .03), (1, 1.3, .8), seg=6, rings=3, p=P["orange"] if kind == "duck" else (P["black"] if kind == "panda" else fur))
        if kind in ("bear", "bunny", "cat", "pig"):
            sp("Blush", .013, (sx * .047, .062, .185), (1, .5, .8), seg=5, rings=3, p=P["pink"])
    if kind == "bunny":
        sp("Tail", .02, (0, -.078, .085), seg=5, rings=3, p=P["cream"])


# ================================================================================================= UV / bake fixes
_installed = False
_temps = []


def cyl_uv(mat):
    """Flag a paint: its parts get ONE cylindrical UV island each (instead of 6-8 smart-project islands per sphere)."""
    mat["dv4_cyl_uv"] = True
    return mat


def _split_overrides(outs):
    """Faces with C_/E_/G_ override materials need no atlas space: split them off (hidden from the bake rays too)."""
    for ob in outs:
        idx = [i for i, m in enumerate(ob.data.materials) if m and m.get("dv4_override")]
        if not idx or not any(p.material_index in idx for p in ob.data.polygons):
            continue
        if all(p.material_index in idx for p in ob.data.polygons):
            continue                                     # a pure override node (bulbs on a Blink node): nothing to split
        dv4._select([ob])
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="DESELECT")
        for i in idx:
            ob.active_material_index = i; bpy.ops.object.material_slot_select()
        bpy.ops.mesh.separate(type="SELECTED"); bpy.ops.object.mode_set(mode="OBJECT")
        g = [o for o in bpy.context.selected_objects if o is not ob][0]
        for k in ("visible_camera", "visible_diffuse", "visible_glossy", "visible_transmission", "visible_shadow", "visible_volume_scatter"):
            setattr(g, k, False)
        _temps.append((ob, g))
        dv4.log("split %d override faces off %s" % (len(g.data.polygons), ob.name))


def uv_weight(mat, w):
    """Texel-density weight for a paint (1 = normal; 1.6 for painted icons, .5 for plain dark parts)."""
    mat["dv4_uv_scale"] = float(w)
    return mat


def _uv_to_metres(ob):
    """Smart project normalises each object to the unit square: rescale so 1 UV unit = 1 metre (same density everywhere)."""
    me = ob.data; uv = me.uv_layers.active.data
    a3 = sum(p.area for p in me.polygons); a2 = 0.0
    for p in me.polygons:
        pts = [uv[li].uv for li in p.loop_indices]
        a2 += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))) * .5
    if a2 <= 1e-12:
        return
    k = math.sqrt(a3 / a2)
    buf = [0.0] * (2 * len(me.loops)); uv.foreach_get("uv", buf)
    uv.foreach_set("uv", [x * k for x in buf])


def _weight_islands(ob):
    """UV islands (faces connected through shared vertex + same UV) are scaled by their material's dv4_uv_scale."""
    me = ob.data
    w = {i: (m.get("dv4_uv_scale") if m else None) for i, m in enumerate(me.materials)}
    if not any(v and abs(v - 1.0) > 1e-3 for v in w.values()):
        return
    uv = me.uv_layers.active.data
    parent = list(range(len(me.polygons)))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    key = {}
    for p in me.polygons:
        for li in p.loop_indices:
            q = uv[li].uv
            k = (me.loops[li].vertex_index, round(q.x * 2e4), round(q.y * 2e4))
            if k in key:
                a, b = find(key[k]), find(p.index)
                if a != b:
                    parent[b] = a
            else:
                key[k] = p.index
    isl = {}
    for p in me.polygons:
        isl.setdefault(find(p.index), []).append(p)
    n = 0
    for polys in isl.values():
        sc = max((w.get(p.material_index) or 1.0) for p in polys)
        if abs(sc - 1.0) < 1e-3:
            continue
        pts = [uv[li].uv for p in polys for li in p.loop_indices]
        cx = sum(q.x for q in pts) / len(pts); cy = sum(q.y for q in pts) / len(pts)
        for q in pts:
            q.x = cx + (q.x - cx) * sc; q.y = cy + (q.y - cy) * sc
        n += 1
    dv4.log("weighted %d of %d UV islands on %s" % (n, len(isl), ob.name))


def _cyl_islands(ob):
    me = ob.data
    cyl = {i for i, m in enumerate(me.materials) if m and m.get("dv4_cyl_uv")}
    if not cyl or "Paint" not in me.color_attributes:
        return
    uv = me.uv_layers.active.data; pa = me.color_attributes["Paint"].data
    groups = {}
    for p in me.polygons:
        if p.material_index in cyl:
            groups.setdefault(round(pa[p.loop_start].color[2], 5), []).append(p)
    for polys in groups.values():
        vids = {v for p in polys for v in p.vertices}
        c = sum((me.vertices[v].co for v in vids), Vector()) / len(vids)
        r = max(1e-3, sum(((me.vertices[v].co - c).xy.length for v in vids)) / len(vids))
        C = 2 * math.pi * r
        for p in polys:
            us, pole = [], []
            for li in range(p.loop_start, p.loop_start + p.loop_total):
                d = me.vertices[me.loops[li].vertex_index].co - c
                if d.xy.length < r * .02:
                    us.append(None); pole.append(li)
                else:
                    us.append(math.atan2(d.y, d.x) / (2 * math.pi) * C)
            good = [u for u in us if u is not None]
            if good and max(good) - min(good) > C * .5:
                us = [None if u is None else (u + C if u < 0 else u) for u in us]
                good = [u for u in us if u is not None]
            mean = sum(good) / len(good) if good else 0.0
            for k, li in enumerate(range(p.loop_start, p.loop_start + p.loop_total)):
                z = me.vertices[me.loops[li].vertex_index].co.z - c.z
                uv[li].uv = (mean if us[k] is None else us[k], z)
    dv4.log("cylindrical UV islands: %d parts" % len(groups))


def install_fix():
    """Wraps dv4.unwrap (split override faces off, cylindrical islands for flagged paints) and dv4.bake (join back).
    Also sets the scene's view transform to Standard so the saved atlas keeps the true paint colours (the factory scene
    saves through AgX, which greys out the whites and desaturates the palette)."""
    global _installed
    try:
        vs = bpy.context.scene.view_settings; vs.view_transform = "Standard"; vs.look = "None"; vs.exposure = 0.0; vs.gamma = 1.0
    except Exception as e:
        dv4.log("view transform:", e)
    if _installed:
        return
    _installed = True
    orig_bake = dv4.bake

    def unwrap(outs, size=1024, bake_margin=4):
        _split_overrides(outs)
        margin = (bake_margin + 3) / size
        pure = [ob for ob in outs if ob.data.materials and all(m and m.get("dv4_override") for m in ob.data.materials)]
        for ob in pure:                       # bulbs on a Blink node: no atlas space, UVs collapsed to a point
            if not ob.data.uv_layers:
                ob.data.uv_layers.new(name="UVMap")
            ob.data.uv_layers.active.data.foreach_set("uv", [0.0] * (2 * len(ob.data.loops)))
            ob["dv4_pure_override"] = True
            dv4.log("no atlas space for pure override node", ob.name)
        outs = [ob for ob in outs if ob not in pure]
        for ob in outs:
            dv4._select([ob])
            if not ob.data.uv_layers:
                ob.data.uv_layers.new(name="UVMap")
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.smart_project(angle_limit=rad(76), island_margin=.003, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
            bpy.ops.object.mode_set(mode="OBJECT")
            _uv_to_metres(ob)
            _cyl_islands(ob)
            _weight_islands(ob)
        dv4._select(outs)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.pack_islands(udim_source="CLOSEST_UDIM", rotate=True, rotate_method="ANY", scale=True, merge_overlap=False,
                                margin_method="FRACTION", margin=margin, shape_method="CONCAVE")
        bpy.ops.object.mode_set(mode="OBJECT")

    def bake(outs, name, size, samples=64):
        try:
            return orig_bake([ob for ob in outs if not ob.get("dv4_pure_override")], name, size, samples)
        finally:
            for ob, g in _temps:
                dv4._select([g, ob], active=ob); bpy.ops.object.join()
            _temps.clear()
    dv4.unwrap = unwrap; dv4.bake = bake


install_glass_fix = install_fix
