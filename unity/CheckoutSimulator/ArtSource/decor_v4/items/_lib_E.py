"""_lib_E: extra paint recipes and shape helpers for group E (tree-planter, flower-bed, street-lamp, bike-rack, recycle-bins)."""
import math
import bmesh
import dv4
from dv4 import N, MATH, VMATH, MIX, RAMP, COORD, NOISE, VORO, WAVE, ATTR, SMOOTH, RNG


# ------------------------------------------------------------------------------------------------- paints
def paint_canopy(name="Canopy", base="4C9A38", dark="1D4F26", light="9AD452", spk="D2F08C", **fin):
    """Clumpy foliage: soft clump shading, top lighter than the underside, leaf specks."""
    def r(c):
        nt = c.nt
        clump = NOISE(nt, c.pos, 5.0, 3.0, .55)
        up = MATH(nt, "ADD", MATH(nt, "MULTIPLY", c.nz, .5), .5)
        g = MATH(nt, "ADD", MATH(nt, "MULTIPLY", clump, .55), MATH(nt, "MULTIPLY", up, .45))
        col = RAMP(nt, g, [(.1, dark), (.45, base), (.9, light)])
        fine = VORO(nt, c.pos, 55.0, "F1", "Distance")
        col = MIX(nt, MATH(nt, "MULTIPLY", fine, .5), col, dark)
        cells = SMOOTH(nt, VORO(nt, c.pos, 28.0, "F1", "Distance"), .25, .55)
        col = MIX(nt, MATH(nt, "MULTIPLY", cells, .25), col, dark)
        sp = SMOOTH(nt, NOISE(nt, c.pos, 45.0, 2.0), .64, .74)
        col = MIX(nt, MATH(nt, "MULTIPLY", MATH(nt, "MULTIPLY", sp, up), .85), col, spk)
        return col
    fin.setdefault("k_ao", .55); fin.setdefault("k_light", .45)
    return dv4.paint(name, r, **fin)


def paint_petal(name, col, dark, light, **fin):
    """Flower petals: one colour family, lighter on top, darker in the crevices."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 30.0, 2.0)
        colr = RAMP(nt, mot, [(.3, dark), (.7, col)])
        up = SMOOTH(nt, c.nz, .1, .95)
        colr = MIX(nt, MATH(nt, "MULTIPLY", up, .45), colr, light)
        colr = MIX(nt, MATH(nt, "MULTIPLY", c.crev, .7), colr, dark)
        return colr
    return dv4.paint(name, r, k_ao=.45, k_light=.3, edge=light, edge_k=.5, edge_r=.005, **fin)


def paint_brick(name="Brick", base="BE5B3E", dark="8C3E29", light="D97D5E", mortar="E8DECB", n=28, h=.07, z0=0.0, z1=1.0,
                radial=True, length=.16, **fin):
    """Staggered brick courses with light mortar joints between z0 and z1 (radial: around the Z axis; else along X)."""
    def r(c):
        nt = c.nt
        if radial:
            ang = MATH(nt, "ARCTAN2", c.y, c.x)
            u = MATH(nt, "MULTIPLY", ang, n / (2 * math.pi))
        else:
            u = MATH(nt, "DIVIDE", c.x, length)
        zz = MATH(nt, "DIVIDE", MATH(nt, "SUBTRACT", c.z, z0), h)
        row = MATH(nt, "FLOOR", zz)
        stag = MATH(nt, "MULTIPLY", MATH(nt, "MODULO", row, 2.0), .5)
        uu = MATH(nt, "ADD", u, stag)
        du = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", MATH(nt, "FRACT", uu), .5))
        dz = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", MATH(nt, "FRACT", zz), .5))
        gv = SMOOTH(nt, du, .5 - .07, .5 - .035)
        gh = SMOOTH(nt, dz, .5 - .13, .5 - .07)
        gm = MATH(nt, "MAXIMUM", gv, gh)
        band = MATH(nt, "MULTIPLY", SMOOTH(nt, c.z, z0 - .01, z0 + .01), SMOOTH(nt, c.z, z1 + .01, z1 - .01))
        gm = MATH(nt, "MULTIPLY", gm, band)
        cell = N(nt, "CombineXYZ", X=MATH(nt, "FLOOR", uu), Y=row, Z=0.0).outputs[0]
        tint = NOISE(nt, VMATH(nt, "MULTIPLY", cell, (.731, 1.37, 1.0)), 1.0, 0.0)
        mot = NOISE(nt, c.pos, 25.0, 3.0)
        col = RAMP(nt, mot, [(.3, dark), (.7, base)])
        col = MIX(nt, MATH(nt, "MULTIPLY", tint, .55), col, light)
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, NOISE(nt, c.pos, 60.0, 2.0), .6, .72), .3), col, dark)
        mcol = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 40.0, 2.0), .3), mortar, "B9AE9C")
        return MIX(nt, gm, col, mcol)
    return dv4.paint(name, r, edge="F0CDB8", edge_k=.4, edge_r=.01, **fin)


def paint_painted(name, hex, light="FFFFFF", dark=None, variation=.1, sheen=.12, **fin):
    """Powder-coated / painted metal and plastic: tiny mottle, sheen on top faces, worn light edges."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 12.0, 3.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, variation), hex, dark or "000000")
        hl = SMOOTH(nt, c.nz, .3, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, sheen), col, light)
        return col
    return dv4.paint(name, r, edge=light, edge_k=.6, edge_r=.008, **fin)


def paint_wicker(name="Wicker", base="C9954F", dark="7E5426", light="EBC27E", scale=55.0, **fin):
    """Woven basket: horizontal strands with vertical ribs crossing them."""
    def r(c):
        nt = c.nt
        s1 = WAVE(nt, c.pos, scale=scale, dist=.6, detail=1.0, dscale=1.0, direction="Z")
        col = RAMP(nt, s1, [(.1, dark), (.45, base), (.9, light)])
        rib = MATH(nt, "MAXIMUM", SMOOTH(nt, WAVE(nt, c.pos, scale=scale * .5, dist=.3, detail=1.0, direction="X"), .8, .95),
                   SMOOTH(nt, WAVE(nt, c.pos, scale=scale * .5, dist=.3, detail=1.0, direction="Y"), .8, .95))
        col = MIX(nt, MATH(nt, "MULTIPLY", rib, .55), col, dark)
        col = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 8.0, 2.0), .25), col, dark)
        return col
    return dv4.paint(name, r, edge=light, edge_k=.5, edge_r=.006, **fin)


def paint_rubber(name="Rubber", base="2B2E31", dark="141618", light="596067", **fin):
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 30.0, 3.0)
        col = RAMP(nt, mot, [(.3, dark), (.75, base)])
        tread = SMOOTH(nt, NOISE(nt, c.pos, 80.0, 2.0), .55, .62)
        col = MIX(nt, MATH(nt, "MULTIPLY", tread, .5), col, light)
        return col
    return dv4.paint(name, r, edge=light, edge_k=.7, edge_r=.006, k_light=.3, **fin)


def paint_fabric(name, hex, dark, light, stripe=None, stripe_scale=40.0, **fin):
    """Cloth: fine weave, optional horizontal stripes (along Z)."""
    def r(c):
        nt = c.nt
        weave = NOISE(nt, c.pos, 120.0, 1.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", weave, .18), hex, dark)
        if stripe:
            s = SMOOTH(nt, WAVE(nt, c.pos, scale=stripe_scale, dist=0.0, detail=0.0, direction="Z"), .45, .55)
            col = MIX(nt, s, col, stripe)
        up = SMOOTH(nt, c.nz, .2, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", up, .2), col, light)
        return col
    return dv4.paint(name, r, k_light=.3, **fin)


# ------------------------------------------------------------------------------------------------- shapes
def flat_shape(name, pts, depth=.01, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", **kw):
    """Extruded 2D polygon (CCW points in the local XY plane, +Z normal), thickness `depth` centred on the plane."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, 0.0)) for x, y in pts]
    f = bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=[f], ngon_method="EAR_CLIP")
    ob = dv4.from_bm(name, bm, paint, out, loc, rot, smooth=False, **kw)
    dv4.mod_solidify(ob, depth, offset=0.0)
    return ob


def star_pts(r_out, r_in, n=5, a0=90.0):
    pts = []
    for i in range(2 * n):
        a = math.radians(a0 + i * 180.0 / n)
        r = r_out if i % 2 == 0 else r_in
        pts.append((math.cos(a) * r, math.sin(a) * r))
    return pts


def heart_pts(s, n=24):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x * s / 17.0, y * s / 17.0))
    return pts


def ring_pts(r, n=16):
    return [(math.cos(2 * math.pi * i / n) * r, math.sin(2 * math.pi * i / n) * r) for i in range(n)]


def arc_pts(center, r, a0, a1, n=8, plane="XZ"):
    """Points on an arc (degrees) for tubes."""
    out = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        u, v = math.cos(a) * r, math.sin(a) * r
        if plane == "XZ":
            out.append((center[0] + u, center[1], center[2] + v))
        elif plane == "YZ":
            out.append((center[0], center[1] + u, center[2] + v))
        else:
            out.append((center[0] + u, center[1] + v, center[2]))
    return out


def bent_arrow(name, center, r, a0, a1, width, depth, paint, loc=(0, 0, 0), rot=(0, 0, 0), out="Body", head=1.6, n=9, tip_k=1.2, **kw):
    """Curved chunky arrow (recycling symbol style) in the local XY plane: an arc band from a0 to a1 (deg), head at a1."""
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append((math.cos(a) * (r + width / 2), math.sin(a) * (r + width / 2)))
    ah = math.radians(a1)
    tdir = (-math.sin(ah), math.cos(ah))
    if a1 < a0:
        tdir = (-tdir[0], -tdir[1])
    hw = width * head
    base_o = (math.cos(ah) * (r + hw), math.sin(ah) * (r + hw))
    base_i = (math.cos(ah) * (r - hw), math.sin(ah) * (r - hw))
    tip = (math.cos(ah) * r + tdir[0] * width * head * tip_k, math.sin(ah) * r + tdir[1] * width * head * tip_k)
    pts += [base_o, tip, base_i]
    for i in range(n, -1, -1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append((math.cos(a) * (r - width / 2), math.sin(a) * (r - width / 2)))
    if a1 < a0:
        pts.reverse()
    return flat_shape(name, pts, depth, loc, rot, paint, out, **kw)


def rounded_rect_pts(w, h, r, n=4):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90.0 * i / n)
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


# ------------------------------------------------------------------------------------------------- plants
def flower_head(name, size, loc, paint, out="Body", rot=(0, 0, 0), lobes=6, seg=12):
    """Scalloped dome flower (marigold / mum silhouette)."""
    prof = [(0, 0), (.55, .08), (.95, .32), (1.0, .58), (.72, .82), (.35, .96), (0, 1.0)]
    prof = [(r * size, z * size) for r, z in prof]
    return dv4.lathe(name, prof, seg=seg, loc=loc, rot=rot, paint=paint, out=out, scallop=(lobes, .14))


def tulip(name, size, loc, paint, out="Body", rot=(0, 0, 0)):
    prof = [(0, 0), (.28, .02), (.48, .25), (.55, .55), (.5, .85), (.38, 1.05), (.2, 1.15)]
    prof = [(r * size, z * size) for r, z in prof]
    return dv4.lathe(name, prof, seg=14, loc=loc, rot=rot, paint=paint, out=out, scallop=(6, .16))


def daisy(name, size, loc, petal, centre, out="Body", rot=(0, 0, 0), petals=10):
    prof = [(0, 0), (.4, .03), (1.0, .0)]
    prof = [(r * size, z * size) for r, z in prof]
    dv4.lathe(name, prof, seg=petals * 2, loc=loc, rot=rot, paint=petal, out=out, scallop=(petals, .22))
    dv4.sphere(name + "C", size * .3, loc=loc, scale=(1, 1, .6), seg=8, rings=5, paint=centre, out=out, rot=rot)


def petunia(name, size, loc, paint, throat, out="Body", rot=(0, 0, 0)):
    """Flat five-lobed flower face (primrose / petunia seen from above) with a dark throat."""
    prof = [(0, 0), (.45, .06), (1.0, .11)]
    prof = [(r * size, z * size) for r, z in prof]
    dv4.lathe(name, prof, seg=20, loc=loc, rot=rot, paint=paint, out=out, scallop=(5, .26))
    dv4.sphere(name + "T", size * .22, loc=loc, scale=(1, 1, .5), seg=8, rings=4, paint=throat, out=out, rot=rot)


def stem(name, p0, p1, paint, out="Body", radius=.006, res=5, lean=.01):
    pm = ((p0[0] + p1[0]) / 2 + lean, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2)
    return dv4.tube(name, [p0, pm, p1], radius=radius, res=res, paint=paint, out=out, resolution=2, taper=[(0, 1.0), (1, .75)])
