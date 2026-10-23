"""_lib_B: extra helpers + paint recipes for group B items (plant-palm, promo-stand, watermelon-pile, digital-totem, gumball).
Imported by the item scripts with  sys.path.insert(0, os.path.join(dv4.ROOT, "items")); import _lib_B as lib
"""
import math
import bpy, bmesh
from mathutils import Vector, Matrix
import dv4
from dv4 import MATH, VMATH, MIX, RAMP, COORD, NOISE, VORO, WAVE, ATTR, SMOOTH, RNG, rad


# ================================================================================================ 2D masks (metres)
def rel(c, cu, cv, axes="xz"):
    """(u, v) sockets = chosen world axes minus a centre."""
    a = {"x": c.x, "y": c.y, "z": c.z}
    return MATH(c.nt, "SUBTRACT", a[axes[0]], cu), MATH(c.nt, "SUBTRACT", a[axes[1]], cv)


def rot2(c, u, v, deg):
    nt = c.nt; ca, sa = math.cos(rad(deg)), math.sin(rad(deg))
    uu = MATH(nt, "SUBTRACT", MATH(nt, "MULTIPLY", u, ca), MATH(nt, "MULTIPLY", v, sa))
    vv = MATH(nt, "ADD", MATH(nt, "MULTIPLY", u, sa), MATH(nt, "MULTIPLY", v, ca))
    return uu, vv


def dist2(c, u, v):
    return MATH(c.nt, "SQRT", MATH(c.nt, "ADD", MATH(c.nt, "MULTIPLY", u, u), MATH(c.nt, "MULTIPLY", v, v)))


def inside(c, d, r, soft=.003):
    """1 where socket d < r (r may be a socket)."""
    return SMOOTH(c.nt, MATH(c.nt, "SUBTRACT", d, r), soft, -soft)


def m_circle(c, u, v, r, soft=.003):
    return inside(c, dist2(c, u, v), r, soft)


def m_ring(c, u, v, r_out, r_in, soft=.003):
    d = dist2(c, u, v)
    return MATH(c.nt, "MULTIPLY", inside(c, d, r_out, soft), MATH(c.nt, "SUBTRACT", 1.0, inside(c, d, r_in, soft)))


def m_rect(c, u, v, w, h, soft=.003):
    """|u| < w and |v| < h (half sizes)."""
    nt = c.nt
    mu = SMOOTH(nt, MATH(nt, "ABSOLUTE", u), w + soft, w - soft)
    mv = SMOOTH(nt, MATH(nt, "ABSOLUTE", v), h + soft, h - soft)
    return MATH(nt, "MULTIPLY", mu, mv)


def m_star(c, u, v, ro, ri=None, n=5, rot=90.0, soft=.003, sharp=1.6):
    """Pointed star (n tips) of outer radius ro."""
    nt = c.nt; ri = ri if ri is not None else ro * .45
    th = MATH(nt, "SUBTRACT", MATH(nt, "ARCTAN2", v, u), rad(rot))
    ph = MATH(nt, "FRACT", MATH(nt, "MULTIPLY", th, n / (2 * math.pi)))
    tri = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", MATH(nt, "MULTIPLY", ph, 2.0), 1.0))     # 1 at tips, 0 at valleys
    tri = MATH(nt, "POWER", tri, sharp)
    r = MATH(nt, "ADD", ri, MATH(nt, "MULTIPLY", tri, ro - ri))
    return inside(c, dist2(c, u, v), r, soft)


def m_burst(c, u, v, r, amp=.14, n=12, soft=.003):
    """Seal / starburst badge: r * (1 + amp cos(n theta))."""
    nt = c.nt
    th = MATH(nt, "ARCTAN2", v, u)
    rr = MATH(nt, "MULTIPLY", MATH(nt, "ADD", 1.0, MATH(nt, "MULTIPLY", MATH(nt, "COSINE", MATH(nt, "MULTIPLY", th, float(n))), amp)), r)
    return inside(c, dist2(c, u, v), rr, soft)


def m_heart(c, u, v, s, soft=.04):
    """Heart of about 2.3*s wide (implicit curve)."""
    nt = c.nt
    X = MATH(nt, "DIVIDE", u, s); Y = MATH(nt, "ADD", MATH(nt, "DIVIDE", v, s), -.1)
    x2 = MATH(nt, "MULTIPLY", X, X); y2 = MATH(nt, "MULTIPLY", Y, Y)
    a = MATH(nt, "SUBTRACT", MATH(nt, "ADD", x2, y2), 1.0)
    f = MATH(nt, "SUBTRACT", MATH(nt, "POWER", a, 3.0), MATH(nt, "MULTIPLY", x2, MATH(nt, "MULTIPLY", y2, Y)))
    return SMOOTH(nt, f, soft, -soft)


def m_tag(c, u, v, w=.05, h=.03, tip=.035, hole=.008, rot=-30.0, soft=.003):
    """Price tag: rectangle (half w x h) with a pointed end on +u and a hole in the point."""
    nt = c.nt
    uu, vv = rot2(c, u, v, rot)
    body = m_rect(c, uu, vv, w, h, soft)
    t = MATH(nt, "SUBTRACT", uu, w)
    hh = MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", 1.0, MATH(nt, "DIVIDE", t, tip)), h)
    tri = MATH(nt, "MULTIPLY", SMOOTH(nt, t, -soft, soft), SMOOTH(nt, MATH(nt, "SUBTRACT", MATH(nt, "ABSOLUTE", vv), hh), soft, -soft))
    tri = MATH(nt, "MULTIPLY", tri, SMOOTH(nt, t, tip + soft, tip - soft))
    m = MATH(nt, "MAXIMUM", body, tri)
    hu = MATH(nt, "SUBTRACT", uu, w + tip * .3)
    return MATH(nt, "MULTIPLY", m, MATH(nt, "SUBTRACT", 1.0, m_circle(c, hu, vv, hole, soft)))


def m_percent(c, u, v, s=.05, soft=.003):
    """A % sign of height ~2*s: two rings and a slanted bar."""
    nt = c.nt
    ru = s * .34; ri = s * .16
    a = m_ring(c, MATH(nt, "ADD", u, s * .5), MATH(nt, "SUBTRACT", v, s * .55), ru, ri, soft)
    b = m_ring(c, MATH(nt, "SUBTRACT", u, s * .5), MATH(nt, "ADD", v, s * .55), ru, ri, soft)
    uu, vv = rot2(c, u, v, 62.0)
    bar = m_rect(c, uu, vv, s * .12, s * .95, soft)
    return MATH(nt, "MAXIMUM", MATH(nt, "MAXIMUM", a, b), bar)


def m_arrow(c, u, v, s=.05, rot=0.0, soft=.003):
    """Arrow pointing +u (rotated by rot), length ~2*s."""
    nt = c.nt
    uu, vv = rot2(c, u, v, rot)
    shaft = m_rect(c, MATH(nt, "ADD", uu, s * .45), vv, s * .55, s * .2, soft)
    t = MATH(nt, "SUBTRACT", uu, s * .1)
    hh = MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", 1.0, MATH(nt, "DIVIDE", t, s * .9)), s * .6)
    head = MATH(nt, "MULTIPLY", SMOOTH(nt, t, -soft, soft), SMOOTH(nt, MATH(nt, "SUBTRACT", MATH(nt, "ABSOLUTE", vv), hh), soft, -soft))
    head = MATH(nt, "MULTIPLY", head, SMOOTH(nt, t, s * .9 + soft, s * .9 - soft))
    return MATH(nt, "MAXIMUM", shaft, head)


def face_mask(c, axis="y", sign=1.0, lo=.6, hi=.9):
    """1 on faces whose normal points along +/- axis."""
    nt = c.nt
    sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(c.geo.outputs["Normal"], sp.inputs[0])
    n = sp.outputs[{"x": "X", "y": "Y", "z": "Z"}[axis]]
    return SMOOTH(nt, MATH(nt, "MULTIPLY", n, sign), lo, hi)


def band_z(c, z0, z1, soft=.004):
    nt = c.nt
    return MATH(nt, "MULTIPLY", SMOOTH(nt, c.z, z0 - soft, z0 + soft), SMOOTH(nt, c.z, z1 + soft, z1 - soft))


# ================================================================================================ paints
def paint_chrome(name="Chrome", dark="4A525B", mid="A9B3BB", light="F2F6F8", tint="DDE8F0", **fin):
    """Stylised chrome: dark 'ground' reflection below, bright sky above, a hot horizon line."""
    def r(c):
        nt = c.nt
        col = RAMP(nt, c.nz, [(-1.0, dark), (-.25, mid), (.0, dark), (.12, light), (.45, tint), (1.0, light)])
        mot = NOISE(nt, c.pos, 6.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, .18), col, mid)
        return col
    return paint(name, r, k_ao=.5, k_light=.25, edge=light, edge_k=1.0, edge_r=.004, **fin)


def paint_brushed(name="Alu", base="AEB7BD", dark="6F7A82", light="DCE3E7", axis="Z", **fin):
    """Brushed aluminium: fine streaks along `axis`, lighter on the top-facing side."""
    def r(c):
        nt = c.nt
        s = {"Z": (90, 90, 1), "X": (1, 90, 90), "Y": (90, 1, 90)}[axis]
        streak = NOISE(nt, COORD(nt, scale=s), 1.5, 2.0)
        col = RAMP(nt, streak, [(.35, dark), (.5, base), (.68, light)])
        col = MIX(nt, .7, col, base)
        tone = NOISE(nt, c.pos, 3.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", tone, .18), col, dark)
        hl = SMOOTH(nt, c.nz, -.2, .9)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, .3), col, light)
        return col
    return paint(name, r, k_ao=.55, k_light=.3, edge=light, edge_k=.9, edge_r=.005, **fin)


def paint_hammered_gold(name="Brass", base="D7A232", dark="8C6218", light="FFE48C", dimple=22.0, **fin):
    """Hammered brass planter: voronoi dimples with a highlight rim on each dent."""
    def r(c):
        nt = c.nt
        d = VORO(nt, c.pos, dimple, "F1", "Distance")
        dent = RAMP(nt, d, [(.0, light), (.25, base), (.6, base), (.95, dark)])
        mot = NOISE(nt, c.pos, 5.0, 2.0)
        shade = RAMP(nt, mot, [(.2, dark), (.55, base), (.9, light)])
        shade = MIX(nt, .4, shade, dent)
        grad = SMOOTH(nt, c.z, .0, .6)
        shade = MIX(nt, MATH(nt, "MULTIPLY", grad, .2), shade, light)
        hl = SMOOTH(nt, c.nz, .1, .9)
        return MIX(nt, MATH(nt, "MULTIPLY", hl, .45), shade, light)
    return paint(name, r, edge=light, edge_k=1.0, edge_r=.006, **fin)


def paint_gloss(name, base, dark, light, hl_amt=.45, **fin):
    """Glossy enamel (cast gumball body, cans): colour + vertical highlight band + top light."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 8.0, 2.0)
        col = RAMP(nt, mot, [(.3, dark), (.7, base)])
        hl = SMOOTH(nt, c.nz, .2, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, hl_amt), col, light)
        return col
    return paint(name, r, edge=light, edge_k=.8, edge_r=.005, **fin)


def paint_cane(name="Cane", base="A9B35A", dark="6D7A2E", light="D7DE8E", ring="8B6A33", period=.11, **fin):
    """Areca palm cane: light green with brown nodal rings every `period` metres (world z)."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 12.0, 2.0)
        col = RAMP(nt, mot, [(.3, dark), (.6, base), (.9, light)])
        ph = MATH(nt, "FRACT", MATH(nt, "DIVIDE", c.z, period))
        rng = SMOOTH(nt, MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", ph, .5)), .07, .04)
        col = MIX(nt, MATH(nt, "MULTIPLY", rng, .85), col, ring)
        streak = WAVE(nt, COORD(nt, scale=(30, 30, 1)), 2.0, 1.0, 1.0, 1.0, "X")
        col = MIX(nt, MATH(nt, "MULTIPLY", streak, .15), col, dark)
        return col
    return paint(name, r, k_ao=.5, **fin)


def paint_melon(name="Melon", dark="2E6B2A", mid="4E9A3A", light="A5CF5F", stripes=12, spot="E3D98D", **fin):
    """Watermelon skin from the Paint attribute of sphere_attr(): R = longitude, G = latitude (0 bottom pole), B random."""
    def r(c):
        nt = c.nt
        lon, lat, rnd = ATTR(nt)
        wob = MATH(nt, "ADD", MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", NOISE(nt, c.pos, 8.0, 2.0), .5), .5),
                   MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", NOISE(nt, c.pos, 35.0, 2.0), .5), .22))
        ph = MATH(nt, "FRACT", MATH(nt, "ADD", MATH(nt, "MULTIPLY", lon, float(stripes)), wob))
        tri = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", MATH(nt, "MULTIPLY", ph, 2.0), 1.0))
        # jagged stripe edges + mottled interior
        s = SMOOTH(nt, tri, .3, .62)
        col = RAMP(nt, s, [(.0, light), (.45, mid), (1.0, dark)])
        mot = NOISE(nt, c.pos, 30.0, 3.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, .25), col, dark)
        col = MIX(nt, MATH(nt, "MULTIPLY", rnd, .2), col, light)
        # pale field spot near the lower pole, darker caps
        sp = MATH(nt, "MULTIPLY", SMOOTH(nt, lat, .16, .04), SMOOTH(nt, NOISE(nt, c.pos, 10.0, 2.0), .35, .5))
        col = MIX(nt, sp, col, spot)
        return col
    return paint(name, r, k_ao=.55, k_light=.4, edge=light, edge_k=.3, edge_r=.004, **fin)


def paint_melon_pos(name, center, dark="2E6B2A", mid="4E9A3A", light="A5CF5F", stripes=12, **fin):
    """Same stripes, by world azimuth around a vertical axis through `center` (for lathed cut halves)."""
    def r(c):
        nt = c.nt
        u, v = rel(c, center[0], center[1], "xy")
        lon = MATH(nt, "MULTIPLY", MATH(nt, "ARCTAN2", v, u), stripes / (2 * math.pi))
        wob = MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", NOISE(nt, c.pos, 8.0, 2.0), .5), .5)
        ph = MATH(nt, "FRACT", MATH(nt, "ADD", lon, wob))
        tri = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", MATH(nt, "MULTIPLY", ph, 2.0), 1.0))
        s = SMOOTH(nt, tri, .3, .62)
        col = RAMP(nt, s, [(.0, light), (.45, mid), (1.0, dark)])
        mot = NOISE(nt, c.pos, 30.0, 3.0)
        return MIX(nt, MATH(nt, "MULTIPLY", mot, .25), col, dark)
    return paint(name, r, k_ao=.55, k_light=.4, **fin)


def paint_flesh(name, center, R, red="E23F3C", pink="F07A72", rind="F3EDCF", skin="4E9A3A", seed="2B1A12", seeds=True, **fin):
    """Cut watermelon face (horizontal, centred at `center`, radius R): red flesh, pale rind ring, painted seeds."""
    def r(c):
        nt = c.nt
        u, v = rel(c, center[0], center[1], "xy")
        d = MATH(nt, "DIVIDE", dist2(c, u, v), R)
        col = RAMP(nt, d, [(.0, red), (.72, red), (.86, pink), (.9, rind), (.95, rind), (.97, skin)])
        grain = NOISE(nt, c.pos, 40.0, 3.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", grain, .22), col, "B8302E")
        if seeds:
            vd = VORO(nt, COORD(nt, scale=(1, 1, .01)), 46.0, "F1", "Distance")
            vc = VORO(nt, COORD(nt, scale=(1, 1, .01)), 46.0, "F1", "Color")
            spc = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(vc, spc.inputs[0])
            keep = SMOOTH(nt, spc.outputs[0], .5, .58)
            sm = MATH(nt, "MULTIPLY", SMOOTH(nt, vd, .3, .22), keep)
            ring = MATH(nt, "MULTIPLY", SMOOTH(nt, d, .3, .38), SMOOTH(nt, d, .78, .7))
            col = MIX(nt, MATH(nt, "MULTIPLY", sm, ring), col, seed)
        return col
    return paint(name, r, k_ao=.4, k_light=.25, **fin)


def paint_straw(name="Straw", base="D9B45A", dark="9C7A2E", light="F4DE8E", **fin):
    def r(c):
        nt = c.nt
        a = WAVE(nt, COORD(nt, scale=(1, 1, 1), rot=(0, 0, 25)), 40.0, 3.0, 2.0, 1.0, "Y")
        b = WAVE(nt, COORD(nt, scale=(1, 1, 1), rot=(0, 0, -40)), 36.0, 3.0, 2.0, 1.0, "Y")
        g = MATH(nt, "MAXIMUM", a, b)
        col = RAMP(nt, g, [(.2, dark), (.6, base), (.95, light)])
        return MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 12.0, 2.0), .3), col, dark)
    return paint(name, r, k_ao=.6, **fin)


def paint_box(name, center, size, band, icon="star", icon_col="FFFFFF", card="C8A070", dark="8F6A40", light="E2C695",
              band_frac=(.18, .68), stripe="F6F1E6", **fin):
    """Printed cardboard product box: kraft base, tape on the lid, a coloured band round the sides with a pictogram front/back."""
    cx, cy, cz = center; sx, sy, sz = size
    z_bot = cz - sz / 2
    def r(c):
        nt = c.nt
        fib = WAVE(nt, COORD(nt, scale=(1, 1, 1)), 70.0, 1.5, 1.0, 1.0, "Z")
        mot = NOISE(nt, c.pos, 7.0, 3.0)
        col = RAMP(nt, mot, [(.25, dark), (.6, card), (.95, light)])
        col = MIX(nt, MATH(nt, "MULTIPLY", fib, .12), col, dark)
        top = face_mask(c, "z", 1.0, .7, .95)
        # lid seam + tape across the top
        u, v = rel(c, cx, cy, "xy")
        seam = SMOOTH(nt, MATH(nt, "ABSOLUTE", v), .004, .0015)
        col = MIX(nt, MATH(nt, "MULTIPLY", seam, top), col, dark)
        tape = SMOOTH(nt, MATH(nt, "ABSOLUTE", u), .03, .026)
        col = MIX(nt, MATH(nt, "MULTIPLY", tape, MATH(nt, "MULTIPLY", top, .8)), col, "E9D3A8")
        # printed band on the sides
        z0 = z_bot + sz * band_frac[0]; z1 = z_bot + sz * band_frac[1]
        side = MATH(nt, "SUBTRACT", 1.0, top)
        bz = MATH(nt, "MULTIPLY", band_z(c, z0, z1), side)
        bcol = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 5.0, 2.0), .15), band, "000000")
        col = MIX(nt, bz, col, bcol)
        st = MATH(nt, "MAXIMUM", band_z(c, z0 + .012, z0 + .02, .002), band_z(c, z1 - .02, z1 - .012, .002))
        col = MIX(nt, MATH(nt, "MULTIPLY", st, side), col, stripe)
        # pictogram on front and back faces
        fm = MATH(nt, "MAXIMUM", face_mask(c, "y", 1.0), face_mask(c, "y", -1.0))
        iu, iv = rel(c, cx, (z0 + z1) / 2, "xz")
        iu = MATH(nt, "MULTIPLY", iu, -1.0)      # seen from +Y, +X is on the left
        R = min(sx, z1 - z0) * .42
        if icon == "star":
            m = m_star(c, iu, iv, R, n=5)
        elif icon == "heart":
            m = m_heart(c, iu, iv, R * .8)
        elif icon == "tag":
            m = m_tag(c, iu, iv, R * .9, R * .55, R * .6, R * .16)
        elif icon == "burst":
            m = m_burst(c, iu, iv, R * .9, .15, 10)
        elif icon == "percent":
            m = m_percent(c, iu, iv, R)
        elif icon == "arrow":
            m = m_arrow(c, iu, iv, R, 90.0)
        elif icon == "dot":
            m = m_circle(c, iu, iv, R * .8)
        else:
            m = m_ring(c, iu, iv, R, R * .6)
        col = MIX(nt, MATH(nt, "MULTIPLY", m, fm), col, icon_col)
        return col
    return paint(name, r, edge=light, edge_k=.6, edge_r=.006, **fin)


def paint_label(name, center, col_bg, icon="star", icon_col="FFFFFF", R=.1, border=None, axes="xz", **fin):
    """A flat printed face (sign panel): background colour + pictogram centred at `center` (world) in plane `axes`."""
    def r(c):
        nt = c.nt
        u, v = rel(c, center[0], center[1], axes)
        col = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 6.0, 2.0), .12), col_bg, "000000")
        if icon == "star":
            m = m_star(c, u, v, R, n=5)
        elif icon == "burst":
            m = m_burst(c, u, v, R, .16, 12)
        elif icon == "percent":
            m = m_percent(c, u, v, R)
        elif icon == "heart":
            m = m_heart(c, u, v, R * .8)
        elif icon == "tag":
            m = m_tag(c, u, v, R * .9, R * .55, R * .6, R * .16)
        elif icon == "burst_percent":
            m = m_burst(c, u, v, R, .16, 12)
            col = MIX(nt, m, col, icon_col)
            m = m_percent(c, u, v, R * .5); icon_col2 = col_bg
            return MIX(nt, m, col, icon_col2)
        else:
            m = m_circle(c, u, v, R)
        return MIX(nt, m, col, icon_col)
    return paint(name, r, **fin)


def paint(name, recipe, **fin):
    return dv4.paint(name, recipe, **fin)


# ================================================================================================ geometry
def sphere_attr(name, r, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), seg=16, rings=10, paint=None, out="Body", rnd=None, axis="Z", **kw):
    """UV sphere whose Paint attribute carries R = longitude 0..1 (seam-safe per face), G = latitude 0..1, B = random.
    axis: which local axis is the pole axis before rot is applied."""
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    if axis != "Z":
        m = Matrix.Rotation(math.radians(90), 3, "X" if axis == "Y" else "Y")
        bmesh.ops.transform(bm, matrix=m.to_4x4(), verts=bm.verts)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ca = me.color_attributes.new("Paint", "FLOAT_COLOR", "CORNER")
    b = RNG.random() if rnd is None else rnd
    ax = {"Z": (0, 1, 2), "Y": (0, 2, 1), "X": (1, 2, 0)}[axis]
    vals = []
    for p in me.polygons:
        lons = []
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            x, y, z = co[ax[0]], co[ax[1]], co[ax[2]]
            lon = (math.atan2(y, x) / (2 * math.pi)) % 1.0
            lat = (z / r + 1) * .5
            lons.append([lon, lat])
        # unwrap the longitude inside the face so the seam interpolates right
        ref = lons[0][0]
        for q in lons:
            if q[0] - ref > .5:
                q[0] -= 1.0
            elif ref - q[0] > .5:
                q[0] += 1.0
            if abs(q[1] - 0) < 1e-6 or abs(q[1] - 1) < 1e-6:
                q[0] = ref
            vals.extend([q[0], q[1], b, 1.0])
    ca.data.foreach_set("color", vals)
    return dv4._obj(name, me, paint, out, loc, rot, scale, True, **kw)


def blade(name, L, W, wfn, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", bend=.3, cup=.15, twist=0.0, thickness=.003,
          nl=4, nw=2, rnd=None, wave=0.0, droop_pow=2.0, **kw):
    """Like dv4.leaf but with a custom half-width function wfn(t) in 0..1 (t along the blade)."""
    bm = bmesh.new()
    lay = bm.loops.layers.color.new("Paint")
    rows = []
    b = RNG.random() if rnd is None else rnd
    for i in range(nl + 1):
        t = i / nl
        w = max(.004, wfn(t)) * W * .5
        y = t * L
        z = -bend * L * (t ** droop_pow) + wave * L * .03 * math.sin(t * 9)
        row = []
        for j in range(nw + 1):
            s = -1 + 2 * j / nw
            zz = z + cup * abs(s) ** 1.5 * w + twist * s * t * .05
            row.append(bm.verts.new((s * w, y, zz)))
        rows.append(row)
    for i in range(nl):
        for j in range(nw):
            f = bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j])); f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for i in range(nl + 1):
        t = i / nl
        for j in range(nw + 1):
            s = j / nw
            v = rows[i][j]
            for lo in v.link_loops:
                lo[lay] = (t, s, b, 1.0)
    ob = dv4.from_bm(name, bm, paint, out, loc, rot, **kw)
    if thickness > 0:
        dv4.mod_solidify(ob, thickness, offset=0.0)
    return ob


def plane(name, w, h, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", **kw):
    """Single quad in the XZ plane facing +Y (w along X, h along Z), centred at loc."""
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in ((-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2))]
    f = bm.faces.new(vs); f.smooth = False
    bm.normal_update()
    if f.normal.y < 0:
        bmesh.ops.reverse_faces(bm, faces=[f])
    return dv4.from_bm(name, bm, paint, out, loc, rot, smooth=False, **kw)


def rounded_box(name, size, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", r=.02, segs=4, **kw):
    return dv4.cube(name, size, loc, rot, paint, out, bevel=r, segs=segs, **kw)


def uv_fit_xz(ob, flip_u=True):
    """Resets the UVs of a flat quad object to 0..1 (U along -X when flip_u so it reads right from +Y, V along +Z)."""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    xs = [v.co.x for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    for p in me.polygons:
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            u = (x1 - co.x) / (x1 - x0) if flip_u else (co.x - x0) / (x1 - x0)
            uv[li].uv = (u, (co.z - z0) / (z1 - z0))


def install_screen_fix():
    """Monkeypatch (this process only): after the bake, give every 'Anim Scroll' quad 0..1 UVs for T_IK_Screen."""
    if getattr(dv4, "_libB_screen_fix", False):
        return
    orig = dv4.set_pivots
    def patched(outs):
        for ob in outs:
            if ob.name.startswith("Anim Scroll"):
                uv_fit_xz(ob)
                dv4.log("screen UVs reset to 0..1 on", ob.name)
        orig(outs)
    dv4.set_pivots = patched
    dv4._libB_screen_fix = True


def install_material_fix():
    """Monkeypatch (this process only). dv4.final_materials() clears the material slots before re-adding them, and Blender
    drops the polygon material_index attribute with the last slot - so on an object that mixes baked paint with override
    slots (G_Glass / E_ / C_ / T_IK_Screen) every face ended up on the atlas. Re-applies the per-face slots afterwards."""
    if getattr(dv4, "_libB_mat_fix", False):
        return
    orig = dv4.final_materials
    def patched(outs, name, img):
        saved = {}
        for ob in outs:
            keys = [m.get("dv4_override") for m in ob.data.materials]
            saved[ob.name] = (keys, [p.material_index for p in ob.data.polygons])
        mats = orig(outs, name, img)
        for ob in outs:
            keys, old = saved[ob.name]
            slot = {m.name: i for i, m in enumerate(ob.data.materials)}
            new = [slot.get(keys[i], 0) if i < len(keys) and keys[i] else 0 for i in range(len(keys))]
            if any(new):
                for p, oi in zip(ob.data.polygons, old):
                    p.material_index = new[oi] if oi < len(new) else 0
                dv4.log("override slots restored on", ob.name, {k: v for k, v in slot.items()})
        return mats
    dv4.final_materials = patched
    dv4._libB_mat_fix = True


def install_fixes():
    install_material_fix()
    install_screen_fix()
