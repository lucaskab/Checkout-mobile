"""_lib_D: extra paint recipes + geometry helpers for group D (cart-corral, flower-stand, coffee-kiosk, festoon-pergola).
Import from an item script:  sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _lib_D as L
"""
import math
import bpy, bmesh
from mathutils import Vector
import dv4
from dv4 import N, MATH, VMATH, MIX, RAMP, COORD, NOISE, VORO, WAVE, ATTR, SMOOTH, RNG, rad


# ================================================================================================= paints
def paint_chrome(name="Chrome", light="F2F5F7", mid="A3AEB6", dark="3A454D", sky="C2D4DE", floor="737E86", k_ao=.5, k_light=.25, **fin):
    """Stylised polished steel: bright sky reflection on upward faces, dark horizon band, mid floor reflection below."""
    def r(c):
        nt = c.nt
        nz01 = MATH(nt, "ADD", MATH(nt, "MULTIPLY", c.nz, .5), .5)
        col = RAMP(nt, nz01, [(0.0, floor), (.28, mid), (.4, dark), (.5, dark), (.56, light), (.74, sky), (1.0, light)])
        streak = NOISE(nt, COORD(nt, scale=(3, 3, 30)), 2.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", streak, .2), col, mid)
        # a second dark reflection band on the lower side (reads as a real tube)
        band2 = SMOOTH(nt, MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", nz01, .16)), .08, .02)
        col = MIX(nt, MATH(nt, "MULTIPLY", band2, .5), col, dark)
        return col
    return dv4.paint(name, r, edge=light, edge_k=.9, edge_r=.006, k_ao=k_ao, k_light=k_light, **fin)


def paint_plastic(name, base, light=None, dark=None, gloss=.45, **fin):
    """Glossy coloured plastic: soft top highlight, darker underside, tiny speckle."""
    light = light or _lighten(base, .45); dark = dark or _lighten(base, -.35)
    def r(c):
        nt = c.nt
        nz01 = MATH(nt, "ADD", MATH(nt, "MULTIPLY", c.nz, .5), .5)
        col = RAMP(nt, nz01, [(.0, dark), (.45, base), (.85, light)])
        hl = SMOOTH(nt, c.nz, .55, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, gloss), col, "FFFFFF")
        spk = NOISE(nt, c.pos, 70.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", spk, .08), col, dark)
        return col
    return dv4.paint(name, r, edge=light, edge_k=.6, edge_r=.006, **fin)


def paint_zinc(name="Zinc", base="B9C2C6", light="E2E8EA", dark="7E8A90", spangle=.35, **fin):
    """Galvanised bucket: voronoi spangles, soft vertical highlight, dark seams in crevices."""
    def r(c):
        nt = c.nt
        cell = VORO(nt, c.pos, 22.0, "F1", "Color")
        sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(cell, sep.inputs[0])
        col = RAMP(nt, sep.outputs[0], [(.1, dark), (.5, base), (.95, light)])
        col = MIX(nt, 1.0 - spangle, col, base)
        nz01 = MATH(nt, "ADD", MATH(nt, "MULTIPLY", c.nz, .5), .5)
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, nz01, .5, 1.0), .35), col, light)
        ang = MATH(nt, "ARCTAN2", c.y, c.x)
        band = SMOOTH(nt, MATH(nt, "COSINE", MATH(nt, "MULTIPLY", ang, 1.0)), .3, .9)
        col = MIX(nt, MATH(nt, "MULTIPLY", band, .25), col, light)
        return col
    return dv4.paint(name, r, edge=light, edge_k=.8, edge_r=.006, **fin)


def paint_kraft(name="Kraft", base="C9A26E", dark="A7824F", light="E0C294", dots=None, dot_scale=28.0, **fin):
    """Kraft wrapping paper (fibre noise, soft creases); dots=hex adds polka dots."""
    def r(c):
        nt = c.nt
        fib = NOISE(nt, COORD(nt, scale=(60, 60, 8)), 1.0, 2.0)
        col = RAMP(nt, fib, [(.3, dark), (.55, base), (.85, light)])
        crease = SMOOTH(nt, NOISE(nt, c.pos, 6.0, 2.0), .58, .64)
        col = MIX(nt, MATH(nt, "MULTIPLY", crease, .45), col, dark)
        if dots:
            d = VORO(nt, c.pos, dot_scale, "F1", "Distance")
            col = MIX(nt, SMOOTH(nt, d, .3, .22), col, dots)
        return col
    return dv4.paint(name, r, edge=light, edge_k=.5, edge_r=.004, **fin)


def paint_stripes(name="Awning", a="EC862E", b="F4EFE4", width=.18, along="X", k_ao=.5, k_light=.3, **fin):
    """Striped canvas (stripes perpendicular to `along`), with cloth weave and sun fade."""
    def r(c):
        nt = c.nt
        u = {"X": c.x, "Y": c.y, "Z": c.z}[along]
        f = MATH(nt, "FRACT", MATH(nt, "DIVIDE", u, width))
        m = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", f, .5))
        st = SMOOTH(nt, m, .255, .245)
        col = MIX(nt, st, a, b)
        weave = NOISE(nt, COORD(nt, scale=(120, 120, 120)), 1.0, 1.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", weave, .12), col, "6B4B2E")
        fade = NOISE(nt, c.pos, 1.5, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", fade, .12), col, "FFF4E0")
        return col
    return dv4.paint(name, r, k_ao=k_ao, k_light=k_light, **fin)


def paint_chalkboard(name="Chalkboard", base="26342F", dark="18221E", **fin):
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 8.0, 3.0)
        col = RAMP(nt, mot, [(.3, dark), (.7, base)])
        dust = NOISE(nt, c.pos, 40.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, dust, .55, .75), .18), col, "8A948F")
        return col
    return dv4.paint(name, r, k_ao=.4, k_light=.2, **fin)


def paint_marble(name="Marble", base="F1EBE0", vein="B9AE9E", vein2="D8CFC2", **fin):
    def r(c):
        nt = c.nt
        v = SMOOTH(nt, NOISE(nt, c.pos, 2.0, 4.0, .6, 2.0), .47, .5)
        v2 = SMOOTH(nt, NOISE(nt, COORD(nt, scale=(1, 1, 1), rot=(0, 0, 40)), 3.5, 3.0, .6, 1.5), .48, .505)
        col = MIX(nt, MATH(nt, "MULTIPLY", v, .7), base, vein)
        col = MIX(nt, MATH(nt, "MULTIPLY", v2, .5), col, vein2)
        mot = NOISE(nt, c.pos, 12.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, .08), col, vein2)
        return col
    return dv4.paint(name, r, edge="FFFFFF", edge_k=.5, edge_r=.006, **fin)


def paint_petal(name, base, tip=None, center=None, dark=None, k_ao=.45, k_light=.4, **fin):
    """Flower petal / head: uses the Paint attribute R (0 = base/centre .. 1 = tip), B = per-flower random."""
    tip = tip or _lighten(base, .35); center = center or _lighten(base, -.3); dark = dark or _lighten(base, -.45)
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        col = RAMP(nt, t, [(0.0, center), (.4, base), (1.0, tip)])
        col = MIX(nt, MATH(nt, "MULTIPLY", rnd, .25), col, tip)
        sc = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", s, .5))
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, sc, .3, .5), .2), col, dark)
        vein = SMOOTH(nt, NOISE(nt, c.pos, 30.0, 2.0), .6, .7)
        col = MIX(nt, MATH(nt, "MULTIPLY", vein, .12), col, dark)
        return col
    return dv4.paint(name, r, edge=tip, edge_k=.4, edge_r=.004, k_ao=k_ao, k_light=k_light, **fin)


def paint_seeds(name="Seeds", base="4A2E14", light="8A5B2A", **fin):
    def r(c):
        nt = c.nt
        d = VORO(nt, c.pos, 120.0, "F1", "Distance")
        col = RAMP(nt, d, [(.1, light), (.5, base)])
        t, s, rnd = ATTR(nt)
        col = MIX(nt, MATH(nt, "MULTIPLY", t, .5), col, "C08A3A")      # lighter ring near the edge (R = radial)
        return col
    return dv4.paint(name, r, k_ao=.6, k_light=.3, **fin)


def paint_glass_fake(name="Vitrine", base="DCEFF6", light="FFFFFF", **fin):
    """Opaque 'glass' for the atlas: pale cyan with a diagonal highlight streak (use G_Glass override when real glass is wanted)."""
    def r(c):
        nt = c.nt
        d = MATH(nt, "ADD", c.x, c.z)
        hl = SMOOTH(nt, MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", MATH(nt, "FRACT", MATH(nt, "MULTIPLY", d, 2.0)), .5)), .25, .12)
        return MIX(nt, MATH(nt, "MULTIPLY", hl, .5), base, light)
    return dv4.paint(name, r, k_ao=.2, k_light=.2, **fin)


def _lighten(hexcol, amt):
    c = [int(hexcol[i:i + 2], 16) for i in (0, 2, 4)]
    if amt >= 0:
        c = [int(v + (255 - v) * amt) for v in c]
    else:
        c = [int(v * (1 + amt)) for v in c]
    return "%02X%02X%02X" % tuple(max(0, min(255, v)) for v in c)


# ================================================================================================= attribute tagging
def tag(ob, mode="z", rnd=None, radial_max=None):
    """Writes the Paint attribute from LOCAL mesh coordinates before realize(): R = height 0..1 (mode 'z') or radial 0..1
    (mode 'r'), G = angle 0..1, B = per-part random. Lets paint_petal / paint_seeds grade a lathe flower head."""
    me = ob.data
    if not hasattr(me, "loops"):
        return ob
    if "Paint" in me.color_attributes:
        me.color_attributes.remove(me.color_attributes["Paint"])
    ca = me.color_attributes.new("Paint", "BYTE_COLOR", "CORNER")
    b = RNG.random() if rnd is None else rnd
    zs = [v.co.z for v in me.vertices]; z0, z1 = min(zs), max(zs)
    rs = [math.hypot(v.co.x, v.co.y) for v in me.vertices]; r1 = radial_max or max(rs) or 1.0
    vals = []
    for lo in me.loops:
        v = me.vertices[lo.vertex_index].co
        if mode == "z":
            t = (v.z - z0) / (z1 - z0) if z1 > z0 else 0.0
        else:
            t = min(1.0, math.hypot(v.x, v.y) / r1)
        s = (math.atan2(v.y, v.x) / (2 * math.pi)) % 1.0
        vals += [t, s, b, 1.0]
    ca.data.foreach_set("color_srgb", vals)
    return ob


# ================================================================================================= geometry
def wire(name, p0, p1, r=.004, paint=None, out="Body", res=5):
    """Straight thin bar (open ends, 4 sides) for wire baskets / strings."""
    return dv4.tube(name, [p0, p1], radius=r, res=res, paint=paint, out=out, kind="POLY", resolution=1)


def bar(name, pts, r=.01, paint=None, out="Body", res=6):
    """Polyline bar (open ends)."""
    return dv4.tube(name, pts, radius=r, res=res, paint=paint, out=out, kind="POLY", resolution=1)


def catenary(p0, p1, sag, n=12):
    """Points hanging between p0 and p1 with the given sag (parabola, fine for festoons)."""
    pts = []
    for i in range(n + 1):
        t = i / n
        x = p0[0] + (p1[0] - p0[0]) * t; y = p0[1] + (p1[1] - p0[1]) * t
        z = p0[2] + (p1[2] - p0[2]) * t - sag * 4 * t * (1 - t)
        pts.append((x, y, z))
    return pts


def disc(name, r, t, loc, paint=None, out="Body", seg=16, rot=(0, 0, 0), **kw):
    """Flat round plate (for pictograms, bases)."""
    return dv4.cylinder(name, r, t, loc=loc, rot=rot, seg=seg, paint=paint, out=out, **kw)


def ring(name, R, r, loc, paint=None, out="Body", seg=20, minor=6, rot=(0, 0, 0), arc=360.0):
    return dv4.torus(name, R, r, loc=loc, rot=rot, seg=seg, minor=minor, paint=paint, out=out, arc=arc)


def plank_box(name, size, loc, paint, rot=(0, 0, 0), bevel=.008, out="Body"):
    return dv4.cube(name, size, loc=loc, rot=rot, paint=paint, bevel=bevel, segs=2, out=out)


def bucket(name, loc, r=.09, h=.24, paint=None, out="Body", seg=14, handle=None, rim=True):
    """Tapered zinc bucket with a rolled rim and a wire handle (resting on the side)."""
    rb = r * .78
    prof = [(0, 0), (rb, 0), (r * .98, h - .022), (r + .012, h), (r * .55, h - .035), (0, h - .04)]
    ob = dv4.lathe(name, prof, seg=seg, loc=loc, paint=paint, out=out)
    if rim:
        dv4.torus(name + "Rim", r * .97, .007, loc=(loc[0], loc[1], loc[2] + h * .45), seg=seg, minor=5, paint=paint, out=out)
    if handle is not None:
        a = handle
        pts = []
        for k in range(7):
            b = math.pi * k / 6
            pts.append((loc[0] + math.cos(a) * (r + .01) * math.cos(b), loc[1] + math.sin(a) * (r + .01) * math.cos(b), loc[2] + h - .01 + math.sin(b) * r * 1.1))
        dv4.tube(name + "Handle", pts, radius=.005, res=5, paint=paint, out=out, resolution=1, kind="POLY")
    return ob


def ballast(name, out, p0, p1, paint, r=.003):
    """UV ballast: dv4.unwrap normalises every output object into 0..1 before packing, so an Anim node whose biggest island is a
    3 cm bulb would take as much atlas as the whole Body. A long thin hidden wire in the node (as long as the Body's biggest
    part) restores the balance. Hide it inside solid geometry."""
    return dv4.tube(name, [p0, p1], radius=r, res=5, paint=paint, out=out, kind="POLY", resolution=1)


# ------------------------------------------------------------------------------------------------- flowers (mobile-cheap heads)
def stem(name, p0, p1, paint, out, r=.004):
    return dv4.tube(name, [p0, p1], radius=r, res=5, paint=paint, out=out, kind="POLY", resolution=1)


def rose(name, loc, s, paint, out, rot=(0, 0, 0)):
    """Rose head: a closed scalloped bud (5 lobes) with a dimpled top - 64 tris."""
    prof = [(0, 0), (.3 * s, .1 * s), (.56 * s, .4 * s), (.58 * s, .65 * s), (.42 * s, .84 * s), (0, .78 * s)]
    ob = dv4.lathe(name, prof, seg=10, loc=loc, rot=rot, paint=paint, out=out, scallop=(5, .14))
    return tag(ob, "z")


def tulip(name, loc, s, paint, out, rot=(0, 0, 0)):
    prof = [(0, 0), (.2 * s, .08 * s), (.4 * s, .4 * s), (.42 * s, .75 * s), (.3 * s, 1.0 * s), (0, .98 * s)]
    ob = dv4.lathe(name, prof, seg=9, loc=loc, rot=rot, paint=paint, out=out, scallop=(3, .12))
    return tag(ob, "z")


def peony(name, loc, s, paint, out, rot=(0, 0, 0)):
    prof = [(0, 0), (.35 * s, .1 * s), (.66 * s, .4 * s), (.68 * s, .62 * s), (.5 * s, .8 * s), (0, .76 * s)]
    ob = dv4.lathe(name, prof, seg=10, loc=loc, rot=rot, paint=paint, out=out, scallop=(5, .12))
    return tag(ob, "z")


def daisy(name, loc, s, paint, center_paint, out, rot=(0, 0, 0), petals=7):
    """Closed scalloped disc (radial paint) + small domed centre."""
    prof = [(0, 0), (.3 * s, .0), (.6 * s, .04 * s), (.3 * s, .07 * s), (0, .07 * s)]
    ob = dv4.lathe(name, prof, seg=petals * 2, loc=loc, rot=rot, paint=paint, out=out, scallop=(petals, .22))
    tag(ob, "r")
    c = dv4.sphere(name + "C", .17 * s, loc=loc, scale=(1, 1, .5), seg=6, rings=3, paint=center_paint, out=out, rot=rot)
    tag(c, "r")
    return ob


def sunflower(name, loc, s, paint, center_paint, out, rot=(0, 0, 0)):
    prof = [(0, -.02 * s), (.36 * s, -.01 * s), (.72 * s, .04 * s), (.36 * s, .08 * s), (0, .08 * s)]
    ob = dv4.lathe(name, prof, seg=22, loc=loc, rot=rot, paint=paint, out=out, scallop=(11, .16))
    tag(ob, "r")
    c = dv4.lathe(name + "C", [(0, .04 * s), (.2 * s, .05 * s), (.33 * s, .09 * s), (.2 * s, .13 * s), (0, .14 * s)], seg=10, loc=loc, rot=rot, paint=center_paint, out=out)
    tag(c, "r")
    return ob


def lavender(name, loc, s, paint, out, rot=(0, 0, 0)):
    """Bumpy tapered spike - one lathe."""
    prof = [(0, 0), (.045 * s, .02 * s), (.052 * s, .07 * s), (.046 * s, .14 * s), (.036 * s, .2 * s), (.02 * s, .25 * s), (0, .28 * s)]
    ob = dv4.lathe(name, prof, seg=6, loc=loc, rot=rot, paint=paint, out=out, scallop=(3, .25))
    return tag(ob, "z")


def hydrangea(name, loc, s, paint, out):
    ob = dv4.icosphere(name, .13 * s, loc=(loc[0], loc[1], loc[2] + .04 * s), subdiv=1, paint=paint, out=out)
    tag(ob, "z")
    for k in range(4):
        a = k * 1.57 + .5
        b = dv4.sphere(name + "%d" % k, .06 * s, loc=(loc[0] + math.cos(a) * .1 * s, loc[1] + math.sin(a) * .1 * s, loc[2] + .02 * s), seg=5, rings=3, paint=paint, out=out)
        tag(b, "z")
    return ob


def bouquet(name, base, out, kinds, paints, leaf_paint, stem_paint, n=5, h=.28, spread=.07, s=1.0, center_paint=None, leaves=3, tilt=28):
    """n flower heads on straight stems fanning out from `base` (z = bucket mouth), plus a few leaves."""
    for i in range(n):
        a = RNG.uniform(0, 2 * math.pi)
        rr = spread * (RNG.uniform(.55, 1.0) if i else .12)
        hh = h * RNG.uniform(.85, 1.1) * (1.08 if i == 0 else 1.0)
        top = (base[0] + math.cos(a) * rr, base[1] + math.sin(a) * rr, base[2] + hh)
        stem(name + "S%d" % i, (base[0] + math.cos(a) * rr * .25, base[1] + math.sin(a) * rr * .25, base[2] - .06), top, stem_paint, out)
        kind = kinds[i % len(kinds)]; p = paints[i % len(paints)]
        k = rr / max(spread, 1e-5)
        rot = (-tilt * k * math.sin(a), tilt * k * math.cos(a), RNG.uniform(0, 360))
        if kind == "rose":
            rose(name + "R%d" % i, top, .12 * s, p, out, rot)
        elif kind == "tulip":
            tulip(name + "T%d" % i, top, .12 * s, p, out, rot)
        elif kind == "peony":
            peony(name + "Pe%d" % i, top, .12 * s, p, out, rot)
        elif kind == "daisy":
            daisy(name + "D%d" % i, top, .11 * s, p, center_paint, out, rot)
        elif kind == "sunflower":
            sunflower(name + "Sf%d" % i, top, .16 * s, p, center_paint, out, rot)
        elif kind == "lavender":
            lavender(name + "L%d" % i, top, 1.15 * s, p, out, rot)
        elif kind == "hydrangea":
            hydrangea(name + "H%d" % i, top, 1.05 * s, p, out)
    for k in range(leaves):
        a = RNG.uniform(0, 360)
        dv4.leaf(name + "Lf%d" % k, .16 * s, .07 * s, loc=(base[0], base[1], base[2] + h * .3), rot=(RNG.uniform(35, 60), 0, a), paint=leaf_paint, out=out,
                 shape="ellipse", bend=.3, cup=.1, thickness=0, nl=2, nw=2)


# ------------------------------------------------------------------------------------------------- pictograms (no text)
def picto_cart(name, loc, s, paint, out="Body", r=.009, normal="Y"):
    """Shopping-cart outline drawn with bars in the XZ plane at y = loc[1] (facing -Y when normal='-Y')."""
    x0, y0, z0 = loc
    def P(u, v):
        return (x0 + u * s, y0, z0 + v * s)
    pts = [P(-.5, .55), P(-.38, .55), P(-.25, .05), P(.42, .05), P(.5, .4), P(-.3, .4)]
    bar(name + "Line", pts, r=r, paint=paint, out=out, res=6)
    bar(name + "Up", [P(-.25, .05), P(-.3, .4)], r=r, paint=paint, out=out, res=6)
    for u in (-.14, .28):
        ring(name + "W%s" % u, .075 * s, r * .9, P(u, -.1), paint=paint, out=out, seg=14, minor=5, rot=(90, 0, 0))
    bar(name + "Bar", [P(-.2, .22), P(.46, .22)], r=r * .8, paint=paint, out=out, res=5)
    bar(name + "Bar2", [P(-.1, .4), P(-.02, .05)], r=r * .8, paint=paint, out=out, res=5)
    bar(name + "Bar3", [P(.1, .4), P(.16, .05)], r=r * .8, paint=paint, out=out, res=5)


def picto_cup(name, loc, s, paint, out="Body", r=.006, steam=True):
    """Coffee cup pictogram (side view) in the XZ plane."""
    x0, y0, z0 = loc
    def P(u, v):
        return (x0 + u * s, y0, z0 + v * s)
    bar(name + "Cup", [P(-.3, .5), P(-.24, .05), P(.24, .05), P(.3, .5)], r=r, paint=paint, out=out, res=6)
    bar(name + "Top", [P(-.34, .5), P(.34, .5)], r=r, paint=paint, out=out, res=6)
    ring(name + "Hdl", .14 * s, r, P(.33, .3), paint=paint, out=out, seg=12, minor=5, rot=(90, 0, 0), arc=180.0)
    bar(name + "Saucer", [P(-.42, -.05), P(.42, -.05)], r=r, paint=paint, out=out, res=6)
    if steam:
        for u in (-.12, .12):
            dv4.tube(name + "St%s" % u, [P(u, .6), P(u - .06, .7), P(u + .06, .82), P(u, .92)], radius=r * .8, res=5, paint=paint, out=out, resolution=4)


def picto_croissant(name, loc, s, paint, out="Body", r=.007):
    x0, y0, z0 = loc
    pts = []
    for k in range(9):
        a = math.radians(20 + k * 17.5)
        pts.append((x0 + math.cos(a) * .4 * s, y0, z0 + math.sin(a) * .3 * s))
    dv4.tube(name, pts, radius=r, res=6, paint=paint, out=out, resolution=3, taper=[(0, .5), (.5, 1.0), (1, .5)])


def picto_heart(name, loc, s, paint, out="Body", r=.006):
    x0, y0, z0 = loc
    pts = []
    for k in range(12):
        t = math.pi * 2 * k / 12
        u = 16 * math.sin(t) ** 3 / 17; v = (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) / 17
        pts.append((x0 + u * .5 * s, y0, z0 + v * .5 * s))
    dv4.tube(name, pts, radius=r, res=5, paint=paint, out=out, resolution=1, cyclic=True)


def picto_flower(name, loc, s, paint, paint2, out="Body", r=.006, petals=5):
    """Chalk-style daisy: ring of petal loops + centre + stem."""
    x0, y0, z0 = loc
    for k in range(petals):
        a = math.radians(90 + k * 360 / petals)
        cx, cz = x0 + math.cos(a) * .22 * s, z0 + math.sin(a) * .22 * s
        dv4.sphere(name + "P%d" % k, .13 * s, loc=(cx, y0, cz), scale=(1, r * 8 / s, 1), seg=6, rings=3, paint=paint, out=out)
    dv4.sphere(name + "C", .1 * s, loc=(x0, y0, z0), scale=(1, r * 10 / s, 1), seg=6, rings=3, paint=paint2, out=out)
    bar(name + "Stem", [(x0, y0, z0 - .3 * s), (x0 + .03 * s, y0, z0 - .62 * s)], r=r, paint=paint, out=out, res=5)


def picto_star(name, loc, s, paint, out="Body", r=.006, n=5):
    x0, y0, z0 = loc
    pts = []
    for k in range(n * 2):
        a = math.radians(90 + k * 180 / n)
        rr = (.5 if k % 2 == 0 else .22) * s
        pts.append((x0 + math.cos(a) * rr, y0, z0 + math.sin(a) * rr))
    bar(name, pts + [pts[0]], r=r, paint=paint, out=out, res=6)
