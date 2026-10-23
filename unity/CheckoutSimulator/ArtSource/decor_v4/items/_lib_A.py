"""_lib_A: extra geometry + paint recipes for group A items (basket-stack, balloons, floor-lamp, bench, water-cooler).
Import from an item:  sys.path.insert(0, os.path.join(dv4.ROOT, "items")); import _lib_A as lib
"""
import math
import bmesh
from mathutils import Vector
import dv4
from dv4 import MATH, VMATH, MIX, RAMP, SMOOTH, NOISE, VORO, COORD, ATTR, paint, from_bm, RNG


# ================================================================================================= node utilities
def normal_xyz(c):
    nt = c.nt
    sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(c.geo.outputs["Normal"], sp.inputs[0])
    return sp.outputs["X"], sp.outputs["Y"], sp.outputs["Z"]


def ABS(nt, x):
    return MATH(nt, "ABSOLUTE", x)


def FRACT(nt, x):
    return MATH(nt, "FRACT", x)


def cell_uv(nt, u, pitch, offset=0.0):
    """signed distance from the nearest lattice line centre: |fract((u-offset)/pitch) - .5| * pitch  (0 at cell centre)."""
    f = FRACT(nt, MATH(nt, "DIVIDE", MATH(nt, "SUBTRACT", u, offset), pitch))
    return MATH(nt, "MULTIPLY", ABS(nt, MATH(nt, "SUBTRACT", f, .5)), pitch)


def grid_mask(nt, u, v, pitch, half, shape="square", soft=.003, off=(0.0, 0.0)):
    """1 inside a hole/dot of half-size `half` repeated every `pitch` in u and v."""
    du = cell_uv(nt, u, pitch, off[0]); dv = cell_uv(nt, v, pitch, off[1])
    if shape == "square":
        d = MATH(nt, "MAXIMUM", du, dv)
    else:
        d = MATH(nt, "SQRT", MATH(nt, "ADD", MATH(nt, "POWER", du, 2.0), MATH(nt, "POWER", dv, 2.0)))
    return SMOOTH(nt, d, half + soft, half - soft)


def zband(nt, z, z0, z1, soft=.006):
    return MATH(nt, "MULTIPLY", SMOOTH(nt, z, z0 - soft, z0 + soft), SMOOTH(nt, z, z1 + soft, z1 - soft))


def ndl(c, L):
    v = Vector(L).normalized()
    return VMATH(c.nt, "DOT_PRODUCT", c.geo.outputs["Normal"], tuple(v))


# ================================================================================================= paints
def paint_plastic(name, base="D74A3C", dark="9E2F24", light="F58A74", hole="4E1510", holes=(), pitch=.021, half=.0065,
                  floor_holes=(), tint=.12, **fin):
    """Moulded plastic with a perforated grid on the walls. holes = [(z0, z1)] bands (world z) where the wall is perforated;
    floor_holes = [z] floors (top-facing) with round holes. Grid axis picks x or y by the wall normal."""
    def r(c):
        nt = c.nt
        nx, ny, nz = normal_xyz(c)
        mot = NOISE(nt, c.pos, 9.0, 2.0)
        col = RAMP(nt, mot, [(.2, dark), (.5, base), (.9, light)])
        col = MIX(nt, .55, col, base)
        if tint > 0:
            t, s, rnd = ATTR(nt)
            col = MIX(nt, MATH(nt, "MULTIPLY", rnd, tint), col, light)
        hx = grid_mask(nt, c.y, c.z, pitch, half)     # walls facing X: grid in (y, z)
        hy = grid_mask(nt, c.x, c.z, pitch, half)     # walls facing Y: grid in (x, z)
        ws = SMOOTH(nt, MATH(nt, "SUBTRACT", ABS(nt, nx), ABS(nt, ny)), -.15, .15)
        # scalar mix: h = hy * (1 - ws) + hx * ws
        h = MATH(nt, "ADD", MATH(nt, "MULTIPLY", hy, MATH(nt, "SUBTRACT", 1.0, ws)), MATH(nt, "MULTIPLY", hx, ws))
        band = 0.0
        for z0, z1 in holes:
            band = MATH(nt, "MAXIMUM", band, zband(nt, c.z, z0, z1))
        side = SMOOTH(nt, ABS(nt, nz), .55, .3)
        hm = MATH(nt, "MULTIPLY", MATH(nt, "MULTIPLY", h, band), side)
        for zf in floor_holes:
            fh = grid_mask(nt, c.x, c.y, pitch * 1.4, half * 1.1, "round")
            fh = MATH(nt, "MULTIPLY", fh, MATH(nt, "MULTIPLY", zband(nt, c.z, zf - .008, zf + .008), SMOOTH(nt, nz, .5, .9)))
            hm = MATH(nt, "MAXIMUM", hm, fh)
        col = MIX(nt, hm, col, hole)
        # glossy sheen on up-facing and rim
        hl = SMOOTH(nt, nz, .25, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, .28), col, light)
        sp = SMOOTH(nt, ndl(c, (.3, .5, .8)), .9, .99)
        col = MIX(nt, MATH(nt, "MULTIPLY", sp, .45), col, "FFE9E2")
        return col
    return paint(name, r, edge=light, edge_k=.6, edge_r=.006, k_ao=.55, k_light=.3, **fin)


def paint_latex(name, base, light, dark, L=(.35, .45, .82), spot=.9, **fin):
    """Glossy balloon latex: smooth light wrap, a bright specular window and a darker underside."""
    def r(c):
        nt = c.nt
        d = ndl(c, L)
        d01 = MATH(nt, "ADD", MATH(nt, "MULTIPLY", d, .5), .5)
        col = RAMP(nt, d01, [(.08, dark), (.42, base), (.78, base), (1.0, light)])
        s = SMOOTH(nt, d, .90, .985)
        col = MIX(nt, MATH(nt, "MULTIPLY", s, spot), col, "FFFFFF")
        s2 = SMOOTH(nt, ndl(c, (-.5, .3, -.6)), .8, .97)        # faint bounce from the floor side
        col = MIX(nt, MATH(nt, "MULTIPLY", s2, .2), col, light)
        return col
    return paint(name, r, k_ao=.2, k_light=.12, **fin)


def paint_chrome(name="Chrome", dark="2A3036", mid="5F6971", light="E6ECF0", warm="B9C2C8", **fin):
    """Cartoon chrome: dark ground reflection, sharp horizon, bright sky."""
    def r(c):
        nt = c.nt
        nz01 = MATH(nt, "ADD", MATH(nt, "MULTIPLY", c.nz, .5), .5)
        col = RAMP(nt, nz01, [(.0, dark), (.30, dark), (.47, mid), (.5, light), (.56, warm), (.68, mid), (.82, light), (1.0, "FFFFFF")])
        return col
    return paint(name, r, edge="FFFFFF", edge_k=.7, edge_r=.004, k_ao=.45, k_light=.2, **fin)


def paint_brass(name="Brass", base="C8963A", dark="7A571A", light="F6DC8C", **fin):
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 12.0, 2.0)
        col = RAMP(nt, mot, [(.2, dark), (.55, base), (.9, light)])
        nz01 = MATH(nt, "ADD", MATH(nt, "MULTIPLY", c.nz, .5), .5)
        band = RAMP(nt, nz01, [(.0, dark), (.32, dark), (.46, base), (.5, light), (.54, base), (.8, base), (1.0, light)])
        col = MIX(nt, .6, col, band)
        return col
    return paint(name, r, edge=light, edge_k=.8, edge_r=.005, k_ao=.5, k_light=.28, **fin)


def paint_fabric(name, base="F4EFE4", dark="D9CDB6", light="FFFBF3", weave=18.0, pleats=0, glow=None, glow_z=None, seam="C9BBA2",
                 inner=None, **fin):
    """Woven fabric; pleats = n vertical seams around Z (lampshade); glow = (hex, z_centre, z_half) warm inside light;
    inner = hex painted on faces whose normal points toward the Z axis (the lit inside of a solidified shade)."""
    def r(c):
        nt = c.nt
        w1 = NOISE(nt, COORD(nt, scale=(weave * 6, weave * 6, weave * 6)), 1.0, 2.0)
        w2 = NOISE(nt, c.pos, weave * .5, 3.0)
        col = RAMP(nt, w2, [(.3, dark), (.6, base), (.9, light)])
        col = MIX(nt, MATH(nt, "MULTIPLY", w1, .18), col, dark)
        if glow:
            gcol, zc, zh = glow
            g = SMOOTH(nt, ABS(nt, MATH(nt, "SUBTRACT", c.z, zc)), zh, 0.0)
            col = MIX(nt, MATH(nt, "MULTIPLY", g, .75), col, gcol)
        if pleats:
            ang = MATH(nt, "ARCTAN2", c.y, c.x)
            u = MATH(nt, "MULTIPLY", ang, pleats / (2 * math.pi))
            du = ABS(nt, MATH(nt, "SUBTRACT", FRACT(nt, u), .5))
            line = SMOOTH(nt, du, .5 - .06, .5 - .02)
            shade = MATH(nt, "MULTIPLY", SMOOTH(nt, du, .2, .48), .35)
            col = MIX(nt, shade, col, dark)
            col = MIX(nt, MATH(nt, "MULTIPLY", line, .7), col, seam)
        if inner:
            cb = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(c.x, cb.inputs[0]); nt.links.new(c.y, cb.inputs[1])
            radial = VMATH(nt, "NORMALIZE", cb.outputs[0])
            dn = VMATH(nt, "DOT_PRODUCT", c.geo.outputs["Normal"], radial)
            m = SMOOTH(nt, dn, .15, -.15)
            col = MIX(nt, m, col, inner)
        return col
    return paint(name, r, k_ao=.5, k_light=.32, **fin)


def paint_tufted(name, base="23355F", dark="121D3A", light="3E5590", px=.17, py=.34, origin=(0.0, 0.0), axis="XY", tilt=0.0,
                 dimple_r=.045, crease=.012, **fin):
    """Velvet with diamond tufting: buttons on lattice A (px, py) and B (shifted by half) -> dimples and creases.
    axis 'XY' uses world x/y (seat); 'XZ' uses x and the tilted (y,z) coordinate (back cushion)."""
    def r(c):
        nt = c.nt
        u = MATH(nt, "SUBTRACT", c.x, origin[0])
        if axis == "XY":
            v = MATH(nt, "SUBTRACT", c.y, origin[1])
        else:
            yy = MATH(nt, "SUBTRACT", c.y, origin[1]); zz = MATH(nt, "SUBTRACT", c.z, origin[2])
            t = math.radians(tilt)
            v = MATH(nt, "ADD", MATH(nt, "MULTIPLY", yy, -math.sin(t)), MATH(nt, "MULTIPLY", zz, math.cos(t)))
        def dist(offu, offv):
            du = cell_uv(nt, u, px, offu); dv = cell_uv(nt, v, py, offv)
            return MATH(nt, "SQRT", MATH(nt, "ADD", MATH(nt, "POWER", du, 2.0), MATH(nt, "POWER", dv, 2.0)))
        d1 = dist(0.0, 0.0); d2 = dist(px * .5, py * .5)
        d = MATH(nt, "MINIMUM", d1, d2)
        vel = NOISE(nt, c.pos, 30.0, 2.0)
        col = RAMP(nt, vel, [(.25, dark), (.5, base), (.85, light)])
        col = MIX(nt, .75, col, base)
        # soft sheen on the puff tops
        hl = SMOOTH(nt, ndl(c, (.25, .45, .86)), .55, .98)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, .35), col, light)
        # dimples around the buttons
        dim = SMOOTH(nt, d, dimple_r, dimple_r * .2)
        col = MIX(nt, MATH(nt, "MULTIPLY", dim, .6), col, dark)
        # creases between neighbouring buttons (cell borders of the diamond lattice)
        cr = SMOOTH(nt, ABS(nt, MATH(nt, "SUBTRACT", d1, d2)), crease, 0.0)
        cr = MATH(nt, "MULTIPLY", cr, SMOOTH(nt, d, dimple_r * .6, dimple_r * 1.4))
        col = MIX(nt, MATH(nt, "MULTIPLY", cr, .45), col, dark)
        # light catching the puff ridge just outside each crease
        rim = SMOOTH(nt, ABS(nt, MATH(nt, "SUBTRACT", d1, d2)), crease * 1.2, crease * 2.6)
        rim = MATH(nt, "MULTIPLY", rim, MATH(nt, "SUBTRACT", 1.0, SMOOTH(nt, ABS(nt, MATH(nt, "SUBTRACT", d1, d2)), crease * 4.0, crease * 2.6)))
        rim = MATH(nt, "MULTIPLY", rim, SMOOTH(nt, d, dimple_r * .8, dimple_r * 1.6))
        col = MIX(nt, MATH(nt, "MULTIPLY", rim, .3), col, light)
        return col
    return paint(name, r, k_ao=.55, k_light=.28, **fin)


def paint_tankwater(name="Tank", deep="1E6FB5", mid="3FA3E6", light="9EDDF7", foam="E8F8FF", z0=1.0, z1=1.5, rings=(), **fin):
    """Water inside a blue bottle: depth gradient, ridge bands, bubbles, a vertical highlight streak."""
    def r(c):
        nt = c.nt
        t = SMOOTH(nt, c.z, z0, z1)
        col = RAMP(nt, t, [(.0, deep), (.5, mid), (1.0, light)])
        for z in rings:
            b = zband(nt, c.z, z - .006, z + .006, .004)
            col = MIX(nt, MATH(nt, "MULTIPLY", b, .5), col, light)
        bub = VORO(nt, VMATH(nt, "MULTIPLY", c.pos, (1, 1, .6)), 22.0, "F1", "Distance")
        bub = SMOOTH(nt, bub, .17, .09)
        col = MIX(nt, MATH(nt, "MULTIPLY", bub, .55), col, foam)
        streak = SMOOTH(nt, ndl(c, (.35, .8, .15)), .82, .97)
        col = MIX(nt, MATH(nt, "MULTIPLY", streak, .6), col, foam)
        top = SMOOTH(nt, c.nz, .6, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", top, .5), col, light)
        return col
    return paint(name, r, k_ao=.2, k_light=.15, **fin)


def paint_bottle(name="Bottle", z0=1.0, water_z=1.5, deep="1C6BB4", mid="3C9FE4", light="8FD5F5", glass="D6ECF7", glass_dark="9FC3DA",
                 foam="F2FBFF", rings=(), **fin):
    """Opaque stylised water bottle: blue water up to water_z (gradient, bubbles, bright waterline), pale glass above, dark
    ridge grooves, two vertical glass highlight streaks."""
    def r(c):
        nt = c.nt
        t = SMOOTH(nt, c.z, z0, water_z)
        wcol = RAMP(nt, t, [(.0, deep), (.55, mid), (1.0, light)])
        bub = VORO(nt, VMATH(nt, "MULTIPLY", c.pos, (1, 1, .7)), 26.0, "F1", "Distance")
        bub = SMOOTH(nt, bub, .16, .08)
        wcol = MIX(nt, MATH(nt, "MULTIPLY", bub, .5), wcol, foam)
        gl = SMOOTH(nt, c.nz, -.2, .9)
        gcol = MIX(nt, MATH(nt, "MULTIPLY", gl, .7), glass_dark, glass)
        below = SMOOTH(nt, c.z, water_z + .004, water_z - .004)
        col = MIX(nt, below, gcol, wcol)
        band = zband(nt, c.z, water_z - .014, water_z + .003, .003)
        col = MIX(nt, MATH(nt, "MULTIPLY", band, .8), col, foam)
        for z in rings:
            g = zband(nt, c.z, z - .01, z + .01, .005)
            col = MIX(nt, MATH(nt, "MULTIPLY", g, .35), col, deep)
        s1 = SMOOTH(nt, ndl(c, (.45, .75, .2)), .86, .97)
        col = MIX(nt, MATH(nt, "MULTIPLY", s1, .75), col, foam)
        s2 = SMOOTH(nt, ndl(c, (-.7, .55, .25)), .93, .99)
        col = MIX(nt, MATH(nt, "MULTIPLY", s2, .5), col, foam)
        top = SMOOTH(nt, c.nz, .7, .98)
        col = MIX(nt, MATH(nt, "MULTIPLY", top, .4), col, foam)
        return col
    return paint(name, r, k_ao=.3, k_light=.2, edge=foam, edge_k=.5, edge_r=.006, **fin)


def paint_stripe(name, base="FBF8F1", stripe=dv4.TEAL, bands=(), variation=.05, **fin):
    """Flat paint with horizontal colour bands [(z0, z1, hex)] (paper cups, trims)."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 10.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, variation), base, "000000")
        for z0, z1, h in bands:
            col = MIX(nt, zband(nt, c.z, z0, z1, .003), col, h)
        return col
    return paint(name, r, k_ao=.5, k_light=.3, **fin)


def paint_wrap(name, base="E0B040", dot="F4EFE4", pitch=.045, half=.009, **fin):
    """Gift wrap: base colour with a polka-dot grid (projected by the face normal)."""
    def r(c):
        nt = c.nt
        nx, ny, nz = normal_xyz(c)
        mot = NOISE(nt, c.pos, 10.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, .12), base, "000000")
        gx = grid_mask(nt, c.y, c.z, pitch, half, "round")
        gy = grid_mask(nt, c.x, c.z, pitch, half, "round")
        gz = grid_mask(nt, c.x, c.y, pitch, half, "round", off=(pitch * .5, pitch * .5))
        wx = SMOOTH(nt, ABS(nt, nx), .5, .8); wy = SMOOTH(nt, ABS(nt, ny), .5, .8); wz = SMOOTH(nt, ABS(nt, nz), .5, .8)
        g = MATH(nt, "MAXIMUM", MATH(nt, "MULTIPLY", gx, wx), MATH(nt, "MAXIMUM", MATH(nt, "MULTIPLY", gy, wy), MATH(nt, "MULTIPLY", gz, wz)))
        return MIX(nt, g, col, dot)
    return paint(name, r, edge="FFF0B8", edge_k=.6, edge_r=.006, k_ao=.55, k_light=.3, **fin)


# ================================================================================================= geometry
def rrect_path(w, d, r, cseg=4):
    """Points (x, y, nx, ny) CCW around a rounded rectangle w x d centred at the origin."""
    hw, hd = max(0.0, w / 2 - r), max(0.0, d / 2 - r)
    pts = []
    for cx, cy, a0 in ((hw, hd, 0), (-hw, hd, 90), (-hw, -hd, 180), (hw, -hd, 270)):
        for k in range(cseg + 1):
            a = math.radians(a0 + 90.0 * k / cseg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a), math.cos(a), math.sin(a)))
    return pts


def sweep_rect(name, profile, w, d, r=.04, cseg=4, cap_first=True, cap_last=True, paint=None, out="Body", loc=(0, 0, 0),
               rot=(0, 0, 0), **kw):
    """Sweeps a profile [(offset, z)] (offset = outward distance from the rounded-rect outline, may be negative) around
    the rounded rectangle. Like lathe() but for boxes with rounded corners: baskets, cabinets, cushions."""
    path = rrect_path(w, d, r, cseg)
    bm = bmesh.new(); rings = []
    for off, z in profile:
        rings.append([bm.verts.new((x + nx * off, y + ny * off, z)) for x, y, nx, ny in path])
    n = len(path)
    for i in range(len(rings) - 1):
        for k in range(n):
            a, b = rings[i][k], rings[i][(k + 1) % n]
            c_, d_ = rings[i + 1][(k + 1) % n], rings[i + 1][k]
            try:
                f = bm.faces.new((a, b, c_, d_)); f.smooth = True
            except ValueError:
                pass
    if cap_first:
        f = bm.faces.new(list(reversed(rings[0]))); f.smooth = False
    if cap_last:
        f = bm.faces.new(rings[-1]); f.smooth = False
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return from_bm(name, bm, paint, out, loc, rot, **kw)


def prism(name, pts2d, h, paint=None, out="Body", loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.0, **kw):
    """Extruded polygon: pts2d [(x, y)] CCW in local XY, extruded from z 0 to h."""
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, 0)) for x, y in pts2d]
    hi = [bm.verts.new((x, y, h)) for x, y in pts2d]
    n = len(pts2d)
    bm.faces.new(list(reversed(lo))); bm.faces.new(hi)
    for i in range(n):
        bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = from_bm(name, bm, paint, out, loc, rot, smooth=False, **kw)
    if bevel > 0:
        dv4.mod_bevel(ob, bevel, 2)
    return ob


def tufted_cushion(name, w, d, h, px=.17, rows=3, amp=.02, nx=28, ny=10, paint=None, out="Body", loc=(0, 0, 0), rot=(0, 0, 0),
                   bevel=.03, segs=3, button_r=.012, button_paint=None, dimple=.012, **kw):
    """Upholstered cushion w x d x h (local, z up from 0): the top is a grid with puffs between the diamond lattice of buttons.
    Returns (object, [button positions (x, y, z) in local space])."""
    py = d / rows if rows > 1 else d
    buttons = []
    ncol = int(w / px) + 2
    for j in range(rows):
        y = -d / 2 + py * (j + .5)
        off = (px * .5) if ((j - (rows - 1) // 2) % 2) else 0.0      # centre row on lattice A (matches paint_tufted)
        for i in range(-ncol, ncol + 1):
            x = i * px + off
            if abs(x) < w / 2 - px * .45 and abs(y) < d / 2 - py * .3:
                buttons.append((x, y))
    rb = .5 * math.hypot(px * .5, py * .5) * 1.25
    def puff(x, y):
        dmin = min(math.hypot(x - bx, y - by) for bx, by in buttons) if buttons else rb
        t = min(1.0, dmin / rb)
        t = t * t * (3 - 2 * t)
        return amp * (t ** .85) - dimple * (1 - t) ** 3
    bm = bmesh.new()
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = -w / 2 + w * i / nx; y = -d / 2 + d * j / ny
            e = min(x + w / 2, w / 2 - x, y + d / 2, d / 2 - y)       # flatten toward the border so the bevel stays clean
            k = min(1.0, e / .035)
            z = h + puff(x, y) * k
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])); f.smooth = True
    # boundary loop CCW: bottom row ->, right column ^, top row <-, left column v
    loop = [grid[0][i] for i in range(nx)] + [grid[j][nx] for j in range(ny)] + [grid[ny][i] for i in range(nx, 0, -1)] + \
           [grid[j][0] for j in range(ny, 0, -1)]
    base = [bm.verts.new((v.co.x, v.co.y, 0.0)) for v in loop]
    n = len(loop)
    for k in range(n):
        f = bm.faces.new((base[k], base[(k + 1) % n], loop[(k + 1) % n], loop[k])); f.smooth = True
    bm.faces.new(list(reversed(base)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = from_bm(name, bm, paint, out, loc, rot, **kw)
    if bevel > 0:
        m = dv4.mod_bevel(ob, bevel, segs, angle=40.0)
    if button_r > 0:
        from mathutils import Euler
        R = Euler([math.radians(a) for a in rot], "XYZ")
        for bx, by in buttons:
            p = Vector((bx, by, h + puff(bx, by) + button_r * .5)); p.rotate(R); p += Vector(loc)
            dv4.sphere("Btn", button_r, loc=tuple(p), rot=rot, scale=(1, 1, .55), seg=8, rings=4, paint=button_paint or paint, out=out)
    return ob, [(bx, by, h + puff(bx, by)) for bx, by in buttons]


def helix(center, r, turns, h, n=16, a0=0.0, r1=None):
    """Points of a helix around a vertical axis through center, from z=center.z going DOWN by h."""
    pts = []
    for i in range(n + 1):
        t = i / n
        a = a0 + t * turns * 2 * math.pi
        rr = r if r1 is None else r + (r1 - r) * t
        pts.append((center[0] + math.cos(a) * rr, center[1] + math.sin(a) * rr, center[2] - h * t))
    return pts
